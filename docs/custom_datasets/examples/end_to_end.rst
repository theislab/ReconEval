End-to-end reconstruction
=========================

:doc:`Back to examples <../examples>`

This example runs the end-to-end workflow on 500 cells and 500 genes from
the LuCA dataset.

Besides **PCA**, this tutorial focuses on **AE**, the modeled library-size
variant (``mlAE``), and **VAE**, the no library-size variant (``nlscVI``).

How to run
----------

Run from the repository root. Containers use the same paths as **Direct**.

.. tab-set::

   .. tab-item:: Direct

      Activate the ``reconeval`` environment:

      .. code-block:: bash

         conda activate reconeval

      Then, from the repository root, run ``[PYTHON COMMAND]`` shown in the
      **Direct** tab of each step.

   .. tab-item:: Slurm

      Submit the ready-to-use scripts in ``custom_datasets_demo/01_end_to_end/submit/``
      from the repository root, also explore the :doc:`Slurm guide <../slurm>`.

      The provided scripts use **Apptainer** to run the Python commands.

      The scripts have the following structure:

      .. code-block:: bash

         #!/usr/bin/env bash

         [SLURM HEADERS]

         image=/path/to/reconeval-all.sif
         [PATHS AND APPTAINER SETUP]

         CMD=$(cat <<'COMMAND'
         [PYTHON COMMANDS]
         COMMAND
         )

         mkdir -p results/luca-demo/tmp
         apptainer exec [APPTAINER OPTIONS] \
             --env TMPDIR=/work/results/luca-demo/tmp \
             "$image" \
             conda run --no-capture-output -n reconeval \
             bash -e -c "$CMD"

      Submit the script from the repository root:

      .. code-block:: bash

         mkdir -p logs
         sbatch [SLURM SCRIPT]

      .. dropdown:: Note: Placeholder info
         :icon: info
         :color: info
         
         - ``[SLURM HEADERS]``: Slurm job specified with ``#SBATCH``
         - ``[PATHS AND APPTAINER SETUP]``: define the required paths and environment settings

         - ``[PYTHON COMMANDS]``: the full Python commands from the relevant **Direct** tabs
         - ``[APPTAINER OPTIONS]``:

           - ``--bind "$PWD:/work"``: mount the repository at ``/work``
           - ``--bind "$(realpath results):$(realpath results)"``: mount the canonical results target
           - ``--bind "$(realpath data):$(readlink data)"``: mount the target of the external data symlink
           - ``--pwd /work``: set the working directory
           - ``--nv``: enable NVIDIA GPU access

         - ``/path/to/reconeval-all.sif``: path to your Apptainer image; set it in each script
         - ``[SLURM SCRIPT]``: the path to the ``.sbatch`` file for the step,
           e.g. ``custom_datasets_demo/01_end_to_end/submit/train.sbatch``

   .. tab-item:: Apptainer

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         apptainer exec --cleanenv --nv \
             --env TMPDIR=/work/results/luca-demo/tmp \
             --bind "$PWD:/work" \
             --bind "$(realpath results):$(realpath results)" \
             --bind "$(realpath data):$(readlink data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

      - Temporary files use ``results/luca-demo/tmp``
      - ``data`` is a symlink here; omit the extra mount if it is a regular folder
      - ``results`` is a symlink here; omit the extra mount if it is a regular folder

      Replace:

      - ``[PYTHON COMMAND]`` with the full command from the **Direct** tab of the relevant step
      - ``/path/to/reconeval-all.sif`` with the absolute path to your image

   .. tab-item:: Docker

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         docker run --rm --gpus all \
             -e TMPDIR=/work/results/luca-demo/tmp \
             -v "$PWD:/work" \
             -v "$(realpath results):$(realpath results)" \
             -v "$(realpath data):$(readlink data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

      - Temporary files use ``results/luca-demo/tmp``
      - ``data`` is a symlink here; omit the extra mount if it is a regular folder
      - ``results`` is a symlink here; omit the extra mount if it is a regular folder

      Replace:
       
      - ``[PYTHON COMMAND]`` with the full command from the **Direct** tab of the relevant step
      - ``reconeval:latest`` with the name and tag of your Docker image

In a nutshell
-------------

The full pipeline from **Direct** tabs:

