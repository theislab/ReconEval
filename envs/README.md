# envs/

Reproducible conda environment files for each runtime in the ReconEval
benchmark. Foundation models ship mutually-incompatible dep stacks
(different torch / CUDA / flash-attn combos), so each FM gets its own
env.

| File | Purpose | Drivers / Tutorials |
|---|---|---|
| `cstm_scvi_env.yaml` | End-to-end models (PCA, AE, VAE (scVI, nlscVI, mlscVI)), MLP decoder, STATE training | `experiments/01_end_to_end/codes/*`, `02_foundation_model/codes/decoderonly_hvg.py`, `train_decoder_from_embedding.py`, `03_latent_shift/codes/train_st.py`, all tutorials |
| `state_env.yaml` | STATE (SE) FM embed | `02_foundation_model/codes/SE_emb*.py` |
| `scgpt.yaml` | scGPT FM embed | `02_foundation_model/codes/scGPT_emb.py` |
| `scconcept_env.yaml` | scConcept FM embed + Transformer decoder | `02_foundation_model/codes/scConcept_emb.py`, `decoderonly_hvg_tsfm.py` |
| `scimilarity_env.yaml` | SCimilarity FM embed | `02_foundation_model/codes/scimilarity_emb.py` |
| `pancellflow.yaml` | CellFlow training + eval (JAX) | `03_latent_shift/codes/train_cf.py`, `eval_cf.py` |
| `requirements-min.txt` | Metrics + tutorials only — no torch / FMs, pip-only | `tutorials/metrics.ipynb` |

## Quick start

```bash
# Reproduce the metrics tutorial without any GPU / FM dependencies:
pip install -r envs/requirements-min.txt

# Full end-to-end stack (most users want this):
conda env create -f envs/cstm_scvi_env.yaml

# FM-specific envs as needed (each FM has its own to avoid torch/CUDA conflicts):
conda env create -f envs/state_env.yaml       # STATE / SE FM
conda env create -f envs/scgpt.yaml
conda env create -f envs/scconcept_env.yaml
conda env create -f envs/scimilarity_env.yaml

# Latent-shift (CellFlow + STATE):
conda env create -f envs/pancellflow.yaml
```

## Provenance

Each yaml was derived from a `pip list` of the corresponding live
environment on the IT-CB cluster (snapshot date 2026-06-08), narrowed to
only the packages actually imported by the public source under
`src/sc_reconstruction/` and `experiments/`. GPU-only RAPIDS packages
(`cudf-cu12`, `cuml-cu12`, …) are pinned in `cstm_scvi_env.yaml` because
`ReconPCA` uses `dask_cuda.LocalCUDACluster`; on a CPU-only host those
deps can be dropped if you skip PCA training.
