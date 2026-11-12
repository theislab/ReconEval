import scanpy as sc
import anndata as ad
from anndata import AnnData
from omegaconf import DictConfig
import torch
from torch.utils.data import Dataset, IterableDataset
import dask.array as da
import h5py
import numpy as np
from typing import Optional, Dict, Any
from scvi import REGISTRY_KEYS


class DaskSCVIIterableDataset(IterableDataset):
    def __init__(
        self,
        X,
        chunk_shuffle=True,
        batch_size=4096,
        seed=42,
        chunks_per_worker=5  
        ):
        super().__init__()
        self.X = X
        self.chunk_shuffle = chunk_shuffle
        self.batch_size = batch_size
        self.num_chunks = self.X.numblocks[0]
        self.base_seed = seed
        self.epoch = 0
        self.chunks_per_worker = chunks_per_worker 

    def set_epoch(self, epoch: int):
        self.epoch = epoch

    def __iter__(self):
        worker_info = torch.utils.data.get_worker_info()
        num_workers = worker_info.num_workers if worker_info else 1
        worker_id = worker_info.id if worker_info else 0

        dynamic_seed = self.base_seed + self.epoch
        rng = np.random.default_rng(dynamic_seed)

        chunk_indices = list(range(self.num_chunks))
        if self.chunk_shuffle:
            rng.shuffle(chunk_indices)

        chunk_groups = [
            chunk_indices[i:i+self.chunks_per_worker] 
            for i in range(0, len(chunk_indices), self.chunks_per_worker)
        ]

        groups_per_worker = (len(chunk_groups) + num_workers - 1) // num_workers
        start_idx = worker_id * groups_per_worker
        end_idx = min(start_idx + groups_per_worker, len(chunk_groups))
        assigned_groups = chunk_groups[start_idx:end_idx]

        for group in assigned_groups:
            merged_data = np.concatenate([
                self.X.blocks[chunk_idx].compute()
                for chunk_idx in group
            ], axis=0)

            if self.chunk_shuffle:
                group_seed = dynamic_seed + hash(tuple(group)) % (2**32)
                rng_group = np.random.default_rng(group_seed)
                rng_group.shuffle(merged_data, axis=0)

            num_samples = merged_data.shape[0]
            for i in range(0, num_samples, self.batch_size):
                sub_array = merged_data[i : i + self.batch_size]
                yield {
                    REGISTRY_KEYS.X_KEY: torch.from_numpy(sub_array),
                    REGISTRY_KEYS.BATCH_KEY: torch.zeros(
                        (sub_array.shape[0], 1), dtype=torch.int64
                    ),
                    REGISTRY_KEYS.LABELS_KEY: torch.zeros(
                        (sub_array.shape[0], 1), dtype=torch.int64
                    ),
                }
                
class DecodeOnlyDataset(Dataset):
    def __init__(
        self, 
        data_dict: Dict[str, Any],
        expression_key: str = 'X', 
        latent_key: str = 'scANVI', 
        batch_key: Optional[str] = None,
        pseudo_batch: bool = False
    ):
        super().__init__()
        
        self.expression = data_dict[expression_key]
        self.latent = data_dict[latent_key]
        self.batch_key = batch_key
        self.pseudo_batch = pseudo_batch
        
        if batch_key and batch_key in data_dict:
            self.batch = data_dict[batch_key]
            self.has_real_batch = True
        elif pseudo_batch:
            batch_shape = (len(self.expression), 1)
            self.batch = np.zeros(batch_shape, dtype=np.float32)
            self.has_real_batch = False
        else:
            self.batch = None
            self.has_real_batch = False
    
    def __len__(self):
        return len(self.expression)
    
    def __getitem__(self, idx):
        x = torch.from_numpy(self.expression[idx]).float()
        z = torch.from_numpy(self.latent[idx]).float()
        
        batch_item = {
            'x': x,
            'z': z,
        }
        
        if self.batch is not None:
            batch_item['batch_onehot'] = torch.from_numpy(self.batch[idx]).float()
            
        return batch_item


class PseudoBatchDataset(Dataset):
    def __init__(
        self, 
        data_dict,
        expression_key = 'X', 
        latent_key = 'SE', 
    ):
        super().__init__()
        
        self.expression = data_dict[expression_key]
        self.latent = data_dict[latent_key]
        
        batch_shape = (len(self.expression), 1)  
        self.batch = np.zeros(batch_shape, dtype=np.float32)
    
    def __len__(self):
        return len(self.expression)
    
    def __getitem__(self, idx):
        x = torch.from_numpy(self.expression[idx]).float()
        z = torch.from_numpy(self.latent[idx]).float()
        batch_onehot = torch.tensor(self.batch[idx]).float()
        
        
        return {
            'x': x,
            'z': z, 
            'batch_onehot': batch_onehot,
        }


