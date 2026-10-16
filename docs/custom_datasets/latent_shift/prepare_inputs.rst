.. _custom-data-latent-inputs:

Add expression, embeddings, and conditions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`Back to Latent shift <../latent_shift>`

1. Choose a representation and width from the training script's ``EMB_DIMS``
   and prepare the corresponding embeddings (e.g. ``AE_128``)
2. Provide the following files for STATE and CellFlow:

.. code-block:: text

   /path/to/mydata/
   ├── train/train.h5ad
   ├── val/val.h5ad
   └── test/test.h5ad

.. dropdown:: Note: Details on latent shift inputs
   :icon: info
   :color: info

   Each ``.h5ad`` file should contain:

   - Expression in ``.X`` and embeddings in ``.obsm["X_AE_128"]`` (for ``AE_128``),
     with matching cell order. Expression genes must follow the order expected
     by the decoder
   - Metadata in ``.obs["donor"]``, ``.obs["cell_type"]``, and
     ``.obs["target_gene"]``
   - Controls labelled ``PBS`` in ``.obs["target_gene"]`` for the
     donor/cell-type groups being predicted

   Adapt the metadata keys and control labels to your dataset.