.. code-block:: bash

   # Activate environment
   conda activate reconeval

   # 0. Prerequisites: Prepare dataset
   python experiments/preprocessing/prepare_dataset.py \
       --config-name data/luca \
       utils=experiments/preprocessing/utils/luca.py \
       input=data/luca/core_250130.h5ad \
       output=data/luca/demo \
       demo=true \
       demo_cells=500 \
       demo_genes=500 \
       seed=42 \
       split.strategy=combination \
       split.path=null \
       +save_counts=true #raw counts for Geneformer and UCE in the foundation-model example

   # 0. Prerequisites: Convert training and full expression stores to .h5ad
   python experiments/preprocessing/zarr_to_h5ad.py \
       "$(realpath data)/luca/demo/expression.zarr" \
       "$(realpath data)/luca/demo/train.zarr"

   # 1. Train (example: mlAE, latent dim 10)
   python experiments/01_end_to_end/codes/train.py \
       --config-dir custom_datasets_demo/01_end_to_end/configs \
       data=custom_luca_demo \
       model=train/AE \
       trainer=AE \
       model.meta.name=mlAE \
       model.model_args.library_size_mode=modeled \
       'model.model_args.n_hidden=[1024]' \
       model.model_args.n_latent=10 \
       'weights.dir=results/luca-demo/mlAE/10' \
       +model.logging.wandb.offline=true #AE and VAE log to Weights & Biases; offline saves logs locally

   # 2. Reference PCA
   python experiments/01_end_to_end/codes/train.py \
       --config-dir custom_datasets_demo/01_end_to_end/configs \
       data=custom_luca_demo \
       model=train/PCA \
       trainer=PCA \
       data.model_specific.PCA.train_path=data/luca/demo/expression.h5ad \
       'trainer.temp_dir=${weights.dir}/pca-work' \
       model.model_args.n_components=50 \
       weights.dir=results/luca-demo/reference-pca

   # 3. Evaluate (distributional metrics, mlAE latent dim 10)
   python experiments/01_end_to_end/codes/eval_distributional.py \
       --config-dir custom_datasets_demo/01_end_to_end/configs \
       --config-name base_eval_demo \
       model=eval/AE \
       model.meta.name=mlAE \
       metric=_distributional \
       'metric.projector.load.path=[results/luca-demo/reference-pca/mean.zarr,results/luca-demo/reference-pca/pc_50.zarr]' \
       "model.load.path='results/luca-demo/mlAE/10/<run>/<checkpoint>'" \
       "model.load.model_name='<run>'" \
       output.save_path=results/luca-demo/mlAE/10/distributional.csv

   # 4. Plot distributional metrics
   python custom_datasets_demo/01_end_to_end/codes/plot_metrics.py \
       --results-dir results/luca-demo

   # 5. (Optional) Extract embeddings
   python experiments/01_end_to_end/codes/extract_e2e_embeddings.py \
       --hvg_zarr data/luca/demo/expression.zarr \
       --model AE \
       --ckpt "results/luca-demo/mlAE/10/<run>/<checkpoint>" \
       --out results/luca-demo/embeddings/mlAE/10.zarr

.. _end-to-end-prerequisites:

0. Prerequisites
----------------

**Prepare the dataset**

The commands below prepare the LuCA demo and save the output to ``data/luca/demo/``:

