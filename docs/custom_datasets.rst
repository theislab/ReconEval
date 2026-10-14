Custom data
===========

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

Instructions
------------

Or follow the general instructions for your own data:

- :doc:`Set up environments <custom_datasets/prerequisites>`
- Choose a guide for your preprocessed data:

  - :doc:`End-to-end reconstruction <custom_datasets/end_to_end>`
  - :doc:`Foundation model <custom_datasets/foundation_model>`
  - :doc:`Latent shift <custom_datasets/latent_shift>`

- :doc:`Run through SLURM <custom_datasets/slurm>` (optional)

The instructions use ``mydata`` as the dataset name and ``/path/to/...`` for
paths; replace these placeholders with your own values.

.. toctree::
   :maxdepth: 1
   :hidden:

   custom_datasets/examples
   custom_datasets/prerequisites
   custom_datasets/end_to_end
   custom_datasets/foundation_model
   custom_datasets/latent_shift
   custom_datasets/slurm
