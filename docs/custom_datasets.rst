Use custom data
===============

- Start with a **preprocessed** dataset
- Choose the task below:
  
  - 01_end_to_end
  - 02_foundation_model
  - 03_latent_shift
  
- Run:
   
  - Python CLI directly
  - or submit it through SLURM
  
- The current documentation uses ``mydata`` and ``/path/to/...`` as the examples for dataset name 
  and path to it respectively; replace these placeholders.

.. _custom-data-installation:

1. Set up prerequisites
-----------------------

To create environment check the following instructions:

- Environments `README <https://github.com/theislab/ReconEval/blob/main/envs/README.md>`_ in the ReconEval repository
- :doc:`installation`

.. _slurm-parameters:

2. Set up SLURM parameters
--------------------------

Skip this section for direct Python runs.

Before submitting a job:

1. Use scripts located in ``experiments/*/submit/`` directory
   as the examples for your own SLURM submission scripts.

2. Edit ``#SBATCH`` settings in your ``.sbatch`` file for your cluster. Existing resource requests
   were used for the benchmark datasets, use them as a reference.

3. Update the Conda initialization and activation lines to use your local
   Conda setup and the environment created in the
   :ref:`installation step <custom-data-installation>`:

   .. code-block:: bash

      source /path/to/miniforge3/etc/profile.d/conda.sh
      conda activate reconeval

4. After Conda activation, add ``cd /path/to/ReconEval`` and your task's
   **Run from CLI** command to the ``.sbatch`` file. Adjust the paths
   and training options.

5. Create the log directory **before** submission, from the repository root:

   .. code-block:: bash

      mkdir -p logs/slurm


**NB!** Each task includes the variables supported by its submission scripts. 
You can configure each submission script using task-specific environment variables. 
To change other training settings, edit the Python command inside
your copied ``.sbatch`` file.

Check the AE training run with exported environment variables as an example:

.. code-block:: bash

   export DATA=mydata
   export LATENT=128
   export MAX_EPOCHS=100
   export MIN_EPOCHS=10

   sbatch --export=ALL experiments/01_end_to_end/submit/train_ae.sbatch


.. _custom-data-end-to-end:

3. End-to-end
----------------------------------------------

3.1. Add the preprocessed dataset
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

- For AE and the scVI variants, provide:

  .. code-block:: text

     /path/to/mydata/
     ├── train.zarr
     ├── val.zarr
     └── test.zarr

- PCA instead reads ``train.h5ad`` from the same
  directory, with expression stored as a CSR matrix in ``.X``.


3.2. Run from CLI
~~~~~~~~~~~~~~~~~~~~~~~~~

**Run with a YAML configuration:**

1. Activate the `reconeval` environment from the :ref:`installation step <custom-data-installation>` by using `cstm_scvi_env.yaml` file.
2. Use ``template.yaml`` and the example YAML files to create
   your own ``mydata.yaml`` configuration.
   Save it in ``experiments/01_end_to_end/configs/data/``.

3. Replace the required ``???`` fields and keep the
   model-specific dataloader settings, e.g.:

   .. code-block:: yaml

      name: mydata
      path: /path/to/mydata
      input_dim: 2000

4. Run model training with your ``mydata.yaml`` configuration.

   For example, train an AE:

   .. code-block:: bash

      python experiments/01_end_to_end/codes/train.py \
        model=train/AE \
        trainer=AE \
        data=mydata \
        model.model_args.n_latent=128

**Alternatively, you can use command-line overrides:**

Use the same copied ``mydata.yaml`` and supply or override its settings
for an individual run:

.. code-block:: bash

   python experiments/01_end_to_end/codes/train.py \
     model=train/AE \
     trainer=AE \
     data=mydata \
     data.name=new_mydata \
     data.path=/path/to/new_mydata

**NB!**

- Both options use Hydra's ``key=value`` syntax. 
- ``data=mydata`` selects ``configs/data/mydata.yaml``.
- Command-line values take precedence over YAML.

**Model selection:**

Available models:

- AE
- scVI
- nlscVI
- mlscVI
- PCA

**Common overrides:**

Required fields must be set in your dataset YAML or through command-line
overrides. Data-loader defaults below refer to ``template.yaml``;
trainer defaults refer to the selected AE or scVI configuration.
VAE refers to ``scVI``, ``nlscVI``, and ``mlscVI``.

.. csv-table::
   :header: "Override", "Required / optional", "Meaning"
   :widths: 40, 30, 30

   "``data.name=mydata``", "Required", "Dataset label used in output paths and logs"
   "``data.path=/path/to/mydata``", "Required", "Directory containing the input split files"
   "``data.input_dim=2000``", "Required", "Number of expression columns in the input data"
   "``data.model_specific.AE.minibatch_size=256``", "Optional; default: 256", "Cells per batch; replace AE with the selected non-PCA model"
   "``data.model_specific.AE.num_workers=0``", "Optional; default: 0", "Data-loading workers; replace AE with the selected non-PCA model"
   "``trainer.max_epochs=100``", "Optional; default: 100", "Maximum epochs for AE and scVI variants"
   "``trainer.min_epochs=10``", "Optional; default: AE 10; scVI variants 30", "Minimum training epochs"
   "``seed=42``", "Optional; default: 42", "Random seed"
   "``split=split03``", "Optional; default: split03", "Split label"
   "``model.model_args.n_hidden=[1024]``", "Optional; AE default: [1024]", "AE hidden-layer widths; list length determines depth"
   "``model.model_args.n_hidden=1024``", "Optional; VAE default: 1024", "VAE hidden-layer width"
   "``model.model_args.n_latent=128``", "Optional; default: AE 100; VAE 300", "Latent dimension"
   "``model.model_args.n_layers=3``", "Optional; VAE default: 3", "VAE number of hidden layers"
   "``model.model_args.library_size_mode=none``", "Optional; AE default: none", "AE library-size handling: none disables scaling; observed uses the input expression sum per cell; modeled learns the scale"
   "``model.model_args.use_observed_lib_size=true``", "Optional; scVI/nlscVI default: true; mlscVI default: false", "VAE library-size handling: true uses observed totals; false infers library size"

**NB!** For ``nlscVI``, ``use_observed_lib_size`` controls library-size
inference, but the decoder does not scale its output by library size.

**NB!** Before running PCA, replace the default ``temp_dir`` in
``ReconPCA._setup_cluster``
(``src/sc_reconstruction/models/reconpca.py``) with a writable
directory for temporary files on your machine.

3.3. Run through SLURM
~~~~~~~~~~~~~~~~~~~~~~

1. Use ``template.yaml`` and the example YAML files to create
   your own ``mydata.yaml`` configuration.
   Save it in ``experiments/01_end_to_end/configs/data/``.
2. Fill all required fields in ``mydata.yaml``. 
3. Set up SLURM parameters in your sbatch script as described in :ref:`section 2 <slurm-parameters>`.
4. Run the script with your dataset configuration, e.g. for AE:

.. code-block:: bash

   export DATA=mydata
   export LATENT=128
   export MAX_EPOCHS=100
   export MIN_EPOCHS=10

   sbatch --export=ALL experiments/01_end_to_end/submit/train_ae.sbatch


3.4. Outputs
~~~~~~~~~~~~
**Model files**

Training saves model outputs under:

- ``RECONEVAL_OUT`` is set: ``$RECONEVAL_OUT/weights/mydata/<split>/<model>/<note>/``
- ``RECONEVAL_OUT`` is unset: ``~/reconeval_outputs/weights/<dataset>/<split>/<model>/<note>/``

The directory names correspond to configuration settings:

- ``<dataset>``: ``data.name``, such as ``mydata``
- ``<split>``: ``split``, which defaults to ``split03``
- ``<model>``: ``model.meta.name``, such as ``AE`` or ``scVI``
- ``<note>``: ``model.meta.note``, which defaults to ``Default``

The saved files depend on the selected model:

- **AE:** ``.ckpt`` checkpoints
- **scVI variants:** ``.pt`` checkpoints
- **PCA:** ``mean.zarr`` and ``pc_<n_components>.zarr``, containing
  the training mean and principal-component matrix. Both are needed
  for reconstruction.

**NB!** AE and the scVI variants place checkpoints beneath an additional run
directory named by ``model.save.filename``. By default, this name
includes training settings and the date.

**Logs and configuration**

Using the same output root:

- ``logs/`` is the configured W&B logging directory.
- ``outputs/<dataset>/<model>/<YYYY-MM-DD_HH-MM>/`` contains Hydra's
  run files, including configuration and overrides under ``.hydra/``.

For SLURM jobs, the supplied submission scripts also write standard
output and error logs to ``logs/slurm/`` relative to the submission
directory.

4. Foundation model
------------------------------------------------

.. _custom-data-mlp-data:

4.1. Add embeddings and expression targets
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Generate embeddings following instructions in :doc:`tutorials/fm`, take into consideration that each model requires
its own environment (see `README <https://github.com/theislab/ReconEval/blob/main/envs/README.md>`_ in the ReconEval repository`).

2. Provide the following files for MLP decoder:

.. code-block:: text

   /path/to/mydata/
   ├── embeddings/
   │   ├── train.zarr/
   │   └── val.zarr/
   ├── all_genes.zarr/
   └── target_genes.zarr/

**NB!** Each of ``.zarr`` files should contain two arrays: expression and embeddings under ``SE``, ``scGPT``, ``scConcept``, or ``SCimilarity``.

.. _custom-data-mlp-cli:

4.2. Run from CLI
~~~~~~~~~~~~~~~~~

**Run the MLP decoder:**

1. Activate ``reconeval`` defined in :ref:`installation step <custom-data-installation>`.

2. Set the paths and embedding key, then train the decoder. Decoder training does not require YAML configuration file. For ``SE`` embeddings:

   .. code-block:: bash

      python experiments/02_foundation_model/codes/train_decoder_from_embedding.py \
        --emb-train-zarr /path/to/mydata/embeddings/train.zarr \
        --emb-val-zarr /path/to/mydata/embeddings/val.zarr \
        --all-genes-zarr /path/to/mydata/all_genes.zarr \
        --target-genes-zarr /path/to/mydata/target_genes.zarr \
        --embedding-key SE \
        --num-workers 0 \
        --epochs 500 \
        --out /path/to/results/mydata/SE/MLP

**Required inputs and common optional settings:**

.. csv-table::
   :header: "Flag", "Required / optional", "Meaning"
   :widths: 30, 30, 40

   "``--emb-train-zarr``", "Required", "Training store containing expression and embeddings"
   "``--emb-val-zarr``", "Required", "Validation store containing expression and embeddings"
   "``--all-genes-zarr``", "Required", "Store whose var_names attribute lists the expression columns in order"
   "``--target-genes-zarr``", "Required", "Store whose var_names attribute lists the genes to reconstruct"
   "``--embedding-key``", "Required", "Embedding array name: SE, scGPT, scConcept, or scimilarity"
   "``--out``", "Required", "Output directory for checkpoints and configuration"
   "``--epochs``", "Optional; default: 500", "Maximum training epochs"
   "``--batch-size``", "Optional; default: 256", "Cells per batch"
   "``--lr``", "Optional; default: 0.0001", "Learning rate"
   "``--n-layers``", "Optional; default: 1", "Number of hidden layers"
   "``--hidden``", "Optional; default: 4096", "Hidden-layer width"
   "``--num-workers``", "Optional; default: 16", "Data-loading workers; use 0 to load data in the main process"
   "``--seed``", "Optional; default: 42", "Random seed"

4.3. Run through SLURM
~~~~~~~~~~~~~~~~~~~~~~

1. Configure your ``.sbatch`` script as described in
   :ref:`section 2 <slurm-parameters>`, using the command from
   :ref:`section 4.2 <custom-data-mlp-cli>`.
2. Set the input paths, embedding key, output directory, and training options.
3. Run your script from the repository root:

.. code-block:: bash

   sbatch --export=ALL /path/to/train_mydata_mlp.sbatch

4.4. Outputs
~~~~~~~~~~~~

**Model files**

Training saves model outputs in the directory specified by ``--out``,
such as ``/path/to/results/mydata/SE/MLP/``.

- **MLP:** a ``.ckpt`` checkpoint with the lowest validation loss.

**Logs and configuration**

- ``config.yaml`` in the same directory records the run settings, including
  the embedding dimension (``latent_dim``) and number of output genes
  (``gene_dim``).
- For SLURM jobs, log locations follow the ``#SBATCH`` settings in your
  submission script.

5. Latent shift
--------------------------------------------------

For STATE and CellFlow, generate embeddings using a model trained in
:ref:`section 3 <custom-data-end-to-end>` or a pretrained foundation model
(:ref:`section 4.1 <custom-data-mlp-data>`). Use the same encoder for all
splits and save embeddings in ``.obsm`` (e.g. ``.obsm["X_AE_128"]``).

5.1. Add expression, embeddings, and conditions
~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~

1. Choose a representation and width from the training script's ``EMB_DIMS``
   and prepare the corresponding embeddings (e.g. ``AE_128``).
2. Provide the following files for STATE and CellFlow:

.. code-block:: text

   /path/to/mydata/
   ├── train/train.h5ad
   ├── val/val.h5ad
   └── test/test.h5ad

**NB!** Each ``.h5ad`` file should contain:

- Expression in ``.X`` and embeddings in ``.obsm["X_AE_128"]`` (for ``AE_128``),
  with matching cell order. Expression genes must follow the order expected
  by the decoder.
- Metadata in ``.obs["donor"]``, ``.obs["cell_type"]``, and
  ``.obs["target_gene"]``.
- Controls labelled ``PBS`` in ``.obs["target_gene"]`` for the
  donor/cell-type groups being predicted.

Adapt the metadata keys and control labels to your dataset.

.. _custom-data-state-cli:

5.2. Run STATE from CLI
~~~~~~~~~~~~~~~~~~~~~~~

**Run STATE:**

1. Activate ``reconeval-pancellflow`` from the
   :ref:`installation step <custom-data-installation>`.

2. Copy ``template_train.toml`` and ``template_val.toml`` from
   ``experiments/03_latent_shift/configs/st/`` to ``mydata_train.toml`` and
   ``mydata_val.toml`` in the same directory. Set the split directories in
   ``[datasets]`` and use matching dataset names in ``[training]``.
   Keep the ``"train"`` value in both files; the script uses a separate
   data module's training loader for validation.

3. In ``experiments/03_latent_shift/codes/train_st.py``, point
   ``build_data_module`` and ``build_val_data_module`` to those TOML files.
   Update ``DATA_KWARGS_COMMON`` for your metadata keys and control label.

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

.. _custom-data-cellflow-cli:

5.3. Run CellFlow from CLI
~~~~~~~~~~~~~~~~~~~~~~~~~~

**Run CellFlow:**

1. Activate ``reconeval-pancellflow`` from the
   :ref:`installation step <custom-data-installation>`.

2. In ``experiments/03_latent_shift/codes/train_cf.py``, set ``DATA_ROOT``
   to ``/path/to/mydata`` and adapt the metadata/control labels if needed.

3. In ``train_cf.py``, update the block that calls ``hf_hub_download()``
   with ``filename="pbmc_parse.h5ad"`` and reads ``uns/esm2_embeddings``
   to load your dataset's perturbation features. Retain a vector for every
   non-control perturbation across all splits, including any absent from
   training. Validation/test donor and cell-type labels must occur in the
   training categories.

4. Set the representation and output directory, then train CellFlow.
   For ``AE_128`` embeddings:

   .. code-block:: bash

      python experiments/03_latent_shift/codes/train_cf.py \
        --model AE_128 \
        --config repro \
        --num_iters 500000 \
        --batch_size 1024 \
        --valid_freq 50000 \
        --out_dir /path/to/results/mydata/cellflow

**Required inputs and common optional settings:**

.. csv-table::
   :header: "Flag", "Required / optional", "Meaning"
   :widths: 30, 30, 40

   "``--model``", "Required", "Representation listed in EMB_DIMS, e.g. AE_128"
   "``--config``", "Optional; default: repro", "Training preset: repro or paper"
   "``--num_iters``", "Optional; default: 500000", "Training iterations"
   "``--batch_size``", "Optional; default: 1024", "Cells per batch"
   "``--valid_freq``", "Optional; default: 50000", "Validation interval in iterations"
   "``--seed``", "Optional; default: 42", "Random seed"
   "``--out_dir``", "Optional; default: generated under out_root", "Exact run output directory; set a writable path for your run"
   "``--out_root``", "Optional; default: script's OUT_ROOT", "Output root used when out_dir is omitted"

**NB!** During training, metrics labelled ``test`` are computed on ``val/val.h5ad``.

5.4. Run through SLURM
~~~~~~~~~~~~~~~~~~~~~~

1. Configure your ``.sbatch`` script as described in
   :ref:`section 2 <slurm-parameters>`, using the command from
   :ref:`section 5.2 <custom-data-state-cli>` for STATE or
   :ref:`section 5.3 <custom-data-cellflow-cli>` for CellFlow.
   Activate ``reconeval-pancellflow`` in the script.
2. Set the representation, output directory, and training options,
   including the decoder checkpoint for STATE when needed.
3. Run your script from the repository root:

.. code-block:: bash

   # STATE
   sbatch --export=ALL /path/to/train_mydata_state.sbatch

   # CellFlow
   sbatch --export=ALL /path/to/train_mydata_cellflow.sbatch

5.5. Outputs
~~~~~~~~~~~~

**Model files**

- **STATE:** saves models under ``<out_root>/<run_name>/checkpoints/``,
  including the three best validation checkpoints, ``last.ckpt``, and
  ``final.ckpt``. The run name retains ``pbmc_split03`` even for custom
  data. An existing ``last.ckpt`` is used to resume training automatically.
- **CellFlow:** saves the best and last CellFlow model artifacts in the
  directory specified by ``--out_dir``. The best model is selected using
  validation data.

Set ``--out_root`` for STATE and ``--out_dir`` for CellFlow to writable
paths, as in the CLI examples. Their defaults use cluster-specific paths;
``RECONEVAL_OUT`` does not redirect these outputs.

**Logs and configuration**

- **STATE:** ``config.yaml`` and label mappings are saved in the run
  directory, alongside ``checkpoints/``.
- **CellFlow:** ``config.json``, ``training_logs.json``, and
  ``training_curves.png`` are saved in the output directory.
- For SLURM jobs, log locations follow the ``#SBATCH`` settings in your
  submission script.
