from typing import Any, Dict
import numpy as np
import zarr
import os
import tempfile
import anndata as ad
from sc_reconstruction.dataloaders.datamodules import DaskPCADataModule
from sc_reconstruction.models._base_model import BaseReconstructionModel

def set_mem():
    import rmm
    import cupy as cp
    from rmm.allocators.cupy import rmm_cupy_allocator
    rmm.reinitialize(managed_memory=True)
    cp.cuda.set_allocator(rmm_cupy_allocator)






class ReconPCA(BaseReconstructionModel):
    """PCA reconstruction model with a scalable GPU implementation.

    Adapted from `rapids-singlecell
    <https://github.com/scverse/rapids_singlecell>`_ so the fit scales to
    100M-cell datasets via a ``dask_cuda.LocalCUDACluster`` and chunked
    SVD over the input zarr store.
    """
    def __init__(self, n_components: int = 300):
        super().__init__()
        self.n_components = n_components
        self.mean = None
        self.pc = None
        self.cluster = None
        self.client = None
    
    def _setup_cluster(self,
                      gpu_ids: str = "0",
                      temp_dir: str | None = None):
        from dask_cuda import LocalCUDACluster
        from dask.distributed import Client
        if temp_dir is None:
            temp_dir = tempfile.gettempdir()
        os.makedirs(temp_dir, exist_ok=True)
        self.cluster = LocalCUDACluster(
            local_directory=temp_dir,
            CUDA_VISIBLE_DEVICES=gpu_ids
        )
        self.client = Client(self.cluster)
        self.client.run(set_mem)

    def prepare(self, 
                data_path: str,
                batch_size: int = 1_000_000, 
                **kwargs) -> ad.AnnData:
        '''
        * not used in the current version
        Prepare the data for training
        data_path: str - The path to the training data, should be a h5ad file with X as acsr matrix
        batch_size: int - The batch size
        '''
        with h5py.File(data_path, "r") as f:
            adata = ad.AnnData(
                X=ad.experimental.read_elem_as_dask(
                    f["X"], 
                    chunks=(batch_size, -1) 
                )
            )
        return adata

    def train(self,
             datamodule: DaskPCADataModule,
             gpu_ids: str = "0",
             save_mean: bool = True,
             save_path: str = None,
             temp_dir: str | None = None,
             **kwargs) -> None:
        '''
        Train PCA model
        adata: ad.AnnData - X: dask array of csr matrix
        gpu_ids: str - The GPU IDs to use
        save_mean: bool - Whether to save the mean
        temp_dir: str | None - Directory for Dask temporary files; defaults to
            the system temporary directory.
        '''
        import rapids_singlecell as rsc
        import anndata as ad
        self._setup_cluster(gpu_ids, temp_dir=temp_dir)
        print("set up cluster")
        datamodule.prepare_data()
        adata = datamodule.train_dataloader()
        print("adata:", adata.X)
        # have to be done before saving mean
        # how does this affect the save mean?
        rsc.get.anndata_to_GPU(adata)

        if save_mean:
            print("saving mean")
            block_sums = adata.X.map_blocks(lambda b: b.sum(axis=0), dtype=adata.X.dtype)
            total_sum = block_sums.sum(axis=0).compute()
            self.mean = total_sum / adata.X.shape[0]
            self.mean = np.ascontiguousarray(self.mean.get())
        else:
            print("not saving mean")

        print("running PCA")
        rsc.pp.pca(
            adata, 
            n_comps=self.n_components,
            key_added="X_pca",
            mask_var=None
        )
        
        self.pc = adata.varm["X_pca"]
        self.pc = np.ascontiguousarray(self.pc)
        print("pc:", self.pc.shape, "device:", self.pc.device)
        if save_path:
            self.save(save_path)



    def predict(self, 
                X: np.ndarray,
                **inference_kwargs) -> np.ndarray:
        """
        Takes a raw NumPy array (batch of data), 
        prepares it, runs the reconstruction, and returns a NumPy array.
        
        Parameters:
        X: np.ndarray - Raw input data.
        Returns:
        np.ndarray: The predicted/reconstructed output.
        """
        latent = (X - self.mean) @ self.pc
        norm_recon = np.dot(latent, self.pc.T)  
        pred = norm_recon + self.mean  
        return pred
    
    def save(self, dir_path: str) -> None:
        print("saving mean and pc")
        os.makedirs(dir_path, exist_ok=True)
        if self.mean is not None:
            zarr.save(f"{dir_path}/mean.zarr", self.mean)
            print("saved mean")
        if self.pc is not None:
            zarr.save(f"{dir_path}/pc_{self.n_components}.zarr", self.pc)
            print("saved pc")
        print(f"Model saved to {dir_path}")

    def load(self, path: list[str], map_location = None) -> None:
        """Load the model
        path: list[str] - The path to the model file.
        path[0]: str - The path to the mean zarr file.
        path[1]: str - The path to the pc zarr file.
        """
        self.mean = zarr.load(path[0])
        self.pc = zarr.load(path[1])
        self.n_components = self.pc.shape[1]
        print(f"Model loaded from {path}")

    def _teardown_cluster(self):
        if self.client:
            self.client.close()
        if self.cluster:
            self.cluster.close()
        print("Cluster resources released")

    def __del__(self):
        self._teardown_cluster()
