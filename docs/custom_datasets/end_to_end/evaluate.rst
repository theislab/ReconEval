Evaluate
~~~~~~~~

:doc:`Back to End-to-end reconstruction <../end_to_end>`

The evaluation consists of two steps:

- Reconstruct the held-out data
- Score the measured and reconstructed expression

To explore a demo using the LuCA dataset, see the :doc:`End-to-end tutorial <../../tutorials/end_to_end>`.
This section explains how to configure and run the evaluation scripts via the Python CLI, using outputs from the previous sections.

For end-to-end evaluation, the framework supports:

- Distributional (Statistical) metrics
- Biological metrics

For details, see `Metric families <../../overview.html#metric-families>`_ and the
:doc:`Metrics tutorial <../../tutorials/metrics>`.

.. _custom-data-e2e-eval-config:

Configure
^^^^^^^^^

The evaluation scripts use three main YAML configurations (data, metric, model), and a reference PCA YAML for distributional evaluation:

- Reuse your :ref:`data YAML <custom-data-e2e-data-config>`
- Choose a metric and use its prepared YAML from
  ``experiments/01_end_to_end/configs/metric/``
- Create a YAML for your trained model under
  ``experiments/01_end_to_end/configs/model/eval/``
- Create a reference PCA YAML under
  ``experiments/01_end_to_end/configs/metric/projector/``

**Model evaluation YAML details**

.. tab-set::

   .. tab-item:: AE/VAE

      Example for an AE or VAE variant (``model/eval/<model>.yaml``):

      .. code-block:: yaml

         meta:
           name: <model>

         load:
           path: "/path/to/checkpoint"
           model_name: "<training_run_name>"
           additional_params:
             <parameter>: <value>

      Replace the placeholders using the model-specific parameters below.
      Use the exact checkpoint path and the matching run-directory name;
      see :ref:`Outputs <custom-data-e2e-train-outputs>`.

   .. tab-item:: PCA

      Example for PCA (``model/eval/PCA.yaml``):

      .. code-block:: yaml

         meta:
           name: PCA

         model_args:
           _target_: sc_reconstruction.models.reconpca.ReconPCA

         load:
           path:
             - /path/to/weights/mydata/split0X/PCA/Default/mean.zarr
             - /path/to/weights/mydata/split0X/PCA/Default/pc_<n_components>.zarr
           model_name: "pc_<n_components>"

**Reference PCA YAML details**

Create ``experiments/01_end_to_end/configs/metric/projector/PCA.yaml``:


.. code-block:: yaml

   projector_args:
     mydata:
       n_components: 50

   model_args:
     _target_: sc_reconstruction.models.reconpca.ReconPCA
     n_components: ${metric.projector.projector_args.${data.name}.n_components}

   load:
     path:
       - /path/to/weights/${model_data}/uni/PCA/uni/mean.zarr
       - /path/to/weights/${model_data}/uni/PCA/uni/pc_${metric.projector.model_args.n_components}.zarr

- Use the exact paths to the saved mean and components; see :ref:`reference-PCA outputs <custom-data-e2e-reference-pca>`.
- ``mydata`` must match ``data.name``
- ``n_components`` must match the saved PCA
- ``model_data`` defaults to ``data.name`` (``mydata`` in this example)

**Parameters**

Set the parameters in YAML or pass them as ``key=value`` on the CLI:

