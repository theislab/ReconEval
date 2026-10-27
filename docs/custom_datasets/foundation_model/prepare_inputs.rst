.. _custom-data-mlp-data:

Prepare inputs
~~~~~~~~~~~~~~

:doc:`Back to Foundation model <../foundation_model>`

For general preprocessing of lightweight datasets with ``prepare_dataset.py``,
see :doc:`Data preparation <../dataset_preparation>`.

Extraction of embeddings
^^^^^^^^^^^^^^^^^^^^^^^^

To extract embeddings using pretrained foundation models, provide:

- a grouped expression store
- split metadata

Place both stores under your dataset directory:

.. code-block:: text

   /path/to/mydata/
   ├── expression_for_fm.zarr/
   │   ├── <group>/
   │   │   └── X          # cells × genes
   │   ├── ...            # other groups
   │   ├── .zattrs        # gene metadata
   │   └── .zgroup        # Zarr format information
   └── split_metadata.zarr/
       ├── .zattrs        # train/val/test group-name lists
       └── .zgroup        # Zarr format information

.. dropdown:: Note: Split selection
   :icon: info
   :color: info

   Set ``data_args.target_key`` to ``null`` in the extraction configuration
   to select groups from all three split lists. To select only test groups,
   set it to ``test_combinations``.

**Expression**

Group cells by ``data.split_key`` joining their values
with ``-`` to name each group:

.. csv-table::
   :header: "Dataset", "Grouping fields", "Example group name"
   :widths: 15, 45, 40

   "LuCA", "``[cell_type, dataset, origin]``", "``T_cell-study1-tumor``"
   "PBMC", "``[cell_type, donor, cytokine]``", "``T_cell-donor1-PBS``"
   "Tahoe", "``[cell_line, drug, dosage]``", "``cell_line1-drug_A-1``"

Expression store includes:

- ``<group>/X``: cells-by-genes expression
- ``.zattrs``: gene identifiers in the same order as the columns of ``X``
- ``.zgroup``: Zarr format information

All groups must use the same gene columns in the same order.


.. dropdown:: Examples: metadata files
   :color: primary

   .. tab-set::

      .. tab-item:: .zattrs

         Gene names and Ensembl IDs in ``X`` column order (placeholders):

         .. code-block:: json

            {
              "var_names": ["GENE_A", "GENE_B"],
              "var_ensembl_ids_38": ["ENSEMBL_ID_A", "ENSEMBL_ID_B"]
            }

         The scConcept example uses ``var_ensembl_ids_38``; the other
         examples use ``var_names``.

      .. tab-item:: .zgroup

         Zarr format version 2:

         .. code-block:: json

            {
              "zarr_format": 2
            }

**Split metadata**

Create ``split_metadata.zarr`` using the Zarr library. It should contain:

- ``.zattrs`` (group-name lists):

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

         Each listed name must match a group in ``expression_for_fm.zarr``.

      .. tab-item:: .zgroup

         Zarr format version 2:

         .. code-block:: json

            {
              "zarr_format": 2
            }

For different split definitions, reuse the expression store and create
separate split metadata.

.. _custom-data-fm-decoder-training-inputs:

Decoder training
^^^^^^^^^^^^^^^^

Provide training and validation expression with matching embeddings.
See :doc:`Combine expression and embeddings <combine_embeddings>` to create
these stores:

.. code-block:: text

   /path/to/mydata/
   ├── embeddings/
   │   └── <model>/
   │       ├── train.zarr/
   │       │   ├── X                  # cells × expression genes
   │       │   └── <embedding_key>    # same cells × embedding dimensions
   │       └── val.zarr/
   │           ├── X
   │           └── <embedding_key>
   ├── all_genes.zarr/                # root var_names attribute
   └── target_genes.zarr/             # root var_names attribute

Replace ``<model>`` and ``<embedding_key>`` with ``SE``, ``scGPT``,
``scConcept``, or ``scimilarity``.

- ``all_genes.zarr.attrs["var_names"]``: all expression genes in ``X`` column order
- ``target_genes.zarr.attrs["var_names"]``: selected genes in decoder output order

Reference PCA
^^^^^^^^^^^^^

Reuse a reference PCA or fit a new one; see :doc:`reference PCA <reference_pca>`.

Evaluation
^^^^^^^^^^

To run evaluation, provide:

- a grouped expression store
- a grouped embedding store
- split metadata

Place these stores under your dataset directory:

.. code-block:: text

   /path/to/mydata/
   ├── expression.zarr/
   │   ├── <group>/
   │   │   ├── X              # cells × target genes
   │   │   └── obs_index      # optional cell IDs
   │   ├── ...                # other groups
   │   ├── .zattrs            # target gene names (var_names)
   │   └── .zgroup            # Zarr format information
   ├── embeddings/
   │   └── <model>/
   │       └── grouped.zarr/
   │           ├── <group>/
   │           │   └── X      # same cells × embedding dimensions
   │           ├── ...        # other groups
   │           └── .zgroup    # Zarr format information
   └── split_metadata.zarr/
       ├── .zattrs            # train/val/test group-name lists
       └── .zgroup            # Zarr format information

**Expression**

Group cells by ``data.split_key``, joining their values with ``-``
to name each group.

Expression store includes:

- ``<group>/X``: cells-by-target-genes expression
- ``<group>/obs_index``: optional cell IDs in matching row order
- ``.zattrs``: ``var_names`` in expression-column and decoder-output order
- ``.zgroup``: Zarr format information

Use the same expression preprocessing as for decoder training.

.. dropdown:: Examples: metadata files
   :color: primary

   .. tab-set::

      .. tab-item:: .zattrs

         .. code-block:: json

            {
              "var_names": ["GENE_A", "GENE_B"]
            }

      .. tab-item:: .zgroup

         Zarr format version 2:

         .. code-block:: json

            {
              "zarr_format": 2
            }

**Embeddings**

Store grouped embeddings in
``embeddings/<model>/grouped.zarr``:

- ``<group>/X``: cells-by-embedding-dimensions matrix
- ``.zgroup``: Zarr format information, see the example above

**Split metadata**

Reuse the split metadata prepared for extraction. It contains:

- ``.zattrs``: ``train_combinations``, ``val_combinations``, and
  ``test_combinations``
- ``.zgroup``: Zarr format information

Each group selected for evaluation must exist in both the expression
and embedding stores.

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

.. dropdown:: Note: Held-out evaluation
   :icon: info
   :color: info

   Set ``train_fraction=0`` and ``test_fraction=1`` to evaluate only
   groups listed in ``test_combinations``.

   Evaluation reads the grouped stores, not ``train.zarr`` or ``val.zarr``.

Data configuration
^^^^^^^^^^^^^^^^^^

See :doc:`Data configuration <data_configuration>` for the data settings
used during embedding extraction, decoder training, and evaluation.
