Data preparation
================

:doc:`Back to Custom data <../custom_datasets>`

To prepare lightweight datasets that fit in memory, use ``experiments/preprocessing/prepare_dataset.py``.

What the script does
--------------------

- Reads an ``.h5ad`` file with expression in ``.X`` or the selected layer
- Normalizes each cell to ``1e4`` total counts and applies ``log1p`` (optional)
- Selects highly variable genes
- Groups cells using the selected keys in ``.obs`` and names each group by joining their cleaned values with ``-``
- Creates train, validation, and test splits, or reuses existing splits
- Shuffles the training split and annotates train, validation, and test splits with ``library_log_mean`` & ``library_log_var``

Prepare your inputs
-------------------
Use:

- ``.h5ad`` file
- ``split_metadata.zarr`` (optional)

Configure
-----------

Create ``experiments/preprocessing/configs/data/mydata.yaml`` using ``configs/base.yaml``; replace the paths, grouping columns and other parameters with your own values:

.. code-block:: yaml

   # @package _global_
   defaults:
     - /base
     - _self_

   input: /path/to/input.h5ad
   output: /path/to/mydata
   hvg:
     method: n_top_genes
     n_top_genes: 2000
   layer: null                 # .X, or the name of a layer
   columns: [???, ????, ???]
   var_names_col: null          # .var_names, or the name of a .var column
   split:
     strategy: combination
     train_ratio: 0.7
     val_ratio: 0.15
   seed: 42
   demo: false
   demo_cells: 500
   utils: null

**HVG method**

- ``n_top_genes``: select a fixed number of genes with ``hvg.n_top_genes``
- ``dispersion``: select genes using thresholds set by ``hvg.min_mean``,
  ``hvg.max_mean``, and ``hvg.min_disp``
- ``precomputed``: use existing annotations in the ``.var`` column specified by ``hvg.column``

**Split strategy**

- ``combination``: split by group
- ``category``: split by a selected grouping key
- ``read``: reuse existing split assignments

**Additional settings**

- ``train_ratio`` & ``val_ratio``: set proportions for training and validation; the remaining data forms the test split
- ``seed``: random seed for reproducible sampling and splits
- ``demo``: randomly sample cells before preprocessing (default: ``false``)
- ``demo_cells``: maximum number of sampled cells in demo mode (default: ``500``)

See ``configs/data/luca.yaml`` and ``configs/data/pbmc.yaml`` for examples.
Optionally, use ``utils`` for custom preprocessing and postprocessing.

Run
---------------

Follow :doc:`Environment setup <prerequisites>` and activate the ``reconeval`` environment. 

From ``experiments/preprocessing``, run:

.. code-block:: bash

   python prepare_dataset.py --config-name data/mydata

Override individual settings with CLI:

.. code-block:: bash

   python prepare_dataset.py --config-name data/mydata \
     input=/path/to/input_new.h5ad \
     output=/path/to/mydata_new

Run a demo with the usage of a new output directory:

.. code-block:: bash

   python prepare_dataset.py --config-name data/mydata \
     demo=true \
     demo_cells=500 \
     split.strategy=combination \
     output=/path/to/mydata_demo

Outputs
-------

The outputs of ``prepare_dataset.py`` are inputs for **end-to-end** training and
evaluation. The script saves them as Zarr files in the directory specified by
``output``:

.. code-block:: text

   /path/to/mydata/
   ├── expression.zarr/
   │   ├── <group>/
   │   │   ├── X
   │   │   └── obs_index
   │   └── ...
   ├── train.zarr/
   │   └── X
   ├── val.zarr/
   │   └── X
   ├── test.zarr/
   │   └── X
   ├── split_metadata.zarr/
   │   └── ...
   └── ...

Additionally:

- use ``zarr_to_h5ad.py`` to create ``.h5ad`` inputs for PCA
- use ``expression.zarr`` for embedding extraction

**Foundation model** and **latent shift** workflows require additional preparation.

For task-specific input details, see:

- :doc:`End-to-end reconstruction <end_to_end/prepare_inputs>`
- :doc:`Foundation model <foundation_model/prepare_inputs>`
- :doc:`Latent shift <latent_shift/prepare_inputs>`
