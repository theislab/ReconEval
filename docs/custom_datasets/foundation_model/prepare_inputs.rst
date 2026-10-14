.. _custom-data-mlp-data:

Add embeddings and expression targets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`Back to Foundation model <../foundation_model>`

1. Generate embeddings following instructions in :doc:`../../tutorials/fm`.
   Each model requires its own environment (see
   `README <https://github.com/theislab/ReconEval/blob/main/envs/README.md>`_
   in the ReconEval repository)

2. Provide the following files for MLP decoder:

.. code-block:: text

   /path/to/mydata/
   ├── embeddings/
   │   ├── train.zarr/
   │   └── val.zarr/
   ├── all_genes.zarr/
   └── target_genes.zarr/

.. dropdown:: Note: Details on model inputs
   :icon: info
   :color: info

   Each of ``.zarr`` files should contain two arrays: expression and
   embeddings under ``SE``, ``scGPT``, ``scConcept``, or ``SCimilarity``.
