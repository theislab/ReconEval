# 01_end_to_end — full-gene reconstruction

Trains five end-to-end reconstruction models — **PCA**, **AE** and three
VAE variants (**scVI**, **nlscVI**, **mlscVI**) — across the latent grid `{10, 32, 128, 512, 2048}`
on PBMC, Tahoe or LuCA. The decoder is trained jointly with the encoder.

## Layout

```
01_end_to_end/
├── configs/
│   ├── base_train.yaml       # root config (used by train.py)
│   ├── model/train/
│   │   ├── PCA.yaml
│   │   ├── AE.yaml
│   │   ├── scVI.yaml
│   │   ├── nlscVI.yaml
│   │   └── mlscVI.yaml
│   ├── data/
│   │   ├── pbmc.yaml
│   │   ├── tahoe.yaml
│   │   └── luca.yaml
│   └── trainer/
│       ├── PCA.yaml
│       ├── AE.yaml
│       └── scVI.yaml         # also used by nlscVI + mlscVI
├── codes/
│   ├── train.py              # Hydra @hydra.main(config_name=base_train)
│   ├── extract_e2e_embeddings.py  # post-hoc encoder.embed(adata)
│   ├── eval_recon_knn.py     # KNN-based reconstruction scoring (Hydra base_metrics_sampled)
│   ├── eval_biological.py    # biological metric family on saved checkpoints
│   └── eval_distributional.py # statistical metric family on saved checkpoints
└── submit/
    ├── train_pca.sbatch
    ├── train_ae.sbatch
    ├── train_scvi.sbatch
    └── pbmc_search.sh        # latent-size grid sweep (wraps the 3 sbatchs)
```

## Eval drivers

Three eval scripts score a trained model's outputs against the metric
families in `tutorials/metrics.ipynb`:

| Driver | Hydra root | Family |
|---|---|---|
| `eval_recon_knn.py` | `base_metrics_sampled` | KNN baseline R²/MSE/MMD/energy |
| `eval_biological.py` | `base_eval` | cellcycle, pathway, coexpression, DEG, cytokine |
| `eval_distributional.py` | `base_eval` | R², MSE, energy distance over the test combination split |

Each driver expects a trained checkpoint produced by `train.py` and a
metric subgroup (`configs/metric/*.yaml`). Example:

```bash
python experiments/01_end_to_end/codes/eval_distributional.py \
  data=pbmc split=split03 model=train/AE +metric=_distributional
```

## CLI

`train.py` is Hydra-driven:

```bash
python experiments/01_end_to_end/codes/train.py \
  model=train/<PCA|AE|scVI|nlscVI|mlscVI> \
  data=<pbmc|tahoe|luca> \
  trainer=<PCA|AE|scVI> \
  model.model_args.{n_components,n_latent}=<dim> \
  split=<split01|split02|split03> \
  trainer.max_epochs=400 trainer.min_epochs=10
```

`trainer=scVI` is the right trainer for scVI, nlscVI and mlscVI (matches
the private repo). PCA uses `n_components`, AE/scVI/nlscVI/mlscVI use
`n_latent`. mlscVI is a multi-layer scVI variant — see
`configs/model/train/mlscVI.yaml` for the `n_layers` default.

## Sbatch wrappers

Each is parametric via env vars. Submit one job:

```bash
sbatch --export=ALL,LATENT=128,DATA=pbmc,SPLIT=split03 \
       experiments/01_end_to_end/submit/train_ae.sbatch
```

| Env var | Default | Notes |
|---|---|---|
| `DATA` | `tahoe` | one of `pbmc`, `tahoe`, `luca` |
| `SPLIT` | `split03` | one of `split01`, `split02`, `split03` |
| `LATENT` | `128` | latent dim; auto-mapped to `n_components` or `n_latent` |
| `MAX_EPOCHS` | `400` (AE), `200` (scVI) | trainer cap |
| `MIN_EPOCHS` | `10` (AE), `1` (scVI) | trainer floor |

## Sweep

`submit/pbmc_search.sh` submits one job per (model, latent) cell of the
grid. Overrides via env vars:

```bash
MODELS="PCA AE scVI nlscVI" LATENTS="10 32 128 512 2048" DATA=pbmc \
  bash experiments/01_end_to_end/submit/pbmc_search.sh
```

(Defaults to the full 4 × 5 = 20-job grid on PBMC, split03.)

## Quick smoke test

PCA on CPU (smallest path, no GPU needed):

```bash
conda activate cstm_scvi_env
RECONEVAL_OUT=/tmp/reconeval_smoke \
python experiments/01_end_to_end/codes/train.py \
  model=train/PCA data=pbmc trainer=PCA \
  model.model_args.n_components=10 split=split03
```

Expected output: a PCA weights file under
`${RECONEVAL_OUT}/weights/pbmc/split03/PCA/Default/<filename>.pt`.

## Conda env

| Env | Used for |
|---|---|
| `cstm_scvi_env` | All four models — torch + scvi-tools. |
