import pandas as pd


def pre_proc(adata, cfg, id_col='Unnamed: 0', cell_type_col='cell_type_new_coarse'):
    """Remap cell types from an external CSV annotation file."""
    new_cell_type = pd.read_csv(cfg.cell_type_csv)
    d = (new_cell_type[[id_col, cell_type_col]]
         .drop_duplicates()
         .set_index(id_col)[cell_type_col]
         .to_dict())
    adata.obs['cell_type_new'] = adata.obs['cell_id'].map(d)
    print(f"Remapped {len(d)} cell type annotations.")
    return adata


def post_proc(zarr_dir, cfg):
    pass
