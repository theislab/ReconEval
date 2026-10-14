.. _custom-data-state-cli:

Run STATE from CLI
~~~~~~~~~~~~~~~~~~

:doc:`Back to Latent shift <../latent_shift>`

For cluster submission, follow :ref:`Run through SLURM <slurm-parameters>`.

**Run STATE:**

1. Activate ``reconeval-pancellflow`` from the
   :ref:`installation step <custom-data-installation>`

2. Copy ``template_train.toml`` and ``template_val.toml`` from
   ``experiments/03_latent_shift/configs/st/`` to ``mydata_train.toml`` and
   ``mydata_val.toml`` in the same directory. Set the split directories in
   ``[datasets]`` and use matching dataset names in ``[training]``.
   Keep the ``"train"`` value in both files; the script uses a separate
   data module's training loader for validation

3. In ``experiments/03_latent_shift/codes/train_st.py``, point
   ``build_data_module`` and ``build_val_data_module`` to those TOML files.
   Update ``DATA_KWARGS_COMMON`` for your metadata keys and control label

4. Set the representation, decoder checkpoint, and output directory, then
   train STATE. The checkpoint must match the embedding width and output
   gene order. For ``AE_128`` embeddings:

   .. code-block:: bash

      python experiments/03_latent_shift/codes/train_st.py \
        --model AE_128 \
        --decoder_mode frozen \
        --decoder_ckpt /path/to/ae128.ckpt \
        --max_steps 40000 \
        --batch_size 16 \
        --no_wandb \
        --out_root /path/to/results/mydata/state

**Required inputs and common optional settings:**

.. dropdown:: Table: Training parameters
   :icon: table
   :color: primary

   .. csv-table::
      :header: "Flag", "Required / optional", "Meaning"
      :widths: 30, 30, 40

      "``--model``", "Required", "Representation listed in EMB_DIMS, e.g. AE_128"
      "``--decoder_mode``", "Optional; default: frozen", "Use a trained decoder; fresh initializes one"
      "``--decoder_ckpt``", "Optional; default: path in DECODER_CONFIGS", "Checkpoint for a frozen AE, VAE, or MLP decoder; ignored for PCA and fresh decoders"
      "``--decoder_weight``", "Optional; default: 0.0", "Gene-space loss weight; use a positive value to train a fresh decoder"
      "``--max_steps``", "Optional; default: 40000", "Maximum training steps"
      "``--batch_size``", "Optional; default: 16", "Cell sets per training batch"
      "``--lr``", "Optional; default: 0.0001", "Learning rate"
      "``--seed``", "Optional; default: 42", "Random seed"
      "``--arch_config``", "Optional; default: hf_se_parse", "Architecture YAML name under configs/arch, or a YAML file path"
      "``--cell_set_len``", "Optional; default: architecture setting (512 for hf_se_parse)", "Cells per set"
      "``--no_wandb``", "Optional; default: false", "Pass this flag to disable W&B logging"
      "``--out_root``", "Optional; default: script's OUT_ROOT", "Output root; a run subdirectory is created. Set a writable path for your run"

For PCA, set the decoder's ``mean_path`` and ``pc_path`` in
``DECODER_CONFIGS``.

