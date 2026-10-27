.. _custom-data-e2e-reference-pca:

Prepare reference PCA
~~~~~~~~~~~~~~~~~~~~~

:doc:`Back to End-to-end reconstruction <../end_to_end>`

For distributional evaluation, reuse a matching reference PCA or fit one
using the :ref:`reference expression <custom-data-e2e-reference-pca-inputs>`
and :ref:`dataset configuration <custom-data-e2e-data-config>`.

After completing the :ref:`PCA setup <custom-data-e2e-pca-setup>`,
run from the repository root in GPU-enabled ``reconeval``, directly
or through :ref:`Slurm <slurm-parameters>`.

The example fits 50 components. Replace ``<output_root>`` with the absolute
path to your :ref:`output directory <custom-data-e2e-model-files>`:

.. code-block:: bash

   python experiments/01_end_to_end/codes/train.py \
     data=mydata \
     model=train/PCA \
     trainer=PCA \
     data.model_specific.PCA.train_path=/path/to/mydata/reference.h5ad \
     model.model_args.n_components=50 \
     'trainer.save_path=<output_root>/weights/mydata/uni/PCA/uni'

Outputs in ``<output_root>/weights/mydata/uni/PCA/uni/``:

- ``mean.zarr``: mean expression per gene
- ``pc_50.zarr``: the genes-by-50 component matrix

Reuse these files across models with matching preprocessing and gene
order; see :ref:`evaluation setup <custom-data-e2e-eval-config>`.
