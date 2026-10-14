.. _custom-data-cellflow-cli:

Run CellFlow from CLI
~~~~~~~~~~~~~~~~~~~~~

:doc:`Back to Latent shift <../latent_shift>`

For cluster submission, follow :ref:`Run through SLURM <slurm-parameters>`.

**Run CellFlow:**

1. Activate ``reconeval-pancellflow`` from the
   :ref:`installation step <custom-data-installation>`

2. In ``experiments/03_latent_shift/codes/train_cf.py``, set ``DATA_ROOT``
   to ``/path/to/mydata`` and adapt the metadata/control labels if needed

3. In ``train_cf.py``, update the block that calls ``hf_hub_download()``
   with ``filename="pbmc_parse.h5ad"`` and reads ``uns/esm2_embeddings``
   to load your dataset's perturbation features. Retain a vector for every
   non-control perturbation across all splits, including any absent from
   training. Validation/test donor and cell-type labels must occur in the
   training categories

4. Set the representation and output directory, then train CellFlow.
   For ``AE_128`` embeddings:

   .. code-block:: bash

      python experiments/03_latent_shift/codes/train_cf.py \
        --model AE_128 \
        --config repro \
        --num_iters 500000 \
        --batch_size 1024 \
        --valid_freq 50000 \
        --out_dir /path/to/results/mydata/cellflow

**Required inputs and common optional settings:**

.. dropdown:: Table: Training parameters
   :icon: table
   :color: primary

   .. csv-table::
      :header: "Flag", "Required / optional", "Meaning"
      :widths: 30, 30, 40

      "``--model``", "Required", "Representation listed in EMB_DIMS, e.g. AE_128"
      "``--config``", "Optional; default: repro", "Training preset: repro or paper"
      "``--num_iters``", "Optional; default: 500000", "Training iterations"
      "``--batch_size``", "Optional; default: 1024", "Cells per batch"
      "``--valid_freq``", "Optional; default: 50000", "Validation interval in iterations"
      "``--seed``", "Optional; default: 42", "Random seed"
      "``--out_dir``", "Optional; default: generated under out_root", "Exact run output directory; set a writable path for your run"
      "``--out_root``", "Optional; default: script's OUT_ROOT", "Output root used when out_dir is omitted"

.. dropdown:: Note: CellFlow validation metrics
   :icon: info
   :color: info

   During training, metrics labelled ``test`` are computed on ``val/val.h5ad``.
