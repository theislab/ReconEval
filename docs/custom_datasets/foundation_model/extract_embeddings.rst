Extract embeddings
~~~~~~~~~~~~~~~~~~

:doc:`Back to Foundation model reconstruction <../foundation_model>`

Generate embeddings with a frozen foundation model for decoder training
and evaluation.

For a demo using the LuCA dataset, see the
:doc:`Foundation-model tutorial <../../tutorials/fm>`.

Prepare checkpoints
^^^^^^^^^^^^^^^^^^^

From the repository root, download the pretrained checkpoints:

.. code-block:: bash

   conda activate reconeval
   python experiments/02_foundation_model/codes/download_checkpoints.py \
       --model all \
       --output-dir checkpoints/pretrained

Use ``--model <model>`` to download one model. The script prints the
``model_args.checkpoint_path`` to use in the extraction configuration or CLI,
plus ``model_args.protein_embeds_path`` for **SE**.

For **SE** extraction, switch to ``reconeval-state`` after downloading the
checkpoints; see :ref:`STATE environment setup <state-environment>`.

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
- **Geneformer** :cite:p:`theodoris:23`
- **UCE** :cite:p:`rosen:23`
- **scFoundation** :cite:p:`hao:24`

All models are used frozen for embedding extraction. Replace ``<model>``
in paths and commands with ``SE``, ``scGPT``, ``scConcept``, lowercase
``scimilarity``, ``Geneformer``, ``UCE``, or ``scFoundation``.

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
            "``data_args.comb_meta_root``", "Required for custom data", "Log1p-normalized expression store containing ``<group>/X``"
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
            "``data_args.comb_meta_root``", "Required for custom data", "Log1p-normalized expression store containing ``<group>/X``"
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
            "``data_args.comb_meta_root``", "Required for custom data", "Log1p-normalized expression store containing ``<group>/X``"
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
            "``model_args.gene_overlap_threshold``", "Optional; default: SCimilarity's (``5000``)", "Minimum number of input genes shared with the model; lower values trigger a warning"
            "``data_args.comb_meta_root``", "Required for custom data", "Raw-count or log1p-normalized expression store containing ``<group>/X``; normalized internally"
            "``data_args.split_meta_root``", "Required for custom data", "Store whose root attributes contain the group-name lists"
            "``data_args.output_dir``", "Required for custom output", "Output store receiving embeddings under ``<group>/X``"
            "``data_args.target_key``", "Required for split selection", "``null`` combines ``train_combinations``, ``val_combinations``, and ``test_combinations``; use one of these names to select a single split"
            "``data_args.var_names_path``", "Required for custom data", "Store containing gene identifiers in its root attributes; use ``/path/to/mydata/expression_for_fm.zarr``"
            "``data_args.var_names_key``", "Optional; keep if unchanged", "Gene attribute to read; supplied value: ``var_names``"
            "``parts``", "Optional; default: ``1``", "Part to process, numbered from ``1``"
            "``total_parts``", "Optional; default: ``15``", "Number of parts to divide the selected group list into"

      .. tab-item:: Geneformer

         YAML: ``experiments/02_foundation_model/configs/pretrained/Geneformer.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 35, 20, 45

            "``model_args.checkpoint_path``", "Required", "Pretrained model directory: ``/path/to/pretrained/Geneformer/Geneformer-V2-316M``"
            "``data_args.comb_meta_root``", "Required for custom data", "Raw-count store containing ``<group>/X``"
            "``data_args.split_meta_root``", "Required for custom data", "Store whose root attributes contain the group-name lists"
            "``data_args.output_dir``", "Required for custom output", "Output store receiving embeddings under ``<group>/X``"
            "``data_args.target_key``", "Required for split selection", "``null`` combines ``train_combinations``, ``val_combinations``, and ``test_combinations``; use one of these names to select a single split"
            "``data_args.var_names_path``", "Required for custom data", "Store containing gene identifiers in its root attributes"
            "``data_args.var_names_key``", "Optional; keep if unchanged", "Gene attribute to read; supplied value: ``var_ensembl_ids_38``"
            "``parts``", "Optional; default: ``1``", "Part to process, numbered from ``1``"
            "``total_parts``", "Optional; default: ``15``", "Number of parts to divide the selected group list into"

      .. tab-item:: UCE

         YAML: ``experiments/02_foundation_model/configs/pretrained/UCE.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 35, 20, 45

            "``model_args.checkpoint_path``", "Required", "Pretrained model directory: ``/path/to/pretrained/UCE``"
            "``data_args.comb_meta_root``", "Required for custom data", "Raw-count store containing ``<group>/X``"
            "``data_args.split_meta_root``", "Required for custom data", "Store whose root attributes contain the group-name lists"
            "``data_args.output_dir``", "Required for custom output", "Output store receiving embeddings under ``<group>/X``"
            "``data_args.target_key``", "Required for split selection", "``null`` combines ``train_combinations``, ``val_combinations``, and ``test_combinations``; use one of these names to select a single split"
            "``data_args.var_names_path``", "Required for custom data", "Store containing gene identifiers in its root attributes"
            "``data_args.var_names_key``", "Optional; keep if unchanged", "Gene attribute to read; supplied value: ``var_names``"
            "``parts``", "Optional; default: ``1``", "Part to process, numbered from ``1``"
            "``total_parts``", "Optional; default: ``15``", "Number of parts to divide the selected group list into"

      .. tab-item:: scFoundation

         YAML: ``experiments/02_foundation_model/configs/pretrained/scFoundation.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 35, 20, 45

            "``model_args.checkpoint_path``", "Required", "Pretrained model directory: ``/path/to/pretrained/scFoundation``"
            "``data_args.comb_meta_root``", "Required for custom data", "Log1p-normalized expression store containing ``<group>/X``"
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

The selected script loads ``configs/pretrained/<model>.yaml``.
Set ``target_key: null`` under ``data_args`` to extract embeddings for training,
validation, and test groups, covering decoder training and evaluation. Then run:

.. code-block:: bash

   python "experiments/02_foundation_model/codes/<model>_emb.py"

**Alternatively, you can override YAML values on the command line**

.. code-block:: bash

   python "experiments/02_foundation_model/codes/<model>_emb.py" \
     data_args.target_key=null \
     parts=1 \
     total_parts=1

For **scGPT**, append ``+model_args.gene_col=gene_name``. The ``+`` adds
the key, which is absent from the supplied YAML.

Outputs
^^^^^^^

Embeddings are saved as arrays (cells × embedding dimensions) under ``<group>/X`` in the Zarr store specified by ``data_args.output_dir``.
