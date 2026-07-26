Reproducibility
===============

Three notebooks under ``analysis/data/plots/`` reproduce the paper
figures from cached metric CSVs. No model is retrained.

==============================================================  ==========================================
Setting (Fig 1c)                                                Notebook
==============================================================  ==========================================
End-to-end reconstruction (PCA / AE / VAE)                      ``analysis/data/plots/fig2_clean.ipynb``
Foundation-model reconstruction (frozen FM + decoder)           ``analysis/data/plots/fig3_clean.ipynb``
Latent-shift reconstruction (CellFlow + STATE)                  ``analysis/data/plots/fig4_clean.ipynb``
==============================================================  ==========================================

Cached artefacts
----------------

The metric CSVs and lookup tables consumed by the biological metrics
are hosted at |hf_link|. Download them into ``analysis/frozen/`` before
running the notebooks. The notebooks use paths relative to
``analysis/data/plots/`` (``../frozen/`` and ``../figs/<fig>/``), so
run them from that directory.

.. |hf_link| raw:: html

   <a href="https://huggingface.co/datasets/theislab/ReconEval" target="_blank">huggingface.co/datasets/theislab/ReconEval</a>

Funky-map helper
----------------

The plotting helper that produces the rank-percentile funky map (the
Fig 3 summary) is available as
:func:`sc_reconstruction.metrics.funky_heatmap`. The analysis notebooks
keep their own variants for paper-specific styling, but library users
can produce the same layout with one call on the score DataFrame.
