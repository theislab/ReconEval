Evaluate
~~~~~~~~

:doc:`Back to Foundation model <../foundation_model>`

**Overview**

The evaluation consists of two steps:

- Reconstruct held-out expression
- Score the measured and reconstructed expression

This section explains how to configure and run the evaluation scripts via
the Python CLI, using outputs from the previous sections.

**Metrics**

For foundation model evaluation, the framework supports:

- Distributional (Statistical) metrics
- Biological metrics

For details, see `Metric families <../../overview.html#metric-families>`_ and the
:doc:`Metrics tutorial <../../tutorials/metrics>`.

Configure
^^^^^^^^^

The evaluation scripts use three main YAML configurations (data, metric,
decoder), and a reference PCA YAML for distributional evaluation:

- Reuse your :ref:`data YAML <custom-data-fm-evaluation-config>`
- Choose a metric and update its YAML under
  ``experiments/02_foundation_model/configs/metric/`` using the settings below
- Update ``experiments/02_foundation_model/configs/decoder/MLP.yaml``
  to match your trained decoder
- Create a reference PCA YAML under
  ``experiments/02_foundation_model/configs/metric/projector/``

**Metric evaluation YAML details**

Update the selected metric YAML with the fields below, keeping its other
settings.

.. tab-set::

   .. tab-item:: Distributional metrics

      Update ``metric/decode_statistical.yaml``:

      .. code-block:: yaml

         defaults:
           - projector: PCA
           - _self_

         evaluator:
           _target_: sc_reconstruction.metrics.distributional.ProjectionMetricsBatchEvaluator
           mode: decode
           emb_zarr_path: ${emb_zarr_path}
           reference_batch: null
           input_key: X
           split_key: ${data.split_key}
           max_workers: 1

   .. tab-item:: Biological metrics

      For coexpression, update ``metric/decode_coexpression.yaml``:

      .. code-block:: yaml

         evaluator:
           _target_: sc_reconstruction.metrics._coexpression.CoexpressionBatchEvaluator
           mode: decode
           emb_zarr_path: ${emb_zarr_path}
           reference_batch: null
           input_key: X
           split_key: ${data.split_key}
           max_workers: 1

**Model evaluation YAML details**

Update ``decoder/MLP.yaml``:

.. code-block:: yaml

   model_args:
     n_input: ???  # latent_dim from training config.yaml
     n_output: ???  # gene_dim from training config.yaml

   load:
     path: /path/to/results/mydata/<model>/MLP/<checkpoint>.ckpt
     model_name: <training_run_name>

Match the architecture and other model settings to the training
``config.yaml``; see the
:ref:`decoder training outputs <custom-data-fm-decoder-training-outputs>`.

**Reference PCA YAML details**

Create ``experiments/02_foundation_model/configs/metric/projector/PCA.yaml``:


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

Set parameters in YAML or pass ``key=value`` overrides on the CLI.

