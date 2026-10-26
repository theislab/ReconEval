import sys

from sc_reconstruction.utils.data_tools import transform_to_csr

zarr_paths = sys.argv[1:] or [
    '/lustre/groups/ml01/workspace/xiaotong.fu/data/reconstruction/pbmc_w_ag/comb_w_obs.zarr',
]

for zarr_path in zarr_paths:
    h5ad_path = transform_to_csr(zarr_path)
    print(f"Converted {zarr_path} to {h5ad_path}")

print("All conversions completed.")
