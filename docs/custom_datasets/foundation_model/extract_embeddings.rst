Extract embeddings
~~~~~~~~~~~~~~~~~~

:doc:`Back to Foundation model <../foundation_model>`

Generate embeddings with a frozen foundation model for decoder training
and evaluation.

For a demo using the LuCA dataset, see the
:doc:`Foundation-model tutorial <../../tutorials/fm>`.

Configure
^^^^^^^^^

**Data**

For data-related parameters, see
:ref:`Data configuration <custom-data-fm-extraction-config>`.

**Model**

Choose a model:

- **SE** :cite:p:`adduri:25`
- **scGPT** :cite:p:`cui:24scgpt`
- **scConcept** :cite:p:`bahrami:25`
- **SCimilarity** :cite:p:`heimberg:25`

All models are used frozen for embedding extraction. Replace ``<model>``
in paths and commands with ``SE``, ``scGPT``, ``scConcept``, or lowercase
``scimilarity``.

**Parameters**

Set parameters in YAML or pass ``key=value`` overrides on the CLI.

The table below extends the
:ref:`embedding extraction data parameters <custom-data-fm-extraction-config>`
with model and execution parameters.

.. dropdown:: Table: Embedding extraction parameters
   :icon: table
   :color: primary

   .. tab-set::

      .. tab-item:: SE

         YAML: ``experiments/02_foundation_model/configs/pretrained/SE.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 35, 20, 45

            "``model_args.checkpoint_path``", "Required", "SE checkpoint file: ``/path/to/pretrained/SE/model.ckpt``"
            "``model_args.protein_embeds_path``", "Required", "Protein embeddings: ``/path/to/pretrained/SE/protein_embeddings.pt``"
            "``data_args.comb_meta_root``", "Required for custom data", "Expression store containing ``<group>/X``"
            "``data_args.split_meta_root``", "Required for custom data", "Store whose root attributes contain the group-name lists"
            "``data_args.output_dir``", "Required for custom output", "Output store receiving embeddings under ``<group>/X``"
            "``data_args.target_key``", "Required for split selection", "``null`` combines ``train_combinations``, ``val_combinations``, and ``test_combinations``; use one of these names to select a single split"
            "``parts``", "Optional; default: ``1``", "Part to process, numbered from ``1``"
            "``total_parts``", "Optional; default: ``15``", "Number of parts to divide the selected group list into"

      .. tab-item:: scGPT

         YAML: ``experiments/02_foundation_model/configs/pretrained/scGPT.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 35, 20, 45

            "``model_args.checkpoint_path``", "Required", "Pretrained model directory: ``/path/to/pretrained/scGPT``"
            "``model_args.gene_col``", "Required for array inputs", "Gene-name column; set to ``gene_name``"
            "``data_args.comb_meta_root``", "Required for custom data", "Expression store containing ``<group>/X``"
            "``data_args.split_meta_root``", "Required for custom data", "Store whose root attributes contain the group-name lists"
            "``data_args.output_dir``", "Required for custom output", "Output store receiving embeddings under ``<group>/X``"
            "``data_args.target_key``", "Required for split selection", "``null`` combines ``train_combinations``, ``val_combinations``, and ``test_combinations``; use one of these names to select a single split"
            "``data_args.var_names_path``", "Required for custom data", "Store containing gene identifiers in its root attributes; use ``/path/to/mydata/expression_for_fm.zarr``"
            "``data_args.var_names_key``", "Optional; keep if unchanged", "Gene attribute to read; supplied value: ``var_names``"
            "``parts``", "Optional; default: ``1``", "Part to process, numbered from ``1``"
            "``total_parts``", "Optional; default: ``15``", "Number of parts to divide the selected group list into"


      .. tab-item:: scConcept

         YAML: ``experiments/02_foundation_model/configs/pretrained/scConcept.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 35, 20, 45

            "``model_args.checkpoint_path``", "Required", "Pretrained model directory: ``/path/to/pretrained/scConcept``"
            "``data_args.comb_meta_root``", "Required for custom data", "Expression store containing ``<group>/X``"
            "``data_args.split_meta_root``", "Required for custom data", "Store whose root attributes contain the group-name lists"
            "``data_args.output_dir``", "Required for custom output", "Output store receiving embeddings under ``<group>/X``"
            "``data_args.target_key``", "Required for split selection", "``null`` combines ``train_combinations``, ``val_combinations``, and ``test_combinations``; use one of these names to select a single split"
            "``data_args.var_names_path``", "Required for custom data", "Store containing gene identifiers in its root attributes; use ``/path/to/mydata/expression_for_fm.zarr``"
            "``data_args.var_names_key``", "Optional; keep if unchanged", "Gene attribute to read; supplied value: ``var_ensembl_ids_38``"
            "``parts``", "Optional; default: ``1``", "Part to process, numbered from ``1``"
            "``total_parts``", "Optional; default: ``15``", "Number of parts to divide the selected group list into"

      .. tab-item:: SCimilarity

         YAML: ``experiments/02_foundation_model/configs/pretrained/scimilarity.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 35, 20, 45

            "``model_args.checkpoint_path``", "Required", "Pretrained model directory: ``/path/to/pretrained/scimilarity``"
            "``data_args.comb_meta_root``", "Required for custom data", "Expression store containing ``<group>/X``"
            "``data_args.split_meta_root``", "Required for custom data", "Store whose root attributes contain the group-name lists"
            "``data_args.output_dir``", "Required for custom output", "Output store receiving embeddings under ``<group>/X``"
            "``data_args.target_key``", "Required for split selection", "``null`` combines ``train_combinations``, ``val_combinations``, and ``test_combinations``; use one of these names to select a single split"
            "``data_args.var_names_path``", "Required for custom data", "Store containing gene identifiers in its root attributes; use ``/path/to/mydata/expression_for_fm.zarr``"
            "``data_args.var_names_key``", "Optional; keep if unchanged", "Gene attribute to read; supplied value: ``var_names``"
            "``parts``", "Optional; default: ``1``", "Part to process, numbered from ``1``"
            "``total_parts``", "Optional; default: ``15``", "Number of parts to divide the selected group list into"

.. dropdown:: Note: Parallel extraction
   :icon: info
   :color: info

   ``parts`` and ``total_parts`` support parallel extraction.
   With the supplied defaults, ``parts: 1`` selects the first of ``15`` parts.
   Run each part (``parts=1`` through ``parts=15``) to process all selected groups.

   For Slurm job arrays, pass ``parts=${SLURM_ARRAY_TASK_ID}``
   and use array indices from ``1`` to ``total_parts``.

Run
^^^

Activate the model's environment using the
:doc:`environment instructions <../prerequisites>`, then run from the
repository root, or follow :ref:`Run through Slurm <slurm-parameters>`.

**Run with a YAML configuration**

The selected script loads ``configs/pretrained/<model>.yaml``:

.. code-block:: bash

   python "experiments/02_foundation_model/codes/<model>_emb.py"

**Alternatively, you can override YAML values on the command line**

.. code-block:: bash

   python "experiments/02_foundation_model/codes/<model>_emb.py" \
     data_args.target_key=test_combinations \
     parts=1 \
     total_parts=1

Outputs
^^^^^^^

Embeddings are saved as arrays (cells × embedding dimensions) under ``<group>/X`` in the Zarr store specified by ``data_args.output_dir``.
