Extract embeddings (optional)
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

:doc:`Back to End-to-end reconstruction <../end_to_end>`

Extract embeddings from a trained model for downstream tasks:

- For inputs, see :ref:`Embedding extraction inputs <custom-data-e2e-embedding-inputs>`
- Train perturbation-response models, e.g. STATE :cite:p:`adduri:25` or CellFlow :cite:p:`klein:25`, see :ref:`Latent shift <custom-data-latent-shift>` for details

Configure
^^^^^^^^^

Pass these parameters as CLI flags; no YAML configuration is needed.

.. dropdown:: Table: Embedding extraction parameters
   :icon: table
   :color: primary

   .. tab-set::

      .. tab-item:: Run

         .. csv-table::
            :header: "Flag", "Required / optional", "Meaning"
            :widths: 30, 30, 40

            "``--model``", "Required", "``AE`` (including olAE and mlAE), ``nlscVI``, or ``PCA``"
            "``--hvg_zarr``", "Required for custom data", "Path to the grouped ``expression.zarr`` store"
            "``--out``", "Required", "Output Zarr path; use a separate path for each trained model and split"

      .. tab-item:: AE and nlscVI

         .. csv-table::
            :header: "Flag", "Required / optional", "Meaning"
            :widths: 30, 30, 40

            "``--ckpt``", "Required for AE/nlscVI", "Trained checkpoint: ``.ckpt`` for AE variants or ``.pt`` for nlscVI"
            "``--device``", "Optional; default: ``cuda``", "``cpu`` or ``cuda`` for AE/nlscVI"
            "``--batch_size``", "Optional; default: 4096", "Cells per encoding batch for AE/nlscVI"

      .. tab-item:: PCA

         .. csv-table::
            :header: "Flag", "Required / optional", "Meaning"
            :widths: 30, 30, 40

            "``--pca_mean``", "Required for PCA", "Path to the saved ``mean.zarr``"
            "``--pca_pc``", "Required for PCA", "Path to the saved components; retain the filename ``pc_<n_components>.zarr``"

Run
^^^

Run from the repository root in the ``reconeval`` environment, or follow
:ref:`Run through Slurm <slurm-parameters>`.

Example for AE variants or nlscVI:

.. code-block:: bash

   python experiments/01_end_to_end/codes/extract_e2e_embeddings.py \
     --model "<model>" \
     --ckpt /path/to/checkpoint \
     --hvg_zarr /path/to/mydata/expression.zarr \
     --out "/path/to/mydata/embeddings/<model>_emb.zarr" \
     --device cpu

Outputs
^^^^^^^

Embeddings are saved as cells-by-latent-dimensions arrays under
``<group>/X`` in the Zarr store specified by ``--out``.

For preparation of latent-shift inputs, follow
:ref:`Latent-shift inputs <custom-data-latent-inputs>`.
