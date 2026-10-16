Outputs
~~~~~~~

:doc:`Back to Latent shift <../latent_shift>`

**Model files**

- **STATE:** saves models under ``<out_root>/<run_name>/checkpoints/``,
  including the three best validation checkpoints, ``last.ckpt``, and
  ``final.ckpt``. The run name retains ``pbmc_split03`` even for custom
  data. An existing ``last.ckpt`` is used to resume training automatically
- **CellFlow:** saves the best and last CellFlow model artifacts in the
  directory specified by ``--out_dir``. The best model is selected using
  validation data

Set ``--out_root`` for STATE and ``--out_dir`` for CellFlow to writable
paths, as in the CLI examples. Their defaults use cluster-specific paths;
``RECONEVAL_OUT`` does not redirect these outputs.

**Logs and configuration**

- **STATE:** ``config.yaml`` and label mappings are saved in the run
  directory, alongside ``checkpoints/``
- **CellFlow:** ``config.json``, ``training_logs.json``, and
  ``training_curves.png`` are saved in the output directory