class DaskDecodeOnlyIterableDataset(IterableDataset):
    def __init__(
        self,
        X_data,
        latent_data,
        batch_data=None,
        pseudo_batch: bool = False,
        chunk_shuffle=True,
        batch_size=4096,
        seed=42,
        chunks_per_worker=5
    ):
        super().__init__()
        self.X_data = X_data  
        self.latent_data = latent_data  
        self.batch_data = batch_data  
        self.chunk_shuffle = chunk_shuffle
        self.pseudo_batch = pseudo_batch
        self.batch_size = batch_size
        self.num_chunks = self.X_data.numblocks[0]
        self.base_seed = seed
        self.epoch = 0
        self.chunks_per_worker = chunks_per_worker
        
        if self.X_data.shape[0] != self.latent_data.shape[0]:
            raise ValueError(f"X_data and latent_data have different lengths: {self.X_data.shape[0]} vs {self.latent_data.shape[0]}")
        
        if self.batch_data is not None and self.batch_data.shape[0] != self.X_data.shape[0]:
            raise ValueError(f"batch_data length doesn't match X_data: {self.batch_data.shape[0]} vs {self.X_data.shape[0]}")

    def set_epoch(self, epoch: int):
        self.epoch = epoch

    def __iter__(self):
        worker_info = torch.utils.data.get_worker_info()
        num_workers = worker_info.num_workers if worker_info else 1
        worker_id = worker_info.id if worker_info else 0

        if torch.distributed.is_initialized():
            rank = torch.distributed.get_rank()
            world_size = torch.distributed.get_world_size()
        else:
            rank = 0
            world_size = 1

        dynamic_seed = self.base_seed + self.epoch
        rng = np.random.default_rng(dynamic_seed)

        chunk_indices = list(range(self.num_chunks))
        if self.chunk_shuffle:
            rng.shuffle(chunk_indices)

        chunk_groups = [
            chunk_indices[i:i+self.chunks_per_worker] 
            for i in range(0, len(chunk_indices), self.chunks_per_worker)
        ]

        # Drop remainder so every rank gets exactly the same number of groups
        usable = (len(chunk_groups) // world_size) * world_size
        chunk_groups = chunk_groups[:usable]

        groups_per_rank = len(chunk_groups) // world_size
        rank_start = rank * groups_per_rank
        rank_end = rank_start + groups_per_rank
        rank_groups = chunk_groups[rank_start:rank_end]

        # Drop remainder so every worker gets exactly the same number of groups
        usable_w = max(1, len(rank_groups) // num_workers) * num_workers
        rank_groups = rank_groups[:usable_w]

        groups_per_worker = max(1, len(rank_groups) // num_workers)
        start_idx = worker_id * groups_per_worker
        end_idx = start_idx + groups_per_worker
        assigned_groups = rank_groups[start_idx:end_idx]

        for group in assigned_groups:
            merged_X = np.concatenate([
                self.X_data.blocks[chunk_idx].compute()
                for chunk_idx in group
            ], axis=0)
            
            merged_latent = np.concatenate([
                self.latent_data.blocks[chunk_idx].compute()
                for chunk_idx in group
            ], axis=0)
            
            if self.batch_data is not None:
                merged_batch = np.concatenate([
                    self.batch_data.blocks[chunk_idx].compute()
                    for chunk_idx in group
                ], axis=0)
            else:
                merged_batch = np.zeros((merged_X.shape[0], 1), dtype=np.float32)

            if self.chunk_shuffle:
                group_seed = dynamic_seed + hash(tuple(group)) % (2**32)
                rng_group = np.random.default_rng(group_seed)
                indices = np.arange(len(merged_X))
                rng_group.shuffle(indices)
                
                merged_X = merged_X[indices]
                merged_latent = merged_latent[indices]
                merged_batch = merged_batch[indices]

            num_samples = merged_X.shape[0]
            # Drop last partial batch to keep batch counts identical across ranks
            num_batches = max(1, num_samples // self.batch_size)
            for b in range(num_batches):
                i = b * self.batch_size
                end_idx = i + self.batch_size
                batch_X = merged_X[i:end_idx]
                batch_latent = merged_latent[i:end_idx]
                batch_batch = merged_batch[i:end_idx]
                
                batch_dict = {
                    'x': torch.from_numpy(batch_X).float(),
                    'z': torch.from_numpy(batch_latent).float(),
                }
                
                if self.pseudo_batch and merged_batch is not None:
                    batch_dict['batch_onehot'] = torch.from_numpy(batch_batch).float()
                yield batch_dict