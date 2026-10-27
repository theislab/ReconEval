Prepare inputs
~~~~~~~~~~~~~~

:doc:`Back to End-to-end reconstruction <../end_to_end>`

This page describes the input formats required by the end-to-end workflow.
For general preprocessing of lightweight datasets with ``prepare_dataset.py``,
see :doc:`Data preparation <../dataset_preparation>`.

.. _custom-data-e2e-training-inputs:

Training
^^^^^^^^

- For AE and scVI variants, provide one cells-by-genes matrix per
  split, stored as a Zarr array or under ``X``:

  .. code-block:: text

     /path/to/mydata/
     ├── train.zarr
     ├── val.zarr
     └── test.zarr

- PCA instead reads ``train.h5ad`` from the same directory, with expression
  stored as a CSR matrix in ``.X``

.. _custom-data-e2e-reference-pca-inputs:

Reference PCA
^^^^^^^^^^^^^

Combine measured training, validation, and test expression in
``/path/to/mydata/reference.h5ad``, including each cell once.
Store a cells-by-genes CSR matrix in ``.X``, preserving evaluation
preprocessing and gene order.

Use this file only to fit the reference PCA.

.. _custom-data-e2e-eval-inputs:

Evaluation
^^^^^^^^^^

In order to run evaluation, provide following data:

- a grouped expression store
- split metadata

Place both under your dataset directory:

.. code-block:: text

  /path/to/mydata/
  ├── expression.zarr/
  │   ├── <group>/
  │   │   ├── X          # cells × genes
  │   │   └── obs_index  # optional cell IDs
  │   ├── ...            # other groups
  │   ├── .zattrs        # gene metadata, including var_names
  │   └── .zgroup        # Zarr format information
  ├── split_metadata.zarr/
  │   ├── .zattrs        # train/val/test group-name lists
  │   └── .zgroup        # Zarr format information
  └── ...                # train.zarr, val.zarr, test.zarr (Optional)


.. dropdown:: Note: Held-out evaluation parameters
   :icon: info
   :color: info

   For held-out evaluation set ``train_fraction=0`` and ``test_fraction=1`` in configuration 
   to evaluate only groups listed in ``test_combinations``.

.. dropdown:: Note: Evaluation expression data
   :icon: info
   :color: info

   Expression is loaded from ``expression.zarr/<group>/X``; and 
   ``train.zarr``, ``val.zarr``, ``test.zarr`` are not used for evaluation.

**Expression**

Group cells by ``data.split_key`` joining the values with the ``-`` symbol to name each group:


.. csv-table::
   :header: "Dataset", "``data.split_key``", "Example group name"
   :widths: 15, 45, 40

   "LuCA", "``[cell_type, dataset, origin]``", "``T_cell-study1-tumor``"
   "PBMC", "``[cell_type, donor, cytokine]``", "``T_cell-donor1-PBS``"
   "Tahoe", "``[cell_line, drug, dosage]``", "``cell_line1-drug_A-1``"

Expression store includes:

- ``<group>/X``: cells-by-genes expression
- ``<group>/obs_index``: optional cell IDs in matching row order
- ``var_names`` in ``.zattrs``: gene names in the same order as the columns
  of ``X``, used for biological evaluation
- ``.zgroup``: Zarr format information

.. dropdown:: Examples: metadata files
   :color: primary

   .. tab-set::

      .. tab-item:: <group>/obs_index

         Optional cell IDs for the corresponding rows of ``X``:

         .. code-block:: text

            ["cell_001", "cell_002", "cell_003"]

         The number of IDs must equal the number of rows in ``X``, in
         matching order.

      .. tab-item:: .zattrs

         Placeholder gene names for the corresponding columns of ``X``:

         .. code-block:: json

            {
              "var_names": ["GENE_A", "GENE_B", "GENE_C"]
            }

      .. tab-item:: .zgroup

         Zarr format version 2:

         .. code-block:: json

            {
              "zarr_format": 2
            }

**Split metadata**

Create ``split_metadata.zarr`` using the Zarr library. It should contain:

- ``.zattrs`` (train/val/test group-name lists):

  - ``train_combinations``
  - ``val_combinations``
  - ``test_combinations``

- ``.zgroup``: Zarr format information

.. dropdown:: Examples: split metadata files
   :color: primary

   .. tab-set::

      .. tab-item:: .zattrs

         .. code-block:: json

            {
              "train_combinations": ["T_cell-study1-tumor"],
              "val_combinations": ["T_cell-study2-tumor"],
              "test_combinations": ["T_cell-study3-tumor"]
            }

      .. tab-item:: .zgroup

         Zarr format version 2:

         .. code-block:: json

            {
              "zarr_format": 2
            }

For different split definitions, reuse the expression
store and recreate separate split metadata.

.. _custom-data-e2e-embedding-inputs:

Embedding extraction
^^^^^^^^^^^^^^^^^^^^
Use your trained model to obtain embeddings from ``expression.zarr`` prepared in :ref:`Evaluation inputs <custom-data-e2e-eval-inputs>`.
The extractor processes all groups in the store; split metadata is not required.

.. _custom-data-e2e-data-config:

Data configuration
^^^^^^^^^^^^^^^^^^

After preparing the files, copy
``experiments/01_end_to_end/configs/data/template.yaml`` to
``experiments/01_end_to_end/configs/data/mydata.yaml``. Set these top-level
fields and retain the ``model_specific`` dataloader settings:

.. code-block:: yaml

   name: mydata
   path: /path/to/mydata  # directory containing the split files
   input_dim: 2000        # number of genes

   # Set these fields for evaluation
   eval_path: /path/to/mydata/expression.zarr
   split_comb: /path/to/mydata/split_metadata.zarr
   split_key: 
     - ??? # cell_type
     - ??? # dataset
     - ??? # origin

``split_key`` comments use the LuCA example above; replace ``???`` with the fields
and order used to name your groups.

Select this configuration with ``data=mydata`` when running the scripts.
