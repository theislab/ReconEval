=========
ReconEval
=========

|paper|  |docs|  |license|  |data|

Benchmark for **gene expression reconstruction** from single-cell latent
representations, covering observational and perturbational tasks.

.. image:: assets/image1.png
   :alt: ReconEval — benchmark overview
   :align: center
   :width: 800

*Fig 1.* (a) Reconstructing latent cell representations. (b) Latent space
modeling under various conditions. (c) Two reconstruction schemes:
stand-alone reconstruction (end-to-end & foundation-model) and latent-shift
reconstruction (perturbation prediction). (d) Experiment space spans three
datasets, three out-of-distribution levels and four hyperparameter axes.
(e) Three metric families: statistical, biological, perturbational.

Documentation
=============

Full documentation, API reference and rendered tutorials at
`reconeval.readthedocs.io <https://reconeval.readthedocs.io>`_.

What ReconEval evaluates
========================

**Latent representations**

* End-to-end: PCA, AE, VAE across latent dims ``{10, 32, 128, 512, 2048}`` and library size handling (None, Modeled, Observed).
* Foundation model embeddings: SE from STATE (2058-d), scGPT (512-d), scConcept (512-d),
  SCimilarity (128-d)

**Decoders**

* MLP, Transformer, KNN

**Datasets**

==============  ========================================  ===========================
Dataset         Scope                                     Source
==============  ========================================  ===========================
Tahoe-100M      1,137 drugs × 50 cell lines               Arc Institute
PBMC-10M        90 cytokines × 12 donors                  Parse Bio
LuCA            6 tissues, 4 diseases         Human Lung Cancer Atlas
==============  ========================================  ===========================

**Out-of-distribution levels** — 3 level of splitting by cell type / cell line, perturbation, condition.

**Metric families** — see *Computing metrics on your own data* below for the API.

* *Statistical* — R², MMD-RBF, energy distance
* *Biological* — DEG recovery, coexpression structure, cell-cycle composition, cytokine response, pathway activity
* *Perturbational* — KNN purity 

System requirements
===================

