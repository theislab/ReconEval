import scanpy as sc
import anndata as ad
import matplotlib.pyplot as plt
import numpy as np
import os
import sys
from pathlib import Path
import torch
from tqdm import tqdm
import zarr
import hydra
from omegaconf import DictConfig, OmegaConf

if 'MPLBACKEND' in os.environ:
    del os.environ['MPLBACKEND']

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / 'src'))

STATE_SRC = os.environ.get("STATE_SRC")
if STATE_SRC:
    sys.path.insert(0, STATE_SRC)

from sc_reconstruction.utils.data_tools import *
import sc_reconstruction.models.reconse as reconse
from hydra.utils import instantiate
from lightning.pytorch import seed_everything
from torch.utils.data import DataLoader

_create_dataloader = reconse.create_dataloader


# SE forks one loader worker per group; forking this multi-threaded process occasionally deadlocks the worker.
def _create_dataloader_in_process(*args, **kwargs):
    loader = _create_dataloader(*args, **kwargs)
    return DataLoader(loader.dataset, batch_size=loader.batch_size, shuffle=False,
                      collate_fn=loader.collate_fn, num_workers=0)


reconse.create_dataloader = _create_dataloader_in_process


@hydra.main(config_path='../configs/pretrained', config_name="SE", version_base=None)
def emb(cfg: DictConfig) -> None:
    all_combinations = get_zarr_attr(cfg.data_args.split_meta_root, target_key=cfg.data_args.target_key)
    print(f"All combinations for key {cfg.data_args.target_key}: len {len(all_combinations)}")

    total_combinations = len(all_combinations)
    part_size = total_combinations // cfg.total_parts
    start_idx = (cfg.parts - 1) * part_size
    end_idx = cfg.parts * part_size if cfg.parts < cfg.total_parts else total_combinations
    selected_combinations = all_combinations[start_idx:end_idx]
    print(f"Processing part {cfg.parts}/{cfg.total_parts}: combinations {start_idx} to {end_idx}.")
     
    test_dataloader = split_zarr_dataloader(
        cfg.data_args.comb_meta_root, 
        selected_combinations, 
        target_key=cfg.data_args.target_key,
        # idx_key='obs_index'
        )
    gene_names = get_zarr_attr(cfg.data_args.comb_meta_root, target_key='var_names')
    
    pretrained_se = instantiate(cfg.model_args)
    overlap_genes = pretrained_se.get_overlap_genes(gene_names)

    pretrained_se.set_genes(gene_names)

    output_dir = cfg.data_args.output_dir
    state_zarr = zarr.open(output_dir, mode='a')
    CHUNK_SIZE = 10_000
    existing_combinations = list(state_zarr.group_keys())
    print(f"{len(existing_combinations)} existing combinations in output Zarr")
    for combination, X in test_dataloader:
        if combination in existing_combinations:
            print(f"Combination {combination} already processed. Skipping.")
            continue
        cell_emb = pretrained_se.get_latent_representation(X=X)
        state_zarr.create_group(combination, overwrite=True)
        state_zarr[combination].create_dataset(
            'X', 
            data=cell_emb, 
            chunks=(CHUNK_SIZE, cell_emb.shape[1])  
        )
        # state_zarr[combination].create_dataset(
        #     'X',
        #     data=X,
        #     chunks=(CHUNK_SIZE, X.shape[1])
        # )
        # state_zarr[combination].create_dataset(
        #     'obs_index',
        #     data=obs_index,
        #     chunks=(CHUNK_SIZE,)
        # )

    print(f"Embedding extraction for key {cfg.data_args.target_key} completed.")

if __name__ == "__main__":
    emb()