Train
~~~~~

:doc:`Back to End-to-end reconstruction <../end_to_end>`

Configure
^^^^^^^^^

**Data**

Use the :ref:`dataset configuration <custom-data-e2e-data-config>`.

**Model**

Choose a model:

- **AE variants:** **AE** (no library-size), **mlAE** (modeled library size), **olAE** (observed library size)
- **VAE variants:** **nlscVI** (no library-size), **mlscVI** (modeled library size), **scVI** (observed library size)
- **PCA**

For a custom model, see `Bringing your own model <../../tutorials/end_to_end.html#bringing-your-own-model>`_

**Parameters**

Set parameters in YAML or pass ``key=value`` overrides on the CLI.

.. dropdown:: Table: Training parameters
   :icon: table
   :color: primary

   .. tab-set::

      .. tab-item:: Run

         YAML: ``base_train.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``data``", "Required", "Dataset configuration, e.g. ``mydata``"
            "``model``", "Required", "Training configuration: ``train/<model>``; use ``train/AE`` for all AE variants"
            "``trainer``", "Required", "``AE`` for AE variants; ``scVI`` for all VAE variants; ``PCA`` for PCA"
            "``seed``", "Optional; default: ``42``", "Random seed"
            "``split``", "Optional; default: ``split03``", "Split label used in output paths"

      .. tab-item:: Data

         YAML: ``data/mydata.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``data.name``", "Required", "Dataset label used in output paths and logs"
            "``data.path``", "Required", "Directory containing the training, validation, and test files"
            "``data.input_dim``", "Required", "Number of expression columns (genes)"
            "``data.model_specific.<name>.minibatch_size``", "Optional; default: ``256``", "Cells per batch for AE and VAE variants; replace ``<name>`` with the value of ``model.meta.name`` (see the model-specific tabs)"
            "``data.model_specific.<name>.num_workers``", "Optional; default: ``0``", "Data-loading workers for AE and VAE variants; replace ``<name>`` with the value of ``model.meta.name`` (see the model-specific tabs)"

      .. tab-item:: AE variants

         YAML: ``model/train/AE.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``model.meta.name``", "Required for olAE & mlAE; default: ``AE``", "``AE``, ``olAE``, or ``mlAE``; selects the dataloader settings and labels model outputs"
            "``model.model_args.library_size_mode``", "Required for olAE & mlAE; default: ``none``", "``none`` for AE (no library-size scaling); ``observed`` for olAE (observed library size); ``modeled`` for mlAE (learned library size)"
            "``model.model_args.n_hidden``", "Optional; default: ``[1024]``", "Hidden-layer widths; list length determines depth"
            "``model.model_args.n_latent``", "Optional; default: ``100``", "Latent dimension"

      .. tab-item:: VAE variants

         YAML: ``model/train/<model>.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``model.model_args.n_hidden``", "Optional; default: ``1024``", "Hidden-layer width"
            "``model.model_args.n_latent``", "Optional; default: ``300``", "Latent dimension"
            "``model.model_args.n_layers``", "Optional; default: ``3``", "Number of hidden layers"
            "``model.model_args.use_observed_lib_size``", "Optional; scVI & nlscVI default: ``true``; mlscVI default: ``false``", "``true`` uses observed totals; ``false`` infers library size"

      .. tab-item:: PCA

         YAML: ``model/train/PCA.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``model.model_args.n_components``", "Optional; default: ``300``", "Number of principal components"

      .. tab-item:: Trainer

         YAML: ``trainer/AE.yaml`` or ``trainer/scVI.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``trainer.max_epochs``", "Optional; default: ``100``", "Maximum training epochs for AE and VAE variants"
            "``trainer.min_epochs``", "Optional; default: AE ``10``; VAE ``30``", "Minimum training epochs"

   Defaults refer to the provided data template and training configurations.

.. _custom-data-e2e-pca-setup:

.. dropdown:: Note: hardcoded temporary directory
   :icon: info
   :color: info

   Before running PCA, replace the default ``temp_dir`` in
   ``ReconPCA._setup_cluster``
   (``src/sc_reconstruction/models/reconpca.py``) with a writable
   directory for temporary files on your machine.

.. _custom-data-e2e-cli:

Run
^^^

Activate ``reconeval`` using ``cstm_scvi_env.yaml`` from the
:ref:`installation step <custom-data-installation>` and run from the
repository root. For cluster submission, follow
:ref:`Run through SLURM <slurm-parameters>`.

``data=mydata`` selects ``configs/data/mydata.yaml`` as the dataset configuration.

**Run with a YAML configuration**

For example, train a <model> with your ``mydata.yaml`` configuration:

.. code-block:: bash

   python experiments/01_end_to_end/codes/train.py \
     model="train/<model>" \ #e.g. for AE: train/AE
     trainer="<trainer>" \ #e.g. for AE: AE
     data=mydata

**Alternatively, you can use command-line overrides**

Use the same copied ``mydata.yaml`` and supply or override its settings
for an individual run:

.. code-block:: bash

   python experiments/01_end_to_end/codes/train.py \
     model="train/<model>" \ #e.g. for AE: train/AE
     trainer="<trainer>" \ #e.g. for AE: AE
     data=mydata \
     data.name=mydata_new \
     data.path=/path/to/mydata_new

.. _custom-data-e2e-train-outputs:

Outputs
^^^^^^^

**Model files**

Training saves outputs to:

.. code-block:: text

   <output_root>/weights/<dataset>/split0X/<model>/<note>/

``<output_root>`` is ``$RECONEVAL_OUT`` if set, otherwise ``~/reconeval_outputs``.

.. dropdown:: Table: Output folders
   :icon: table
   :color: primary

   .. csv-table::
      :header: "Folder", "Configuration"
      :widths: 25, 75

      "``<dataset>``", "``data.name``, e.g. ``mydata``"
      "``split0X``", "``split``; default: ``split03``"
      "``<model>``", "``model.meta.name``, e.g. ``AE`` or ``scVI``"
      "``<note>``", "``model.meta.note``; default: ``Default``"

**Logs and configuration**

Under the same ``<output_root>``:

- ``logs/``: W&B logs
- ``outputs/<dataset>/<model>/<YYYY-MM-DD_HH-MM>/``: Hydra run files,
  with configuration and overrides in ``.hydra/``
