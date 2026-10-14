.. _custom-data-mlp-cli:

Run from CLI
~~~~~~~~~~~~

:doc:`Back to Foundation model <../foundation_model>`

For cluster submission, follow :ref:`Run through SLURM <slurm-parameters>`.

**Run the MLP decoder:**

1. Activate ``reconeval`` defined in :ref:`installation step <custom-data-installation>`

2. Set the paths and embedding key, then train the decoder. Decoder training does not require YAML configuration file. For ``SE`` embeddings:

   .. code-block:: bash

      python experiments/02_foundation_model/codes/train_decoder_from_embedding.py \
        --emb-train-zarr /path/to/mydata/embeddings/train.zarr \
        --emb-val-zarr /path/to/mydata/embeddings/val.zarr \
        --all-genes-zarr /path/to/mydata/all_genes.zarr \
        --target-genes-zarr /path/to/mydata/target_genes.zarr \
        --embedding-key SE \
        --num-workers 0 \
        --epochs 500 \
        --out /path/to/results/mydata/SE/MLP

**Required inputs and common optional settings:**

.. dropdown:: Table: Training parameters
   :icon: table
   :color: primary

   .. csv-table::
      :header: "Flag", "Required / optional", "Meaning"
      :widths: 30, 30, 40

      "``--emb-train-zarr``", "Required", "Training store containing expression and embeddings"
      "``--emb-val-zarr``", "Required", "Validation store containing expression and embeddings"
      "``--all-genes-zarr``", "Required", "Store whose var_names attribute lists the expression columns in order"
      "``--target-genes-zarr``", "Required", "Store whose var_names attribute lists the genes to reconstruct"
      "``--embedding-key``", "Required", "Embedding array name: SE, scGPT, scConcept, or scimilarity"
      "``--out``", "Required", "Output directory for checkpoints and configuration"
      "``--epochs``", "Optional; default: 500", "Maximum training epochs"
      "``--batch-size``", "Optional; default: 256", "Cells per batch"
      "``--lr``", "Optional; default: 0.0001", "Learning rate"
      "``--n-layers``", "Optional; default: 1", "Number of hidden layers"
      "``--hidden``", "Optional; default: 4096", "Hidden-layer width"
      "``--num-workers``", "Optional; default: 16", "Data-loading workers; use 0 to load data in the main process"
      "``--seed``", "Optional; default: 42", "Random seed"

