import zarr
from scipy.sparse import csr_matrix, vstack
import anndata as ad
import os 
import warnings
from tqdm import tqdm

def transform_to_csr(path, chunk_size=1_000_000):
    import dask.array as da

    if not os.path.isdir(path):
        warnings.warn(f"Path doesn't exist: {path}")
        return None


    datasets = []
    try:
        datasets.append(da.from_zarr(path))
    except Exception:
        try:
            datasets.append(da.from_zarr(path, 'X'))
        except Exception:
            try:
                root = zarr.open_group(path, mode='r')
                try:
                    for g in root.group_keys():
                        loaded = False
                        try:
                            datasets.append(da.from_zarr(path, f"{g}/X"))
                            loaded = True
                        except Exception:
                            pass
                        if not loaded:
                            try:
                                datasets.append(da.from_zarr(path, g))
                            except Exception:
                                warnings.warn(f"Skipping subgroup '{g}' in {path}: no array or 'X'.")
                except Exception:
                    pass
            except Exception as e2:
                warnings.warn(f"Failing loading: {path} Error: {e2}")
                return None

    print(f"Data loaded. Found {len(datasets)} subgroups. Transforming to CSR format...")
    csr_parts = []
    for data in tqdm(datasets):
        data = data.rechunk((chunk_size, -1))
        blocks = []
        n_blocks = data.numblocks[0]
        for i in range(n_blocks):
            block = data.blocks[i, :].compute()
            blocks.append(csr_matrix(block))
        csr_parts.append(vstack(blocks))

    global_csr = vstack(csr_parts) if len(csr_parts) > 1 else csr_parts[0]
    adata = ad.AnnData(X=global_csr)
    adata.write_h5ad(path.replace('.zarr', '.h5ad'))
    return path.replace('.zarr', '.h5ad')


def get_zarr_attr(meta_root, target_key):
    zarr_store = zarr.open(meta_root, mode='r')
    if target_key is None:
        print('return all attributes: train, val, test combinations')
        return zarr_store.attrs['train_combinations'] + zarr_store.attrs['val_combinations'] + zarr_store.attrs['test_combinations']
    if target_key in zarr_store.attrs:
        return zarr_store.attrs[target_key]
    else:
        raise KeyError(f"Key '{target_key}' not found in Zarr attributes.")

def split_zarr_dataloader(zarr_root, target_combinations, target_key='test_combinations', X_key='X', idx_key=None):
    '''
    Specified data loader for mainly inference purpose
    '''
    split_zarr_paths = []
    zarr_store = zarr.open(zarr_root, mode='r')
    for target_combination in target_combinations:
        if idx_key is not None:
            yield target_combination, zarr_store[target_combination][X_key][:], zarr_store[target_combination][idx_key][:]
        else:
            yield target_combination, zarr_store[target_combination][X_key][:] 

def filter_genes(X, gene_names, selected_genes):
    gene_idx = [gene_names.index(gene) for gene in selected_genes]
    return X[:, gene_idx]
