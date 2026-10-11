import zarr
import re
import gc
import time

import scanpy as sc
import pandas as pd

def sanitize_key(key):
    return re.sub(r'[^\w]', '_', str(key)).strip('_')

print("Starting HVG evaluation for PBMC dataset")

adata = sc.read_h5ad('/lustre/groups/ml01/workspace/ten_million/data/final_data/adata_notebook_input.h5ad')
adata.obs['cell_id'] = adata.obs.index
adata.obs = adata.obs.reset_index(drop=True)

new_cell_type = pd.read_csv("/lustre/groups/ml01/workspace/ten_million/data/data_2024_12_16/new_cell_type_annotations.csv")
d = new_cell_type[["Unnamed: 0", "cell_type_new_coarse"]].drop_duplicates().set_index("Unnamed: 0")['cell_type_new_coarse'].to_dict()
adata.obs["cell_type_new"] = adata.obs["cell_id"].apply(lambda x: d[x])

adata.obs.loc[:, 'combination_key'] = adata.obs.apply(
    lambda row: f"{sanitize_key(row['cell_type_new'])}-"
                f"{sanitize_key(row['donor'])}-"
                f"{sanitize_key(row['cytokine'])}",
    axis=1
)

del new_cell_type, d
gc.collect()
time.sleep(10)

for split in ['split01', 'split02', 'split03']:
    print(f"Processing {split}")

    train_combinations = zarr.open_group(f'/lustre/groups/ml01/workspace/xiaotong.fu/data/reconstruction/pbmc/{split}/split_metadata.zarr', mode='r').attrs["train_combinations"]

    adata.obs["is_train"] = adata.obs.apply(lambda x: x.combination_key in train_combinations, axis=1)

    tmp = adata[adata.obs.is_train].copy()

    sc.pp.normalize_total(tmp, target_sum=1e4)
    sc.pp.log1p(tmp)
    sc.pp.highly_variable_genes(tmp, min_mean=0.0125, max_mean=3, min_disp=0.25)

    train_hvgs = set(tmp.var[tmp.var.highly_variable].index.to_list())
    hvgs = set(zarr.open_group('/lustre/groups/ml01/workspace/xiaotong.fu/data/reconstruction/pbmc/comb_w_obs.zarr').attrs['var_names'])
    print(f"Split {split}: {len(train_hvgs.intersection(hvgs)) / len(hvgs)}")

    del tmp, train_hvgs, hvgs, train_combinations
    gc.collect()
    time.sleep(10)