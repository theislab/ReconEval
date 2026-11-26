import importlib.util
import os
import re
import gc
import time

import numpy as np
import zarr
import scanpy as sc
import dask.array as da
from tqdm import tqdm
from dask.diagnostics import ProgressBar
from sklearn.model_selection import train_test_split

import hydra
from omegaconf import DictConfig

def demo_subsample(adata, n_cells=500, n_genes=None, seed=42):
    """Subsample at most n_cells cells and optionally n_genes genes."""
    rng = np.random.default_rng(seed)
    if len(adata) > n_cells:
        cell_idx = np.sort(rng.choice(len(adata), size=n_cells, replace=False))
        adata = adata[cell_idx].copy()
    if n_genes is not None and adata.n_vars > n_genes:
        gene_idx = np.sort(rng.choice(adata.n_vars, size=n_genes, replace=False))
        adata = adata[:, gene_idx].copy()
    return adata

def sanitize_key(key):
    return re.sub(r'[^\w]', '_', str(key)).strip('_')

def load_utils(path):
    spec = importlib.util.spec_from_file_location("dataset_utils", path)
    mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(mod)
    return mod

def read_adata(path, layer=None):
    adata = sc.read_h5ad(path)
    if layer is not None:
        adata.X = adata.layers[layer]
    return adata


def process_adata(adata, normalize=True, target_sum=1e4, log1p=True):
    if normalize:
        sc.pp.normalize_total(adata, target_sum=target_sum)
    if log1p:
        sc.pp.log1p(adata)
    return adata

def select_hvg(adata, hvg):
    if hvg.method == 'precomputed':
        mask = adata.var[hvg.column] == 'True'
    elif hvg.method == 'dispersion':
        sc.pp.highly_variable_genes(adata, min_mean=hvg.min_mean,
                                    max_mean=hvg.max_mean, min_disp=hvg.min_disp)
        mask = adata.var['highly_variable']
    elif hvg.method == 'n_top_genes':
        sc.pp.highly_variable_genes(adata, n_top_genes=hvg.n_top_genes)
        mask = adata.var['highly_variable']
    else:
        raise ValueError(f"Unknown hvg.method: {hvg.method!r}. Choose precomputed, dispersion, or n_top_genes.")
    return adata[:, mask]

def prepare_dataset(adata, hvg):
    adata = process_adata(adata)
    adata = select_hvg(adata, hvg)
    adata.obs['cell_id'] = adata.obs.index.astype(str)
    adata.obs.reset_index(drop=True, inplace=True)
    return adata


def create_comb_key(adata, columns=('cell_type', 'dataset', 'origin')):
    for col in columns:
        adata.obs[col] = adata.obs[col].astype(str)
    adata.obs['comb_key'] = adata.obs.apply(
        lambda r: '-'.join(sanitize_key(r[col]) for col in columns), axis=1
    )
    return adata

def write_comb_to_zarr(adata, output_dir, var_names_col=None):
    os.makedirs(output_dir, exist_ok=True)
    root_zarr = zarr.open(output_dir, mode='a')
    var_names = adata.var[var_names_col].tolist() if var_names_col else adata.var_names.tolist()
    root_zarr.attrs['var_names'] = var_names

    current_combinations = set()
    for comb_key, row_positions in tqdm(adata.obs.groupby('comb_key').indices.items()):
        group = adata.obs.iloc[row_positions]
        current_combinations.add(comb_key)
        x_group = adata.X[row_positions].toarray()
        da.from_array(x_group, chunks=-1).astype(adata.X.dtype).to_zarr(
            output_dir + '/' + comb_key, component='X', overwrite=True)
        da.from_array(group['cell_id'].values, chunks=-1).astype('<U40').to_zarr(
            output_dir + '/' + comb_key, component='obs_index', overwrite=True)

    existing = set(root_zarr.attrs.get('combinations', []))
    existing.update(current_combinations)
    root_zarr.attrs['combinations'] = sorted(existing)