* Linux (Rocky Linux 9.6 tested); Python 3.12; PyTorch 2.5 + CUDA 12.4.
  Full pins per env in ``envs/*.yaml``.
* An NVIDIA GPU is required for training. Metrics + tutorials run on CPU.

Installation
============

Install time: ~2 min (metrics only), ~30 min (full training env).

.. code-block:: bash

   pip install -r envs/requirements-min.txt        # metrics only
   conda env create -f envs/cstm_scvi_env.yaml     # full training env

Demo
====

Runtime: ~5 min on CPU.

Before running, fetch the small demo fixtures from Hugging Face
(``luca_demo.h5ad``, ``cytokine_act_merged.csv``,
``regev_lab_cell_cycle_genes.txt``) into ``analysis/data/frozen/`` — see
the *Reproducibility* section below.

.. code-block:: bash

   jupyter lab tutorials/metrics.ipynb

Expected output: per-metric scores + a ``funky_heatmap`` figure.

Instructions for use
====================

Metrics on your own ``(true, reconstructed)`` AnnData pair:

.. code-block:: python

   from sc_reconstruction.metrics import compute_all_metrics
   scores = compute_all_metrics(adata_true, adata_pred)

For training: see ``experiments/{01_end_to_end, 02_foundation_model,
03_latent_shift}/README.md``.
Reproduction of paper figures: see *Reproducibility* below.

Tutorials
=========

The metrics notebook walks through each metric on a single
``(true, reconstructed)`` AnnData pair, then shows the rank-percentile
aggregation used to compare methods. The same API applies to all three
benchmark settings in Fig 1c.

============================================================  ============================================================
Notebook                                                      What it covers
============================================================  ============================================================
`tutorials/metrics.ipynb <tutorials/metrics.ipynb>`_          Statistical, biological and perturbational metrics; the
                                                              one-call ``compute_all_metrics``; rank-percentile aggregation.
`tutorials/end_to_end.ipynb <tutorials/end_to_end.ipynb>`_    End-to-end reconstruction: 2-method Protocol, AE reference
                                                              implementation, train → reconstruct → score.
`tutorials/fm.ipynb <tutorials/fm.ipynb>`_                    Foundation-model reconstruction as a two-step pipeline:
                                                              FM-specific embed step + FM-agnostic decoder step.
`tutorials/latent_shift.ipynb <tutorials/latent_shift.ipynb>`_  Latent-shift (perturbation prediction): 2-method
                                                              Protocol, small MLP predictor as reference,
                                                              KNN purity scoring.
============================================================  ============================================================

The analysis notebooks under *Reproducibility* run the same recipe against
the cached paper artefacts.

Experiments
===========

YAML configs and SLURM submission scripts for each benchmark setting are
in ``experiments/``, organised by task:

==============================================  ============================================================
Folder                                          What it contains
==============================================  ============================================================
``experiments/preprocessing/``                  PBMC / LuCA / Tahoe data-preparation scripts.
``experiments/01_end_to_end/``                  PCA / AE / VAE (scVI, nlscVI, mlscVI) reconstruction.
``experiments/02_foundation_model/``            FM (SE, scGPT, scConcept, SCimilarity) embed + decoder train.
``experiments/03_latent_shift/``                CellFlow / STATE latent-shift reconstruction.
==============================================  ============================================================

Each task has its own ``configs/``, ``codes/`` and ``submit/`` tree
(Hydra configs, Python drivers, sbatch wrappers, eval scripts). See
each task's ``README.md`` for env, data and CLI override notes.

Reproducibility
===============

Three notebooks under ``analysis/data/plots/`` reproduce the paper's
figures from cached metric CSVs and lookup tables hosted on
`huggingface.co/datasets/theislab/ReconEval
<https://huggingface.co/datasets/theislab/ReconEval>`_. Download those
into ``analysis/frozen/``; the notebooks write SVGs to
``analysis/figs/figN/``. No model is retrained.

Run them from ``analysis/data/plots/`` so the relative paths
``../frozen/`` and ``../figs/`` resolve.

==========================================================  =====================================================  =============================
Setting (Fig 1c)                                            Notebook                                               Figures produced
==========================================================  =====================================================  =============================
End-to-end reconstruction (PCA / AE / VAE)                  ``analysis/data/plots/fig2_clean.ipynb``               Fig 2 (qualitative + summary + scaling)
Foundation-model reconstruction (frozen FM + decoder)       ``analysis/data/plots/fig3_clean.ipynb``               Fig 3 (FM × decoder × metrics panels)
Latent-shift reconstruction (CellFlow + STATE)              ``analysis/data/plots/fig4_clean.ipynb``               Fig 4 (ST/CF scaling + B-cell spotlight)
==========================================================  =====================================================  =============================

Data availability
=================

* **Reproducibility data**
  — `huggingface.co/datasets/theislab/ReconEval
  <https://huggingface.co/datasets/theislab/ReconEval>`_

Update: Model weights uploaded

Paper
=====

Preprint: `available here! <https://www.biorxiv.org/content/early/2026/06/18/2026.06.15.731445>`_

Citation
========

.. code-block:: text

   @article{Fu2026.06.15.731445,
	author = {Fu, Xiaotong and Klein, Dominik and Antipov, Egor and Palma, Alessandro and Tejada-Lapuerta, Alejandro and Bahrami, Mojtaba and K{\"u}mmerle, Louis B. and Lubetzki, Manuel and Casale, Francesco Paolo and Luecken, Malte D. and Theis, Fabian J.},
	title = {Benchmarking gene expression reconstruction from single-cell latent representations},
	elocation-id = {2026.06.15.731445},
	year = {2026},
	doi = {10.64898/2026.06.15.731445},
	publisher = {Cold Spring Harbor Laboratory},
	URL = {https://www.biorxiv.org/content/early/2026/06/18/2026.06.15.731445},
	eprint = {https://www.biorxiv.org/content/early/2026/06/18/2026.06.15.731445.full.pdf},
	journal = {bioRxiv}
	}


License
=======

MIT — see ``LICENSE``.


.. |paper|   image:: https://img.shields.io/badge/paper-TBD-lightgrey.svg
.. |docs|    image:: https://readthedocs.org/projects/reconeval/badge/?version=main
   :target: https://reconeval.readthedocs.io/en/main/
.. |license| image:: https://img.shields.io/badge/license-MIT-blue.svg
   :target: https://opensource.org/licenses/MIT
.. |data|    image:: https://img.shields.io/badge/data-🤗-yellow.svg
   :target: https://huggingface.co/datasets/theislab/ReconEval
