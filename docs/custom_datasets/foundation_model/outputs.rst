Outputs
~~~~~~~

:doc:`Back to Foundation model <../foundation_model>`

**Model files.**

Training saves model outputs in the directory specified by ``--out``,
such as ``/path/to/results/mydata/SE/MLP/``.

- **MLP:** a ``.ckpt`` checkpoint with the lowest validation loss

**Logs and configuration.**

- ``config.yaml`` in the same directory records the run settings, including
  the embedding dimension (``latent_dim``) and number of output genes
  (``gene_dim``)
