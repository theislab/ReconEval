.. _custom-data-fm-configuration:

Data configuration
~~~~~~~~~~~~~~~~~~

:doc:`Back to Foundation model <../foundation_model>`

Each stage requires different configurations for data:

- **Embedding extraction**:
  
  - Edit ``pretrained/<model>.yaml``
  - or pass parameters with CLI

- **Decoder training**:
  
  - Pass parameters with CLI

- **Evaluation**:
  
  - Edit ``data/<dataset>.yaml``
  - and pass additional parameters with CLI

.. _custom-data-fm-extraction-config:

Embedding extraction
^^^^^^^^^^^^^^^^^^^^

Update the data fields in your model's YAML file, keeping its other
settings, or pass them as ``key=value`` CLI overrides.

General data configuration:

.. code-block:: yaml

   data_args:
     comb_meta_root: /path/to/mydata/expression_for_fm.zarr
     split_meta_root: /path/to/mydata/split_metadata.zarr
     output_dir: /path/to/mydata/embeddings/<model>/grouped.zarr
     target_key: null


.. dropdown:: Table: Embedding extraction data parameters
   :icon: table
   :color: primary

   .. tab-set::

      .. tab-item:: SE

         YAML: ``experiments/02_foundation_model/configs/pretrained/SE.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 35, 20, 45

            "``data_args.comb_meta_root``", "Required for custom data", "Expression store containing ``<group>/X``"
            "``data_args.split_meta_root``", "Required for custom data", "Store whose root attributes contain the group-name lists"
            "``data_args.output_dir``", "Required for custom output", "Output store receiving embeddings under ``<group>/X``"
            "``data_args.target_key``", "Required for split selection", "``null`` combines ``train_combinations``, ``val_combinations``, and ``test_combinations``; use one of these names to select a single split"

      .. tab-item:: scGPT

         YAML: ``experiments/02_foundation_model/configs/pretrained/scGPT.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 35, 20, 45

            "``data_args.comb_meta_root``", "Required for custom data", "Expression store containing ``<group>/X``"
            "``data_args.split_meta_root``", "Required for custom data", "Store whose root attributes contain the group-name lists"
            "``data_args.output_dir``", "Required for custom output", "Output store receiving embeddings under ``<group>/X``"
            "``data_args.target_key``", "Required for split selection", "``null`` combines ``train_combinations``, ``val_combinations``, and ``test_combinations``; use one of these names to select a single split"
            "``data_args.var_names_path``", "Required for custom data", "Store containing gene identifiers in its root attributes; use ``/path/to/mydata/expression_for_fm.zarr``"
            "``data_args.var_names_key``", "Optional; keep if unchanged", "Gene attribute to read; supplied value: ``var_names``"

      .. tab-item:: scConcept

         YAML: ``experiments/02_foundation_model/configs/pretrained/scConcept.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 35, 20, 45

            "``data_args.comb_meta_root``", "Required for custom data", "Expression store containing ``<group>/X``"
            "``data_args.split_meta_root``", "Required for custom data", "Store whose root attributes contain the group-name lists"
            "``data_args.output_dir``", "Required for custom output", "Output store receiving embeddings under ``<group>/X``"
            "``data_args.target_key``", "Required for split selection", "``null`` combines ``train_combinations``, ``val_combinations``, and ``test_combinations``; use one of these names to select a single split"
            "``data_args.var_names_path``", "Required for custom data", "Store containing gene identifiers in its root attributes; use ``/path/to/mydata/expression_for_fm.zarr``"
            "``data_args.var_names_key``", "Optional; keep if unchanged", "Gene attribute to read; supplied value: ``var_ensembl_ids_38``"

      .. tab-item:: SCimilarity

         YAML: ``experiments/02_foundation_model/configs/pretrained/scimilarity.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 35, 20, 45

            "``data_args.comb_meta_root``", "Required for custom data", "Expression store containing ``<group>/X``"
            "``data_args.split_meta_root``", "Required for custom data", "Store whose root attributes contain the group-name lists"
            "``data_args.output_dir``", "Required for custom output", "Output store receiving embeddings under ``<group>/X``"
            "``data_args.target_key``", "Required for split selection", "``null`` combines ``train_combinations``, ``val_combinations``, and ``test_combinations``; use one of these names to select a single split"
            "``data_args.var_names_path``", "Required for custom data", "Store containing gene identifiers in its root attributes; use ``/path/to/mydata/expression_for_fm.zarr``"
            "``data_args.var_names_key``", "Optional; keep if unchanged", "Gene attribute to read; supplied value: ``var_names``"

