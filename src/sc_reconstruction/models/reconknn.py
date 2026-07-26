import h5py
import numpy as np
import anndata as ad

from tqdm import tqdm

try:  # GPU-only (RAPIDS/CUDA) deps; optional so the package imports on CPU
    import cupy as cp
    import cuml as cm
except ImportError:  # pragma: no cover - CPU-only environments
    cp = None
    cm = None

class ReconKNN():
    def __init__(self, n_neighbors: int = 5, metric: str = 'euclidean',
                 data_path: str = None, batch_size: int = 1_000_000):
        self.n_neighbors = n_neighbors
        self.metric = metric
        self.batch_size = batch_size
        
        # with h5py.File(data_path, "r") as f:
        #     adata = ad.AnnData(
        #         X=ad.experimental.read_elem_as_dask(
        #             f["X"], 
        #             chunks=(self.batch_size, -1) 
        #         )
        #     )
        
        # indices = np.random.choice(range(len(adata)), size=int(len(adata)*0.1), replace=False)
        # self.adata = adata[indices].copy()
        
        adata = ad.read_h5ad(data_path)
        rng = np.random.default_rng(seed=42)
        indices = rng.choice(range(len(adata)), size=int(len(adata) * 0.1), replace=False)
        self.adata = adata[indices].X.toarray()
            
    # def process_subbatch(self, x, y, idx_shift):
    #     x = cp.asarray(x)
    #     distances = []
    #     indices = []
    #     for e in y:
    #         e = cp.asarray(e)
    #         tmp = cp.sum((e - x) ** 2, axis=1)
    #         idx = cp.argsort(tmp)[:self.n_neighbors]
    #         distances.append(tmp[idx].get())
    #         indices.append(idx.get() + idx_shift)
            
    #     return np.stack(distances), y[np.stack(indices)]
    
    def process_subbatch(self, x, y):
        data_gpu = cp.asarray(x)
        nn = cm.neighbors.NearestNeighbors(
            n_neighbors=self.n_neighbors,
            output_type="numpy",
            metric="euclidean"
        ).fit(data_gpu)

        points_gpu = cp.asarray(y)
        distances, indices = nn.kneighbors(points_gpu)
        
        del data_gpu, points_gpu, nn
        # cp.get_default_memory_pool().free_all_blocks()
        # cp.get_default_pinned_memory_pool().free_all_blocks()
        
        return distances, x[indices]
        

    def predict(self, X: np.ndarray, **inference_kwargs) -> np.ndarray:
        distances = []
        values = []
        
        # for block in tqdm(self.adata.X.blocks.ravel()):
        #     dst, val = self.process_subbatch(block.compute().toarray(), X)
        #     distances.append(dst)
        #     values.append(val)
        
        n = 100
        n_rows = int(self.adata.shape[0] / n) + 2
        for i in range(n):
            dst, val = self.process_subbatch(self.adata[(i * n_rows):((i + 1) * n_rows)], X)
            distances.append(dst)
            values.append(val)
        
        distances = np.concatenate(distances, axis=1)
        values = np.concatenate(values, axis=1)
        
        idx = np.argsort(distances, axis=1)[:, :self.n_neighbors]
        reconstructed = np.stack([values[i, idx[i]] for i in range(values.shape[0])]).mean(axis=1)
        return reconstructed