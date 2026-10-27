Custom data
===========

Before you start
----------------

:doc:`Set up the environment <custom_datasets/prerequisites>` before running workflows.

Data preparation
----------------

For lightweight datasets, follow :doc:`Data preparation
<custom_datasets/dataset_preparation>` to prepare the input files.

Hands-on examples
-----------------

Start with hands-on examples:

.. grid:: 1 1 3 3
   :gutter: 2

   .. grid-item-card:: End-to-end reconstruction
      :link: custom_datasets/examples/end_to_end
      :link-type: doc
      :text-align: center
      :class-body: sd-d-flex-column sd-align-major-center
      :class-title: sd-mb-0

   .. grid-item-card:: Foundation model
      :link: custom_datasets/examples/foundation_model
      :link-type: doc
      :text-align: center
      :class-body: sd-d-flex-column sd-align-major-center
      :class-title: sd-mb-0

   .. grid-item-card:: Latent shift
      :link: custom_datasets/examples/latent_shift
      :link-type: doc
      :text-align: center
      :class-body: sd-d-flex-column sd-align-major-center
      :class-title: sd-mb-0

Advanced usage
--------------

Or follow the advanced instructions for your own data:

- :doc:`End-to-end reconstruction <custom_datasets/end_to_end>`
- :doc:`Foundation model <custom_datasets/foundation_model>`
- :doc:`Latent shift <custom_datasets/latent_shift>`

The instructions use ``mydata`` as the dataset name and ``/path/to/...`` for
paths; replace these placeholders with your own values.

Running on a cluster (optional)
-------------------------------
To run on a cluster with Slurm support, follow :doc:`the Slurm guide <custom_datasets/slurm>`.

.. toctree::
   :maxdepth: 1
   :hidden:

   Environment setup <custom_datasets/prerequisites>
   Data preparation <custom_datasets/dataset_preparation>
   custom_datasets/examples
   custom_datasets/advanced_usage
   custom_datasets/slurm
