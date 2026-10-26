# preprocessing/

Data preparation pipelines for the three benchmark datasets. These produce
the zarr / h5ad inputs that the training drivers under
`experiments/0{1,2,3}_*/codes/` consume.

```
preprocessing/
├── prepare_dataset.py    # universal pipeline for luca/pbmc (replaces preprocess_*.py)
├── combine_emb_zarr.py   # combine expression and embeddings for decoder training
├── configs/              # Hydra configs: base.yaml, data/luca.yaml, data/pbmc.yaml
├── utils/                # dataset-specific hooks: luca.py, pbmc.py
├── preprocess_pbmc.py    # PBMC-10M: normalize, log1p, HVG, zarr per (cell_type, donor, cytokine)
├── preprocess_luca.py    # LuCA: same pattern; splits per study/disease/tissue
├── zarr_to_h5ad.py       # zarr → h5ad helper used by all three pipelines
└── tahoe/                # multi-step Tahoe-100M pipeline (cell line × drug × concentration)
    ├── process_pipeline.sh   # orchestrator (env vars: DATASET_NAME, STEPS, SPLITS, ...)
    ├── tahoe_save.py
    ├── tahoe_saveonly.py
    ├── save_comb.py
    ├── mp_save_comb.py
    ├── merge_comb.py
    ├── merge_mcomb.py
    └── _split/               # split helpers (multi-class)
        ├── split_cell_line.py
        ├── split_drug.py
        └── split_comb.py
```

## Usage

For luca and pbmc, use `prepare_dataset.py` with Hydra configs:

```bash
python prepare_dataset.py --config-name data/luca
python prepare_dataset.py --config-name data/pbmc
```

`preprocess_pbmc.py` and `preprocess_luca.py` are notebook-converted scripts —
read them top-to-bottom; the cell markers (`# In[N]:`) trace back to the
original `preprocess_*.ipynb` notebooks in the private repo. Both are
single-pass scripts you run once per dataset; they write zarr + h5ad
artefacts under `${RECONEVAL_OUT}/data/<dataset>/`.

Tahoe is a multi-step pipeline orchestrated by
`tahoe/process_pipeline.sh` — set `STEPS=save,comb,merge,split` (or a
subset) and the script will submit the matching slurm jobs in order.

## Conda env

| Pipeline | Env |
|---|---|
| `preprocess_pbmc.py` | `cstm_scvi_env` |
| `preprocess_luca.py` | `cstm_scvi_env` |
| `tahoe/*` | `cstm_scvi_env` |

## Data paths

The scripts hardcode the cluster mirror at
`/lustre/groups/ml01/workspace/xiaotong.fu/data/reconstruction/...` for
both inputs (raw counts) and outputs (zarr / h5ad). Patch these to your own
data root before running, or symlink to keep the scripts unchanged.

## Notebook origin

Both `preprocess_pbmc.py` and `preprocess_luca.py` were derived from the
notebooks listed in the private repo:

- `preprocess_pbmc.py` ← `notebooks/datahandling/preprocess_pbmc10m.ipynb`
- `preprocess_luca.py` ← `notebooks/datahandling/preprocess_luca.ipynb`

The notebook structure (commented-out alternates, exploratory cells) is
preserved verbatim — for a Nature-Methods-grade rerun, prune to only the
cells the dataset actually needs.
