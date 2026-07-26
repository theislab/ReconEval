# 03_latent_shift — perturbation prediction in latent space

Predict the **post-perturbation cell state** given a control cell state and a
perturbation covariate. Two methods are benchmarked:

- **CellFlow** — JAX optimal-transport flow matching.
- **STATE** — PyTorch transformer over cell sets.

Both consume the same upstream embeddings (PCA / AE / VAE at
multiple latent dims, plus the four FMs).

## Layout

```
03_latent_shift/
├── configs/
│   ├── cellflow_default.yaml       # CellFlow training defaults
│   ├── state_hf_se_parse.yaml      # STATE training defaults
│   ├── arch/                       # STATE architecture configs
│   │   ├── hf_se_parse.yaml
│   │   ├── paper_large_pbmc.yaml
│   │   ├── paper_parse_pbmc.yaml
│   │   └── paper_small_pbmc.yaml
│   └── st/                         # STATE TOML data configs
│       ├── pbmc_train.toml
│       ├── pbmc_val.toml
│       └── pbmc_test.toml
├── codes/
│   ├── train_cf.py                 # CellFlow trainer (argparse)
│   ├── train_st.py                 # STATE trainer (argparse)
│   ├── prepare_pbmc_st.py          # writes per-model obsm onto pbmc h5ad
│   ├── eval_cf.py                  # CellFlow perturbation evaluator (Hydra base_eval_cf)
│   └── eval_st.py                  # STATE perturbation evaluator (Hydra base_eval_st)
└── submit/
    ├── train_cf.sbatch
    └── train_st.sbatch
```

## Eval drivers

After training, score a run with the matching evaluator (uses
`configs/base_eval_cf.yaml` / `base_eval_st.yaml` + `metric/st_pert.yaml`):

```bash
# CellFlow eval
python experiments/03_latent_shift/codes/eval_cf.py \
  run_dir=/path/to/cf_run +metric=st_pert split=test ckpt=last

# STATE eval
python experiments/03_latent_shift/codes/eval_st.py \
  run_dir=/path/to/st_run +metric=st_pert split=test ckpt=last
```

Both write per-combination CSVs to
`${RECONEVAL_OUT}/results/{cf,st}/{run_name}/{split}/{ckpt}/{metric}/`.

There is no sweep wrapper at this layer — submit the per-model jobs you
need by overriding `MODEL` on the sbatch command.

## CLI

Both drivers are argparse:

```bash
# CellFlow
python experiments/03_latent_shift/codes/train_cf.py \
  --model <PCA_128|AE_128|...|SE|scGPT|...> \
  --num_iters 500000 --batch_size 1024 --valid_freq 50000 \
  [--seed 42] [--out_dir /path/to/cf_runs] [--config repro]

# STATE
python experiments/03_latent_shift/codes/train_st.py \
  --model <PCA_128|AE_128|...|SE|...> \
  --max_steps 40000 --batch_size 16 \
  [--lr 1e-4] [--seed 42] [--no_wandb] \
  [--decoder_mode hf_se_parse] [--arch_config paper_parse_pbmc]
```

## Sbatch wrappers

```bash
# CellFlow on AE-128
sbatch --export=MODEL=AE_128 experiments/03_latent_shift/submit/train_cf.sbatch

# STATE on SE
sbatch --export=MODEL=SE experiments/03_latent_shift/submit/train_st.sbatch
```

Env vars honoured by both: `MODEL` (required), `NUM_ITERS`/`MAX_STEPS`,
`BATCH_SIZE`, `SEED`, `OUT_DIR`/`OUT_ROOT`.

## Quick smoke test

CellFlow needs a GPU (JAX XLA); 100 iters of PCA-128 finishes in ~3 min:

```bash
conda activate pancellflow
CELLFLOW_SRC=/path/to/pancellflow/cellflow/src \
RECONEVAL_OUT=/tmp/reconeval_smoke \
python experiments/03_latent_shift/codes/train_cf.py \
  --model PCA_128 --num_iters 100 --batch_size 64 --valid_freq 100 \
  --out_dir /tmp/cf_smoke
```

STATE same idea with `--no_wandb` and a low `--max_steps`:

```bash
conda activate cstm_scvi_env
RECONEVAL_OUT=/tmp/reconeval_smoke \
python experiments/03_latent_shift/codes/train_st.py \
  --model PCA_128 --max_steps 100 --batch_size 4 --no_wandb \
  --out_root /tmp/st_smoke
```

## Conda envs

| Driver | Env | Why |
|---|---|---|
| `train_cf.py` | `pancellflow` | JAX + cellflow |
| `train_st.py` | `cstm_scvi_env` | torch + STATE |
| `prepare_pbmc_st.py` | `cstm_scvi_env` | torch utilities |

`CELLFLOW_SRC` env var lets you point at a cellflow dev clone instead of
the pip-installed copy.
