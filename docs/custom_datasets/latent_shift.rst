.. _custom-data-latent-shift:

Latent shift
------------

:doc:`Back to introduction <../custom_datasets>`

For STATE and CellFlow :cite:p:`klein:25`, generate embeddings using a model trained in
:ref:`End-to-end <custom-data-end-to-end>` or a pretrained foundation model
(:ref:`embedding preparation <custom-data-mlp-data>`). Use the same encoder for all
splits and save embeddings in ``.obsm`` (e.g. ``.obsm["X_AE_128"]``).

For embeddings from the pretrained State Embedding (SE) foundation model
:cite:p:`adduri:25`, see the
`foundation-model tutorial <../tutorials/fm.html#embed-with-a-foundation-model>`_.

.. toctree::
   :maxdepth: 1

   latent_shift/prepare_inputs
   latent_shift/state
   latent_shift/cellflow
   latent_shift/outputs
