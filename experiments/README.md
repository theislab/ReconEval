# experiments/

YAML configs, SLURM submission scripts and Python training drivers for the
three benchmark settings shown in Fig 1c.

```
experiments/
├── preprocessing/        # PBMC / LuCA / Tahoe data-preparation scripts
├── 01_end_to_end/        # PCA / AE / VAE (scVI, nlscVI, mlscVI) reconstruction
├── 02_foundation_model/  # FM (SE / scGPT / scConcept / SCimilarity) + decoder
└── 03_latent_shift/      # CellFlow / STATE perturbation prediction
```

Each task subfolder contains:

- `configs/` — Hydra YAML configs organised into subgroups (`model/`,
  `data/`, `trainer/`, `pretrained/`, `decoder/`, `metric/`) so a single
  CLI override picks the right config. `03_latent_shift` uses argparse
  drivers plus its own Hydra eval configs.
- `codes/` — Python drivers: training + matching eval scripts. Every
  driver injects the public `src/sc_reconstruction` into `sys.path`
  relative to its own location, so no `PYTHONPATH` setup is needed.
- `submit/` — sbatch wrappers. Each sets `EXPDIR` to its task folder at
  job start and calls `${EXPDIR}/codes/<driver>.py` — no clone-of-private
  -repo dependency.

The `preprocessing/` folder lifts the data-prep pipelines from the
private repo (PBMC and LuCA from `notebooks/datahandling/` notebooks,
Tahoe from `handler/data/_process_tahoe`). See `preprocessing/README.md`.

## Quick start

```bash
# 1. Output sink for checkpoints + logs (optional; defaults to ~/reconeval_outputs/):
export RECONEVAL_OUT=/path/to/scratch

# 2. (CellFlow only) point at a dev clone of cellflow if not pip-installed:
export CELLFLOW_SRC=/path/to/pancellflow/cellflow/src

# 3. (SE only) point at a clone of the STATE source if `state` is not pip-installed:
export STATE_SRC=/path/to/state/src

# 4. Submit an example job (end-to-end AE on Tahoe, latent 128):
sbatch --export=ALL,LATENT=128 experiments/01_end_to_end/submit/train_ae.sbatch

# CellFlow training on PBMC, AE-128 embedding:
sbatch --export=MODEL=AE_128 experiments/03_latent_shift/submit/train_cf.sbatch
```

Slurm log paths are relative (`logs/slurm/`) so they land under the working
directory you ran `sbatch` from; create that dir first or pass
`--output=...` / `--error=...` overrides.

## Env vars

| Name | What it controls | Default |
|---|---|---|
| `RECONEVAL_OUT` | Output root for weights, checkpoints and Hydra outputs/logs. | `$HOME/reconeval_outputs` |
| `CELLFLOW_SRC` | Path to a `cellflow` dev install (used by `03_latent_shift`). | Skipped if unset (assumes pip-installed `cellflow`). |
| `STATE_SRC` | Path to a `state` source clone (used by SE embed in `02_foundation_model`). | Skipped if unset (assumes pip-installed `state`). |
| `MODEL`, `LATENT`, `DATA`, `SPLIT`, `MAX_EPOCHS`, … | sbatch-level overrides documented in each task's README. | Per-script defaults. |

## Data paths

Data paths inside the YAMLs still point at the cluster mirror
(`/lustre/groups/ml01/workspace/xiaotong.fu/data/reconstruction/...`). Override
on the Hydra CLI or symlink to your own data root before submitting.

## Conda envs per task

| Task | Conda env | Why |
|---|---|---|
| 01_end_to_end | `cstm_scvi_env` | torch + scvi-tools |
| 02_foundation_model — SE (embed) | `reconeval-state` | needs the `arc-state` package |
| 02_foundation_model — decoder (all FMs, MLP) | `cstm_scvi_env` | no FM package needed at train time; embeddings are pre-cached |
| 02_foundation_model — scGPT | `reconeval-scgpt` | scgpt's pinned torch/cuda |
| 02_foundation_model — scConcept | `reconeval-scconcept` | concept package + flash-attn |
| 02_foundation_model — SCimilarity | `reconeval-scimilarity` | scimilarity package |
| 03_latent_shift — CellFlow | `pancellflow` | JAX + cellflow |
| 03_latent_shift — STATE | `reconeval-state` | torch + STATE |

## Quick smoke test

A one-iteration sanity run for every driver. See `_smoke.sh` and the per-task
READMEs for details. The minimal forms:

```bash
# 01_end_to_end — PCA on CPU (smallest reproducer)
python experiments/01_end_to_end/codes/train.py \
  model=train/PCA data=pbmc trainer=PCA \
  model.model_args.n_components=10 split=split03

# 02_foundation_model — decoder-only smoke on top of cached FM embeddings
python experiments/02_foundation_model/codes/decoderonly_hvg.py \
  pretrained=SE decoder=MLP data=pbmc decoder.max_epochs=1

# 03_latent_shift — CellFlow on PBMC, 100-iter smoke
python experiments/03_latent_shift/codes/train_cf.py \
  --model PCA_128 --num_iters 100 --batch_size 64 --valid_freq 100
```

See each task's `README.md` for variant lists, CLI override examples and
additional setup notes.
