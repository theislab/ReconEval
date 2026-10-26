ReconEval
=========

.. module:: sc_reconstruction

Benchmark for gene-expression reconstruction from single-cell latent
representations. The package contains:

- a metrics API that scores a ``(true, reconstructed)``
  :class:`anndata.AnnData` pair (statistical, biological, perturbational);
- four tutorial notebooks covering the three benchmark settings;
- training and eval pipelines under ``experiments/`` with Hydra configs
  and sbatch wrappers;
- analysis notebooks under ``analysis/`` that reproduce the paper figures
  from cached metric CSVs.

.. grid:: 1 2 3 3
    :gutter: 2

    .. grid-item-card:: Install
        :link: installation
        :link-type: doc

        ``pip install -e .`` for the metrics API; conda env for the
        full benchmark.

    .. grid-item-card:: Tutorials
        :link: tutorials/index
        :link-type: doc

        Metrics, end-to-end, foundation-model and latent-shift
        reconstruction notebooks.

    .. grid-item-card:: API reference
        :link: api/index
        :link-type: doc

        Public functions and classes in ``sc_reconstruction``.

    .. grid-item-card:: Experiments
        :link: experiments
        :link-type: doc

        Training drivers, eval scripts, sbatch wrappers and Hydra
        configs per task.

    .. grid-item-card:: Reproducibility
        :link: reproducibility
        :link-type: doc

        Analysis notebooks that reproduce the paper figures.

    .. grid-item-card:: Manuscript
        :link: https://example.org/preprint
        :link-type: url

        Preprint: TBD.

.. toctree::
    :maxdepth: 2
    :hidden:

    installation
    custom_datasets
    overview
    tutorials/index
    api/index
    experiments
    reproducibility
    references