.. _custom-data-fm-training-config:

Decoder training
^^^^^^^^^^^^^^^^

Pass these data parameters to ``train_decoder_from_embedding.py`` as CLI flags. 
No YAML configuration is needed.

.. dropdown:: Table: Decoder training data parameters
   :icon: table
   :color: primary

   .. csv-table::
      :header: "Flag", "Required / optional", "Meaning"
      :widths: 30, 20, 50

      "``--emb-train-zarr``", "Required", "Training store containing ``X`` and embeddings: ``/path/to/mydata/embeddings/<model>/train.zarr``"
      "``--emb-val-zarr``", "Required", "Validation store containing ``X`` and embeddings: ``/path/to/mydata/embeddings/<model>/val.zarr``"
      "``--all-genes-zarr``", "Required", "Gene-list store whose root ``var_names`` attribute lists expression genes in column order: ``/path/to/mydata/all_genes.zarr``"
      "``--target-genes-zarr``", "Required", "Gene-list store whose root ``var_names`` attribute lists all or selected expression genes in decoder output order: ``/path/to/mydata/target_genes.zarr``"
      "``--embedding-key``", "Required", "Embedding array name in both stores: ``SE``, ``scGPT``, ``scConcept``, or ``scimilarity``"

.. _custom-data-fm-evaluation-config:

Evaluation
^^^^^^^^^^

**YAML**

Create ``experiments/02_foundation_model/configs/data/mydata.yaml`` with
the evaluation data fields below; see also the
:ref:`End-to-end data configuration <custom-data-e2e-data-config>`.

.. code-block:: yaml

   name: mydata
   eval_path: /path/to/mydata/expression.zarr
   split_comb: /path/to/mydata/split_metadata.zarr
   split_key:
     - ??? # cell_type
     - ??? # dataset
     - ??? # origin

The comments show LuCA example fields. Replace ``???`` with the fields
and order used to name your groups. Select this data configuration with
``data=mydata`` for evaluation.

**CLI parameters**

Pass additional settings as ``key=value`` CLI overrides:

.. dropdown:: Table: Evaluation data parameters
   :icon: table
   :color: primary

   .. csv-table::
      :header: "Parameter", "Required / optional", "Value / meaning"
      :widths: 35, 20, 45

      "``data``", "Required", "Dataset YAML name; use ``data=mydata`` to select ``data/mydata.yaml``"
      "``emb_zarr_path``", "Required", "Grouped embeddings: ``/path/to/mydata/embeddings/<model>/grouped.zarr``"
      "``data.eval_path``", "Optional; uses dataset YAML", "Measured expression store; its columns and root ``var_names`` must match the decoder's output genes in order"
      "``data.split_comb``", "Optional; uses dataset YAML", "Split metadata store containing the group-name lists"
      "``data.split_key``", "Optional; uses dataset YAML", "Grouping fields in group-name order"
      "``train_fraction``", "Required for held-out-only evaluation", "Set to ``0`` to exclude training groups; supplied default: ``0.1``"
      "``test_fraction``", "Optional; default: ``1``", "Fraction of groups from ``test_combinations`` to evaluate"
      "``seed``", "Optional; default: ``42``", "Seed for sampling groups"

.. dropdown:: Note: Held-out evaluation parameters
   :icon: info
   :color: info

   For held-out evaluation, pass ``train_fraction=0`` and ``test_fraction=1``
   as CLI overrides to evaluate only groups listed in ``test_combinations``.

For the full list of parameters, see :doc:`Evaluate <evaluate>`.