def prepare_splits(comb_dir, split_cfg, columns, seed=42):
    """Assign combinations to train/val/test splits.

    Strategies:
      read        — load from a pre-existing split_metadata.zarr (split_cfg.path)
      combination — split by full combination key
      category    — split by one column (split_cfg.column) shared across combinations
    """
    strategy = split_cfg.strategy

    if strategy == 'read':
        meta = zarr.open(split_cfg.path, mode='r')
        return {
            'train': list(meta.attrs['train_combinations']),
            'val':   list(meta.attrs['val_combinations']),
            'test':  list(meta.attrs['test_combinations']),
        }

    combinations = list(zarr.open(comb_dir, mode='r').attrs['combinations'])
    train_ratio = split_cfg.get('train_ratio', 0.7)
    val_ratio   = split_cfg.get('val_ratio',   0.15)
    train_val_ratio = train_ratio + val_ratio

    if strategy == 'combination':
        units = combinations
    elif strategy == 'category':
        col_idx = list(columns).index(split_cfg.column)
        units = list(np.unique([c.split('-')[col_idx] for c in combinations]))
    else:
        raise ValueError(f"Unknown split strategy: {strategy!r}. "
                         f"Choose read, combination, or category.")

    train_val_units, test_units = train_test_split(
        units, train_size=train_val_ratio, random_state=seed)
    train_units, val_units = train_test_split(
        train_val_units, train_size=train_ratio / train_val_ratio, random_state=seed)

    train_set, val_set, test_set = set(train_units), set(val_units), set(test_units)

    if strategy == 'combination':
        return {
            'train': [c for c in combinations if c in train_set],
            'val':   [c for c in combinations if c in val_set],
            'test':  [c for c in combinations if c in test_set],
        }
    else:
        col_idx = list(columns).index(split_cfg.column)
        return {
            'train': [c for c in combinations if c.split('-')[col_idx] in train_set],
            'val':   [c for c in combinations if c.split('-')[col_idx] in val_set],
            'test':  [c for c in combinations if c.split('-')[col_idx] in test_set],
        }

def write_split_to_zarr(adata, splits, output_dir, chunk_size=50_000, seed=42):
    comb_dir = os.path.join(output_dir, 'expression.zarr')

    for partition, combs in splits.items():
        arrays = []
        for comb in combs:
            arrays.append(da.from_zarr(os.path.join(comb_dir, comb), 'X'))

        data = da.concatenate(arrays, axis=0)
        print(f"{partition} shape: {data.shape}")

        if partition == 'train':
            data = data.rechunk((chunk_size, data.shape[1]))
            rng = np.random.default_rng(seed=seed)
            perm = rng.permutation(data.shape[0])
            indexer = [list(perm[i:i+chunk_size]) for i in range(0, data.shape[0], chunk_size)]
            data = da.shuffle(data, indexer=indexer, axis=0, chunks='auto')

        save_path = os.path.join(output_dir, f'{partition}.zarr')
        with ProgressBar():
            data.rechunk((chunk_size, data.shape[1])).to_zarr(save_path, component='X', overwrite=True)

        # compute and store library stats
        X = zarr.open(save_path, mode='r+')['X'][:]
        log_counts = np.ma.log(X.sum(axis=1)).filled(0)
        zarr.open(save_path, mode='r+').attrs['library_log_mean'] = float(log_counts.mean())
        zarr.open(save_path, mode='r+').attrs['library_log_var'] = float(log_counts.var())

        print(f"Done: {save_path}")

def write_split_metadata_to_zarr(splits, output_dir, seed=42):
    meta_path = os.path.join(output_dir, 'split_metadata.zarr')
    meta = zarr.open_group(meta_path, mode='w')
    meta.attrs['train_combinations'] = splits['train']
    meta.attrs['val_combinations']   = splits['val']
    meta.attrs['test_combinations']  = splits['test']
    meta.attrs['random_seed']        = seed

@hydra.main(config_path='configs', config_name='base', version_base=None)
def main(cfg: DictConfig) -> None:
    utils = load_utils(cfg.utils) if cfg.utils else None

    adata = read_adata(cfg.input, cfg.layer)

    if utils and hasattr(utils, 'pre_proc'):
        adata = utils.pre_proc(adata, cfg)

    adata = prepare_dataset(adata, cfg.hvg)

    if cfg.get('demo', False):
        adata = demo_subsample(adata, cfg.get('demo_cells', 500),
                               cfg.get('demo_genes', None), cfg.seed)
    adata = create_comb_key(adata, tuple(cfg.columns))
    expression_dir = os.path.join(cfg.output, 'expression.zarr')
    write_comb_to_zarr(adata, expression_dir, cfg.var_names_col)

    if utils and hasattr(utils, 'post_proc'):
        utils.post_proc(expression_dir, cfg)

    splits = prepare_splits(expression_dir, cfg.split, cfg.columns, cfg.seed)
    write_split_metadata_to_zarr(splits, cfg.output, seed=cfg.seed)
    write_split_to_zarr(adata, splits, cfg.output, seed=cfg.seed)


if __name__ == "__main__":
    main()