.. tab-set::

   .. tab-item:: Direct

      .. code-block:: bash

         # [PYTHON COMMAND]
         python experiments/preprocessing/prepare_dataset.py \
             --config-name data/luca \
             utils=experiments/preprocessing/utils/luca.py \
             input=data/luca/core_250130.h5ad \
             output=data/luca/demo \
             demo=true \
             demo_cells=500 \
             demo_genes=500 \
             seed=42 \
             split.strategy=combination \
             split.path=null \
             +save_counts=true #raw counts for Geneformer and UCE in the foundation-model example

   .. tab-item:: Slurm

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/preprocessing/submit/prepare_dataset.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         apptainer exec --cleanenv \
             --env TMPDIR=/work/results/luca-demo/tmp \
             --bind "$PWD:/work" \
             --bind "$(realpath results):$(realpath results)" \
             --bind "$(realpath data):$(readlink data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         docker run --rm \
             -e TMPDIR=/work/results/luca-demo/tmp \
             -v "$PWD:/work" \
             -v "$(realpath results):$(realpath results)" \
             -v "$(realpath data):$(readlink data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

To use your own dataset, see :doc:`Data preparation <../dataset_preparation>` details. 

**Convert the expression stores to .h5ad**

Convert ``train.zarr`` to ``train.h5ad`` for the **PCA** reconstruction baseline,
and ``expression.zarr`` to ``expression.h5ad`` for reference **PCA**:

.. tab-set::

   .. tab-item:: Direct

      .. code-block:: bash

         # [PYTHON COMMAND]
         python experiments/preprocessing/zarr_to_h5ad.py \
             "$(realpath data)/luca/demo/expression.zarr" \
             "$(realpath data)/luca/demo/train.zarr"

   .. tab-item:: Slurm

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/preprocessing/submit/zarr_to_h5ad.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         apptainer exec --cleanenv \
             --env TMPDIR=/work/results/luca-demo/tmp \
             --bind "$PWD:/work" \
             --bind "$(realpath results):$(realpath results)" \
             --bind "$(realpath data):$(realpath data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         docker run --rm \
             -e TMPDIR=/work/results/luca-demo/tmp \
             -v "$PWD:/work" \
             -v "$(realpath results):$(realpath results)" \
             -v "$(realpath data):$(realpath data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

1. Train
-------------

Train **PCA**, **AE**, and **VAE** at latent dimensions 10, 32, and 128.

The **PCA** baseline is fitted on training cells only, using ``train.h5ad``.

The ``[PYTHON COMMAND]`` example below shows one model; the Slurm script sweeps all three:

.. tab-set::

   .. tab-item:: Direct

      .. code-block:: bash

         # [PYTHON COMMAND]
         ## mlAE, latent dim 10
         python experiments/01_end_to_end/codes/train.py \
             --config-dir custom_datasets_demo/01_end_to_end/configs \
             data=custom_luca_demo \
             model=train/AE \
             trainer=AE \
             model.meta.name=mlAE \
             model.model_args.library_size_mode=modeled \
             'model.model_args.n_hidden=[1024]' \
             model.model_args.n_latent=10 \
             'weights.dir=results/luca-demo/mlAE/10' \
             +model.logging.wandb.offline=true #AE and VAE log to Weights & Biases; offline saves logs locally

   .. tab-item:: Slurm

      The script submits nine array tasks: **PCA**, **AE**, and **VAE**
      at latent dims 10, 32, and 128. Each task requests one GPU and can run
      in parallel as cluster resources become available:

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/01_end_to_end/submit/train.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         apptainer exec --cleanenv --nv \
             --env TMPDIR=/work/results/luca-demo/tmp \
             --bind "$PWD:/work" \
             --bind "$(realpath results):$(realpath results)" \
             --bind "$(realpath data):$(readlink data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         docker run --rm --gpus all \
             -e TMPDIR=/work/results/luca-demo/tmp \
             -v "$PWD:/work" \
             -v "$(realpath results):$(realpath results)" \
             -v "$(realpath data):$(readlink data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Outputs:** ``results/luca-demo/<model>/<latent>/``, for example
``results/luca-demo/mlAE/10/``

For configuration details see :doc:`Train <../end_to_end/train>`.





.. _end-to-end-reference-pca:

2. Reference PCA
----------------------

Fit a reference **PCA** on all demo expression data in ``expression.h5ad``
for distributional evaluation.

Temporary files are stored in ``pca-work`` under ``weights.dir``.

.. tab-set::

   .. tab-item:: Direct

      .. code-block:: bash

         # [PYTHON COMMAND]
         python experiments/01_end_to_end/codes/train.py \
             --config-dir custom_datasets_demo/01_end_to_end/configs \
             data=custom_luca_demo \
             model=train/PCA \
             trainer=PCA \
             data.model_specific.PCA.train_path=data/luca/demo/expression.h5ad \
             'trainer.temp_dir=${weights.dir}/pca-work' \
             model.model_args.n_components=50 \
             weights.dir=results/luca-demo/reference-pca

   .. tab-item:: Slurm

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/01_end_to_end/submit/reference_pca.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         apptainer exec --cleanenv --nv \
             --env TMPDIR=/work/results/luca-demo/tmp \
             --bind "$PWD:/work" \
             --bind "$(realpath results):$(realpath results)" \
             --bind "$(realpath data):$(readlink data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         docker run --rm --gpus all \
             -e TMPDIR=/work/results/luca-demo/tmp \
             -v "$PWD:/work" \
             -v "$(realpath results):$(realpath results)" \
             -v "$(realpath data):$(readlink data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Outputs:** ``results/luca-demo/reference-pca/mean.zarr``, ``pc_50.zarr``

For configuration details see :doc:`Reference PCA <../end_to_end/reference_pca>`.


3. Evaluate
-----------------

Reconstruct held-out expression and compute distributional metrics for **PCA**,
**AE**, and **VAE** at latent dimensions 10, 32, and 128.

.. tab-set::

   .. tab-item:: Direct

      Set ``<run>`` to your training-run folder and ``<checkpoint>`` to the checkpoint path inside it:

      **Distributional metrics**

      .. code-block:: bash

         # [PYTHON COMMAND]
         ## mlAE, latent dim 10, distributional metrics
         python experiments/01_end_to_end/codes/eval_distributional.py \
             --config-dir custom_datasets_demo/01_end_to_end/configs \
             --config-name base_eval_demo \
             model=eval/AE \
             model.meta.name=mlAE \
             metric=_distributional \
             'metric.projector.load.path=[results/luca-demo/reference-pca/mean.zarr,results/luca-demo/reference-pca/pc_50.zarr]' \
             "model.load.path='results/luca-demo/mlAE/10/<run>/<checkpoint>'" \
             "model.load.model_name='<run>'" \
             output.save_path=results/luca-demo/mlAE/10/distributional.csv

   .. tab-item:: Slurm

      Set the explicit checkpoint paths in the script's ``mlae_checkpoints`` and
      ``nlscvi_checkpoints`` arrays, then submit it:

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/01_end_to_end/submit/evaluate.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         apptainer exec --cleanenv \
             --env TMPDIR=/work/results/luca-demo/tmp \
             --bind "$PWD:/work" \
             --bind "$(realpath results):$(realpath results)" \
             --bind "$(realpath data):$(readlink data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         docker run --rm \
             -e TMPDIR=/work/results/luca-demo/tmp \
             -v "$PWD:/work" \
             -v "$(realpath results):$(realpath results)" \
             -v "$(realpath data):$(readlink data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Outputs:** ``results/luca-demo/<model>/<latent>/distributional.csv``

For configuration details see :doc:`Evaluate <../end_to_end/evaluate>`.


4. Plot distributional metrics
------------------------------

After evaluation, plot the four metrics against latent dimension for **PCA**, **AE**,
and **VAE**:

.. tab-set::

   .. tab-item:: Direct

      .. code-block:: bash

         # [PYTHON COMMAND]
         ## Plot all distributional metrics
         python custom_datasets_demo/01_end_to_end/codes/plot_metrics.py \
             --results-dir results/luca-demo

   .. tab-item:: Slurm

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/01_end_to_end/submit/plot_metrics.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         apptainer exec --cleanenv \
             --env TMPDIR=/work/results/luca-demo/tmp \
             --bind "$PWD:/work" \
             --bind "$(realpath results):$(realpath results)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         docker run --rm \
             -e TMPDIR=/work/results/luca-demo/tmp \
             -v "$PWD:/work" \
             -v "$(realpath results):$(realpath results)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Output:** ``results/luca-demo/plots/scaling_latent_distributional.svg``.

For reference, the figure below shows models trained on the full LuCA dataset.

.. figure:: /_static/demo/luca_distributional.svg
   :width: 100%

   Full LuCA test metrics (70/15/15 train/val/test split by combination;
   seed 42 for splitting and training):
   unweighted means over 155 held-out combinations.
   ``(rev)`` marks negated metrics; higher is better.


5. Extract embeddings (optional)
--------------------------------------

Extract latent representations from trained models for downstream tasks
such as perturbation response modelling.

Use the same checkpoint file as in evaluation.

.. tab-set::

   .. tab-item:: Direct

      .. code-block:: bash

         # [PYTHON COMMAND]
         ## mlAE, latent dim 10
         python experiments/01_end_to_end/codes/extract_e2e_embeddings.py \
             --hvg_zarr data/luca/demo/expression.zarr \
             --model AE \
             --ckpt "results/luca-demo/mlAE/10/<run>/<checkpoint>" \
             --out results/luca-demo/embeddings/mlAE/10.zarr

   .. tab-item:: Slurm

      Set ``mlae_checkpoints`` and ``nlscvi_checkpoints`` in the script to the
      same explicit checkpoint files used for evaluation. The script extracts
      embeddings for all demo models and latent dimensions:

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/01_end_to_end/submit/extract_embeddings.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         apptainer exec --cleanenv --nv \
             --env TMPDIR=/work/results/luca-demo/tmp \
             --bind "$PWD:/work" \
             --bind "$(realpath results):$(realpath results)" \
             --bind "$(realpath data):$(readlink data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         docker run --rm --gpus all \
             -e TMPDIR=/work/results/luca-demo/tmp \
             -v "$PWD:/work" \
             -v "$(realpath results):$(realpath results)" \
             -v "$(realpath data):$(readlink data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Outputs:** ``results/luca-demo/embeddings/<model>/<latent>.zarr``

For configuration details see
:doc:`Extract embeddings <../end_to_end/extract_embeddings>`.


Runtime
-------

**Time vs number of cells**

.. figure:: /_static/demo/luca_runtime.svg
   :width: 100%
   :alt: AE, VAE, and PCA training time against cell count at five latent dimensions.

   Total training time vs number of cells on LuCa slices, one panel per latent dimension; mean ± SD over 3 runs. 

.. dropdown:: Note: details on plots
   :icon: info
   :color: info

   - **Models:** AE, VAE, and PCA
   - **Latent dimensions:** 10, 32, 128, 512, and 2048 (where applicable)
   - **Hidden width × depth:** 1024 × 1 (where applicable)
   - **Data:** LuCA slices with 500, 1000, 10000, 100000, and 892296 cells
   - **Hardware:**

     - **GPU:** 1 × NVIDIA H100 80GB
     - **CPU:** 20 × Intel Xeon Platinum 8480+
     - **RAM:** 128 GB

**Time vs TFLOPs**

.. figure:: /_static/demo/time_vs_flops_per_epoch.svg
   :width: 50%
   :alt: AE and VAE training time per epoch against TFLOPs per epoch or fit.

   Training time per epoch vs TFLOPs per epoch or fit on full LuCA; mean ± SD over 3 runs.
   The broken logarithmic x-axis separates PCA from AE and VAE.

.. dropdown:: Note: details on plot
   :icon: info
   :color: info

   - **Models:** AE, VAE, and PCA
   - **Latent dimension:** 2048
   - **Hidden widths × depths:** 1024, 2048, 4096 × 1, 2, 4   
   - **Data:** full LuCA with 892296 cells
   - **Hardware:**

     - **GPU:** 1 × NVIDIA H100 80GB
     - **CPU:** 20 × Intel Xeon Platinum 8480+
     - **RAM:** 128 GB

   - **Time:**

     - AE/VAE: wall time per epoch
     - PCA: fit time

   - **TFLOPs** (:math:`10^{12}` FLOPs):

     - AE/VAE: train/val matrix operations per epoch, excluding optimizer steps, elementwise operations, and I/O
     - PCA: estimated fit operations, excluding projection

**TFLOPs vs width × depth**

.. figure:: /_static/demo/flops_with_pca.png
   :width: 100%
   :alt: AE/VAE and PCA TFLOPs across architectures and latent dimensions.

   TFLOPs across widths x depths and latent dimensions on full LuCA. AE/VAE: TFLOPs per training/validation epoch; dashed PCA: estimated TFLOPs per fit, excluding projection.


.. _custom-data-e2e-time-estimates:

**Estimated time per dataset**

.. tab-set::

   .. tab-item:: Average per run

      .. csv-table:: Estimated compute cost averaged over configurations and splits, in hours
         :file: average_time_estimates.csv
         :header-rows: 1
         :stub-columns: 1
         :widths: 1, 1, 1, 1, 1, 1, 1, 1

   .. tab-item:: Full benchmark

      .. csv-table:: Estimated compute cost across all configurations and splits, in hours
         :file: training_time_estimates.csv
         :header-rows: 1
         :stub-columns: 1
         :widths: 1, 1, 1, 1, 1, 1, 1, 1

.. dropdown:: Note: details on estimates
   :icon: info
   :color: info

   - **Hidden widths × depths:** 1024, 2048, 4096 × 1-4
   - **Latent dimensions:**

     - AE, VAE, and PCA: 10, 32, 128, 512, and 2048
     - MLP: the foundation model's embedding size

   - **Data:** LuCA, PBMC, and Tahoe; 3 splits
   - **Runs:** one configuration on each split; embeddings once per model and dataset
   - **Hardware:**

     - **GPU:** 1 × NVIDIA H100 80GB
     - **CPU:** 20 × Intel Xeon Platinum 8480+
     - **RAM:** 128 GB

   - **Time:**

     - AE, VAE, and MLP training
     - PCA fit
     - embedding extraction and combination
   - **PBMC and Tahoe** are rough extrapolations of the LuCA timings