.. dropdown:: Table: Evaluation parameters
   :icon: table
   :color: primary

   .. tab-set::

      .. tab-item:: Run

         YAML: ``base_eval.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``data``", "Required", "Dataset configuration, e.g. ``mydata``"
            "``model``", "Required", "Evaluation configuration: ``eval/<model>``"
            "``metric``", "Required", "Selected metric configuration"
            "``dynamic_model_loading``", "Optional; default: ``true``", "``load.additional_params`` applies only when this is ``true`` and ``model_args`` is absent"
            "``train_fraction``", "Required for held-out-only evaluation", "Set to ``0`` to exclude training groups; current default: ``0.1``"
            "``test_fraction``", "Optional; default: ``1``", "Fraction of held-out groups to evaluate"
            "``seed``", "Optional; default: ``42``", "Group-sampling seed"
            "``split``", "Optional; default: ``split01``", "Match the trained split label; actual group assignments come from ``data.split_comb``"
            "``output.save_path``", "Required for custom output", "Output CSV path; use a separate path for each model and metric configuration"

      .. tab-item:: AE variants

         YAML: ``model/eval/<model>.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``model.load.path``", "Required", "Checkpoint path"
            "``model.load.model_name``", "Required", "Matching training-run identifier; used in the default output path"
            "``model.load.additional_params.input_dim``", "Required for dynamic AE construction", "``${data.input_dim}``; match the training gene count"
            "``model.load.additional_params.distribution``", "Optional; default: ``normal``", "Match the distribution used during training"
            "``model.load.additional_params.library_size_mode``", "Optional; default: ``none``", "Match the trained variant: AE ``none``, olAE ``observed``, mlAE ``modeled``"

      .. tab-item:: VAE variants

         YAML: ``model/eval/<model>.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``model.load.path``", "Required", "Checkpoint path"
            "``model.load.model_name``", "Required", "Matching training-run identifier; used in the default output path"
            "``model.load.additional_params.gene_likelihood``", "Optional; match training", "Likelihood used to train scVI, nlscVI, or mlscVI"
            "``model.load.additional_params.use_observed_lib_size``", "Optional; match training", "Current training defaults: scVI & nlscVI ``true``; mlscVI ``false``"

      .. tab-item:: PCA

         YAML: ``model/eval/PCA.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``model.load.path``", "Required", "Ordered list ``[mean_path, components_path]``"
            "``model.load.model_name``", "Required", "Label such as ``pc_128``; used in the default output path"
            "``model.model_args._target_``", "Required in the PCA YAML", "``sc_reconstruction.models.reconpca.ReconPCA``"

      .. tab-item:: Metrics

         YAML: ``metric/<metric>.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``metric.evaluator.mode``", "Required", "``reconstruction``"
            "``metric.evaluator.emb_zarr_path``", "Optional", "Omit or set to ``null`` for reconstruction"

      .. tab-item:: Reference PCA

         YAML: ``metric/projector/PCA.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``metric.projector.load.path``", "Required for distributional evaluation", "Ordered list ``[mean_path, components_path]`` for the saved reference PCA"


Run
^^^

Run from the repository root in the ``reconeval`` environment, or follow
:ref:`Run through SLURM <slurm-parameters>`.

**Distributional metrics**

Compute the following metrics:

- **On expression:** :func:`~sc_reconstruction.metrics.metric_r2`,
  :func:`~sc_reconstruction.metrics.metric_mse`
- **Using the reference PCA:** ``mmd_rbf()`` (Maximum Mean Discrepancy or MMD) and
  :func:`~sc_reconstruction.metrics.metric_energy_distance`

Example:

.. code-block:: bash

   python experiments/01_end_to_end/codes/eval_distributional.py \
     data=mydata \
     metric=_distributional \
     model="eval/<model>" \
     metric.evaluator.mode=reconstruction \
     metric.evaluator.emb_zarr_path=null \
     train_fraction=0 \
     test_fraction=1 \
     split="split0X" \
     output.save_path="/path/to/results/mydata/<model>_distributional.csv"

**Biological metrics**

Available metrics: :func:`~sc_reconstruction.metrics.metric_cellcycle`,
:func:`~sc_reconstruction.metrics.metric_pathway`,
:func:`~sc_reconstruction.metrics.metric_coexpression`,
:func:`~sc_reconstruction.metrics.metric_deg`, and
:func:`~sc_reconstruction.metrics.metric_cytokine`.

Coexpression uses MSigDB Hallmark gene sets from Omnipath.
The expression store’s root ``var_names`` attribute must contain matching gene symbols.

Example:

.. code-block:: bash

   python experiments/01_end_to_end/codes/eval_biological.py \
     data=mydata \
     metric=_coexpression \
     metric.evaluator.mode=reconstruction \
     metric.evaluator.emb_zarr_path=null \
     model="eval/<model>" \
     train_fraction=0 \
     test_fraction=1 \
     split="split0X" \
     output.save_path="/path/to/results/mydata/<model>_coexpression.csv"

- For another biological metric, select its configuration under ``experiments/01_end_to_end/configs/metric/`` and supply its required references/annotations 
- See the :doc:`Metrics tutorial <../../tutorials/metrics>` for examples

Outputs
^^^^^^^

Each command saves results to ``output.save_path``.
Rerunning a command replaces the existing output.
