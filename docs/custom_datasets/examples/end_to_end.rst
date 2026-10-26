End-to-end reconstruction
=========================

:doc:`Back to examples <../examples>`

This example runs the end-to-end workflow on 500 cells and 500 genes from
the LuCA dataset.

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

         [PATHS AND APPTAINER SETUP]

         CMD=$(cat <<'COMMAND'
         [PYTHON COMMANDS]
         COMMAND
         )

         mkdir -p results/luca-demo/tmp
         apptainer exec [APPTAINER OPTIONS] \
             --env TMPDIR=/work/results/luca-demo/tmp \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval \
             bash -e -c "$CMD"

      Submit the script from the repository root:

      .. code-block:: bash

         mkdir -p logs
         sbatch [SLURM SCRIPT]

      .. dropdown:: Placeholder info:
         
         - ``[SLURM HEADERS]``: Slurm job specified with ``#SBATCH``
         - ``[PATHS AND APPTAINER SETUP]``: define the required paths and environment settings

         - ``[PYTHON COMMANDS]``: the full Python commands from the relevant **Direct** tabs
         - ``[APPTAINER OPTIONS]``:

           - ``--bind "$PWD:/work"``: mount the repository at ``/work``
           - ``--bind "$(realpath data):$(readlink data)"``: mount the target of the external data symlink
           - ``--pwd /work``: set the working directory
           - ``--nv``: enable NVIDIA GPU access

         - ``/path/to/reconeval-all.sif``: absolute path to your Apptainer image
         - ``[SLURM SCRIPT]``: the path to the ``.sbatch`` file for the step,
           e.g. ``custom_datasets_demo/01_end_to_end/submit/train.sbatch``

   .. tab-item:: Apptainer

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         apptainer exec --cleanenv --nv \
             --env TMPDIR=/work/results/luca-demo/tmp \
             --bind "$PWD:/work" \
             --bind "$(realpath data):$(readlink data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

      - Temporary files use ``results/luca-demo/tmp``
      - ``data`` is a symlink here; omit the extra mount if it is a regular folder

      Replace:

      - ``[PYTHON COMMAND]`` with the full command from the **Direct** tab of the relevant step
      - ``/path/to/reconeval-all.sif`` with the absolute path to your image

   .. tab-item:: Docker

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         docker run --rm --gpus all \
             -e TMPDIR=/work/results/luca-demo/tmp \
             -v "$PWD:/work" \
             -v "$(realpath data):$(readlink data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

      - Temporary files use ``results/luca-demo/tmp``
      - ``data`` is a symlink here; omit the extra mount if it is a regular folder

      Replace:
       
      - ``[PYTHON COMMAND]`` with the full command from the **Direct** tab of the relevant step
      - ``reconeval:latest`` with the name and tag of your Docker image

.. _end-to-end-prerequisites:

Prerequisites
-------------

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
             split.path=null

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
             -v "$(realpath data):$(readlink data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

To use your own dataset, see :doc:`Data preparation <../dataset_preparation>` details. 

**Convert the expression store to .h5ad**

Convert ``expression.zarr`` to ``expression.h5ad`` for reference PCA:

.. tab-set::

   .. tab-item:: Direct

      .. code-block:: bash

         # [PYTHON COMMAND]
         python experiments/preprocessing/zarr_to_h5ad.py \
             "$(realpath data)/luca/demo/expression.zarr"

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
             -v "$(realpath data):$(realpath data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

1. Train
-------------

Train **PCA**, **mlAE**, and **nlscVI** at latent dimensions 10, 32, and 128.

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
             'weights.dir=results/luca-demo/mlAE/10'

   .. tab-item:: Slurm

      The script sweeps **PCA**, **mlAE**, and **nlscVI** at latent dims 10, 32, and 128:

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/01_end_to_end/submit/train.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         apptainer exec --cleanenv --nv \
             --env TMPDIR=/work/results/luca-demo/tmp \
             --bind "$PWD:/work" \
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

Fit a reference PCA on all demo expression data for distributional evaluation.

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
             -v "$(realpath data):$(readlink data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Outputs:** ``results/luca-demo/reference-pca/mean.zarr``, ``pc_50.zarr``

For configuration details see :doc:`Reference PCA <../end_to_end/reference_pca>`.


3. Evaluate
-----------------

Reconstruct held-out expression and compute distributional metrics for PCA,
mlAE, and nlscVI at latent dimensions 10, 32, and 128.

.. tab-set::

   .. tab-item:: Direct

      Set ``<run>`` to your training-run folder and ``<checkpoint>`` to your decoder checkpoint filename:

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
             -v "$(realpath data):$(readlink data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Outputs:** ``results/luca-demo/<model>/<latent>/distributional.csv``

For configuration details see :doc:`Evaluate <../end_to_end/evaluate>`.


1. Plot distributional metrics
------------------------------

After evaluation, plot the four metrics against latent dimension for PCA, mlAE,
and nlscVI:

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
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         docker run --rm \
             -e TMPDIR=/work/results/luca-demo/tmp \
             -v "$PWD:/work" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Output:** ``results/luca-demo/plots/scaling_latent_distributional.svg``.

The figure compares model performance across latent dimensions on the small demo split.
Model performance may be limited by the small demo split.

.. figure:: /_static/demo/luca_distributional.svg
   :width: 100%

   Distributional metrics from the 500-cell, 500-gene LuCA demo. Each point
   is the mean over held-out combinations.


1. Extract embeddings (optional)
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
             -v "$(realpath data):$(readlink data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Outputs:** ``results/luca-demo/embeddings/<model>/<latent>.zarr``

For configuration details see
:doc:`Extract embeddings <../end_to_end/extract_embeddings>`.