.. dropdown:: Table: Evaluation parameters
   :icon: table
   :color: primary

   .. tab-set::

      .. tab-item:: Run

         YAML: ``base_eval_decode.yaml``

         Keep this base YAML unchanged and pass the parameters below as
         ``key=value`` CLI overrides.

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``data``", "Required", "Dataset configuration, e.g. ``mydata``"
            "``pretrained``", "Required", "Foundation model used for the embeddings: ``SE``, ``scGPT``, ``scConcept``, or ``scimilarity``"
            "``decoder``", "Optional; default: ``MLP``", "Decoder configuration matching the trained checkpoint"
            "``metric``", "Required", "Selected metric configuration, e.g. ``decode_statistical`` or ``decode_coexpression``"
            "``emb_zarr_path``", "Required", "Grouped embedding store containing ``<group>/X``"
            "``train_fraction``", "Required for held-out-only evaluation", "Set to ``0`` to exclude training groups; current default: ``0.1``"
            "``test_fraction``", "Optional; default: ``1``", "Fraction of held-out groups to evaluate"
            "``seed``", "Optional; default: ``42``", "Group-sampling seed"
            "``split``", "Optional; default: ``split01``", "Label used in the default output path; group assignments come from ``data.split_comb``"
            "``output.save_path``", "Required for custom output", "Output CSV path; use a separate path for each model and metric configuration"

      .. tab-item:: Decoder

         YAML: ``decoder/MLP.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``decoder.load.path``", "Required", "Path to the trained decoder checkpoint"
            "``decoder.load.model_name``", "Required for the default output path", "Training-run label; unused when output.save_path is supplied explicitly"
            "``decoder.model_args.n_input``", "Required", "Embedding dimension; use latent_dim from training config.yaml"
            "``decoder.model_args.n_output``", "Required", "Output gene count; use gene_dim from training config.yaml"
            "``decoder.model_args.n_layers``", "Optional; default: ``1``", "Hidden-layer count; match training n_layers"
            "``decoder.model_args.n_hidden``", "Optional; default: ``4096``", "Hidden-layer width; match training hidden"
            "``decoder.model_args.distribution``", "Optional; default: ``normal``", "Loss family used during training"
            "``decoder.model_args.library_size_mode``", "Optional; default: ``none``", "Library-size setting; decoder-only training uses none"

         Defaults refer to the supplied ``decoder/MLP.yaml``.

      .. tab-item:: Metrics

         YAML: ``metric/<metric>.yaml``; examples above use
         ``decode_statistical`` and ``decode_coexpression``.

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``metric.evaluator._target_``", "Required", "Evaluator class for the selected metric"
            "``metric.evaluator.mode``", "Required", "``decode``"
            "``metric.evaluator.zarr_path``", "Required", "``${eval_path}``; measured expression from ``data.eval_path``"
            "``metric.evaluator.emb_zarr_path``", "Required", "``${emb_zarr_path}``; grouped embeddings"
            "``metric.evaluator.input_key``", "Required", "``X`` in each embedding group"
            "``metric.evaluator.output_key``", "Required", "``X`` in each expression group"
            "``metric.evaluator.split_key``", "Required", "``${data.split_key}``; fields in group-name order"
            "``metric.evaluator.reference_batch``", "Required", "``null`` for decoder evaluation"
            "``metric.evaluator.max_workers``", "Optional; examples: ``1``", "Use ``1`` for one worker; values above 1 use all detected CPUs"

      .. tab-item:: Reference PCA

         YAML: ``metric/projector/PCA.yaml``

         .. csv-table::
            :header: "Parameter", "Required / optional", "Value / meaning"
            :widths: 40, 25, 35

            "``metric.projector.load.path``", "Required for distributional evaluation", "Ordered list ``[mean_path, components_path]`` for the saved reference PCA"
            "``metric.projector.model_args.n_components``", "Required; example: ``50``", "Number of components in the saved reference PCA"

Run
^^^

Run from the repository root in ``reconeval``, or use
:ref:`Slurm <slurm-parameters>`.

Replace ``<model>`` with ``SE``, ``scGPT``, ``scConcept``, or ``scimilarity``.
Set ``train_fraction=0`` and ``test_fraction=1`` to evaluate all held-out groups.

**Distributional metrics**

Compute the following metrics:

- **On expression:** :func:`~sc_reconstruction.metrics.metric_r2`,
  :func:`~sc_reconstruction.metrics.metric_mse`
- **Using the reference PCA:** ``mmd_rbf()`` (Maximum Mean Discrepancy or MMD) and
  :func:`~sc_reconstruction.metrics.metric_energy_distance`

Example:

.. code-block:: bash

   python experiments/02_foundation_model/codes/eval_decoder_statistical.py \
     data=mydata \
     pretrained="<model>" \
     decoder=MLP \
     metric=decode_statistical \
     emb_zarr_path="/path/to/mydata/embeddings/<model>/grouped.zarr" \
     train_fraction=0 \
     test_fraction=1 \
     output.save_path="/path/to/results/mydata/<model>/distributional.csv"

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

   python experiments/02_foundation_model/codes/eval_decoder_biological.py \
     data=mydata \
     pretrained="<model>" \
     decoder=MLP \
     metric=decode_coexpression \
     emb_zarr_path="/path/to/mydata/embeddings/<model>/grouped.zarr" \
     train_fraction=0 \
     test_fraction=1 \
     output.save_path="/path/to/results/mydata/<model>/coexpression.csv"

- For another biological metric:

  - Copy its configuration from
    ``experiments/01_end_to_end/configs/metric/`` to
    ``experiments/02_foundation_model/configs/metric/``
  - Update its ``evaluator`` section using the settings above,
    keeping its own ``_target_`` and metric-specific parameters
  - Provide the additional inputs required by the metric, e.g.
    control groups for DEG evaluation or a signature CSV for
    cytokine evaluation
  - Select it with ``metric=<metric>``, where ``<metric>`` is the
    configuration filename without ``.yaml``

- See the :doc:`Metrics tutorial <../../tutorials/metrics>` for examples.

Outputs
^^^^^^^

Each command saves results to ``output.save_path``.
Rerunning a command replaces the existing output.
