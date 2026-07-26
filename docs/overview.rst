Overview
========

ReconEval measures how well a latent representation reconstructs the
gene-expression matrix it summarises. The benchmark covers three tasks
(Fig 1c) on three datasets, scored with the same metric set.

Tasks
-----

1. **End-to-end reconstruction.** A single model (PCA, AE, or a VAE
   variant — scVI, nlscVI, mlscVI) encodes expression to a latent space and
   decodes back. The
   latent grid is ``{10, 32, 128, 512, 2048}``.
   Drivers: ``experiments/01_end_to_end/``.
2. **Foundation-model reconstruction.** A frozen FM (SE, scGPT,
   scConcept, SCimilarity) produces per-cell embeddings; a downstream
   MLP, Transformer or KNN decoder maps them back to expression.
   Drivers: ``experiments/02_foundation_model/``.
3. **Latent-shift reconstruction.** Given a control cell's latent state
   and a perturbation covariate, predict the post-perturbation latent
   state and decode it. Two methods: CellFlow (JAX flow matching) and
   STATE (PyTorch transformer over cell sets).
   Drivers: ``experiments/03_latent_shift/``.

Datasets
--------

================  =========================================  ===========================
Dataset           Scope                                      Source
================  =========================================  ===========================
Tahoe-100M        1,137 drugs × 50 cell lines                Arc Institute / Vevo
PBMC-10M          90 cytokines × 12 donors                   Parse Bio
LuCA              6 tissues, 4 diseases                      Human Lung Cancer Atlas
================  =========================================  ===========================

Out-of-distribution splits
--------------------------

Three OOD splits per dataset hold out cell type / line, perturbation,
or condition. The split assignments live under
``data/reconstruction/<dataset>/split0X/``.

Metric families
---------------

The :mod:`sc_reconstruction.metrics` API groups metrics into three
families (Fig 2 / Fig 3):

- **Statistical:** :func:`~sc_reconstruction.metrics.metric_r2`,
  :func:`~sc_reconstruction.metrics.metric_mse`,
  :func:`~sc_reconstruction.metrics.metric_energy_distance`.
- **Biological:** :func:`~sc_reconstruction.metrics.metric_cellcycle`,
  :func:`~sc_reconstruction.metrics.metric_pathway`,
  :func:`~sc_reconstruction.metrics.metric_coexpression`,
  :func:`~sc_reconstruction.metrics.metric_deg`,
  :func:`~sc_reconstruction.metrics.metric_cytokine`.
- **Perturbational:**
  :func:`~sc_reconstruction.metrics.metric_knn_purity`.

:func:`~sc_reconstruction.metrics.compute_all_metrics` runs all of them.
:func:`~sc_reconstruction.metrics.aggregate_rank_percentile` produces
the rank-percentile table, and
:func:`~sc_reconstruction.metrics.funky_heatmap` renders it as the
Fig 3 summary plot.
