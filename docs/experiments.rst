Experiments
===========

The ``experiments/`` tree contains the training and evaluation pipelines
for the three benchmark tasks. Each task folder has its own Hydra
configs, Python drivers and sbatch wrappers; the per-task ``README.md``
lists the drivers in detail.

.. code-block:: text

    experiments/
    ├── preprocessing/        # PBMC / LuCA / Tahoe data preparation
    ├── 01_end_to_end/        # PCA / AE / VAE (scVI, nlscVI, mlscVI)
    │   ├── codes/            # train.py + eval_*.py
    │   ├── configs/          # Hydra (model/, data/, trainer/, metric/)
    │   └── submit/           # *.sbatch wrappers + pbmc_search.sh sweep
    ├── 02_foundation_model/  # SE / scGPT / scConcept / SCimilarity
    │   ├── codes/            # *_emb.py + decoderonly_hvg(_tsfm).py + eval_decoder_*.py
    │   ├── configs/          # pretrained/, decoder/, model/eval/, data/, metric/
    │   └── submit/           # decoderonly_grid.sbatch
    └── 03_latent_shift/      # CellFlow + STATE perturbation prediction
        ├── codes/            # train_cf.py, train_st.py, eval_cf.py, eval_st.py
        ├── configs/          # cellflow_default.yaml, state_hf_se_parse.yaml, arch/, st/
        └── submit/           # train_cf.sbatch, train_st.sbatch

01 — End-to-end reconstruction
------------------------------

PCA, AE, VAE (scVI, nlscVI, mlscVI variants) across the latent grid
``{10, 32, 128, 512, 2048}`` on PBMC, Tahoe or LuCA.
``submit/pbmc_search.sh`` expands the 5-model × 5-latent grid into
separate jobs.

02 — Foundation-model reconstruction
------------------------------------

Two-step pipeline. An FM-specific embedder writes per-cell embeddings to
zarr (one driver per FM). An FM-agnostic decoder is then trained on top.
The Hydra ``--multirun`` sweep over decoder width / depth is in
``submit/decoderonly_grid.sbatch``.

03 — Latent-shift reconstruction
--------------------------------

CellFlow or STATE predict the post-perturbation latent state, which is
then decoded back to expression. Both methods read the same upstream
embeddings (PCA / AE / VAE (scVI, nlscVI) at multiple latent dims, plus the
four FMs) and condition on a perturbation covariate.

Preprocessing
-------------

``experiments/preprocessing/`` contains the data-prep scripts:

- ``preprocess_pbmc.py`` — PBMC-10M zarr per (cell_type, donor, cytokine).
- ``preprocess_luca.py`` — LuCA split by study / disease / tissue.
- ``tahoe/`` — multi-step Tahoe pipeline driven by
  ``process_pipeline.sh``.

Smoke tests
-----------

``experiments/_smoke.sh`` runs a short sanity check for every driver.
Submit per env via the matching
``experiments/_smoke_logs/smoke_*.sbatch`` wrapper; per-driver outcomes
land in ``experiments/_smoke_logs/REPORT.md``.
