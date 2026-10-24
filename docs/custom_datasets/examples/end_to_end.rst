End-to-end reconstruction
=========================

:doc:`Back to examples <../examples>`

This example runs the end-to-end workflow on 500 cells and 500 genes from
the LuCA dataset.

How to run
----------

Run from the repository root. Containers use the same paths as **Direct**.
Keep the extra data mount only if ``data`` links outside the repository.

.. tab-set::

   .. tab-item:: Direct

      Activate the ``reconeval`` environment:

      .. code-block:: bash

         conda activate reconeval

      Then, from the repository root, run ``[PYTHON COMMAND]`` shown in the
      **Direct** tab of each step.

   .. tab-item:: Slurm

      Submit the ready-to-use scripts in ``custom_datasets_demo/01_end_to_end/``
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

         apptainer exec [APPTAINER OPTIONS] \
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
           - ``--bind "$(realpath data):$(realpath data)"``: preserve access to external data
           - ``--pwd /work``: set the working directory
           - ``--nv``: enable NVIDIA GPU access

         - ``/path/to/reconeval-all.sif``: absolute path to your Apptainer image
         - ``[SLURM SCRIPT]``: the path to the ``.sbatch`` file for the step,
           e.g. ``custom_datasets_demo/01_end_to_end/train.sbatch``

   .. tab-item:: Apptainer

      .. code-block:: bash

         apptainer exec --cleanenv --nv \
             --bind "$PWD:/work" \
             --bind "$(realpath data):$(realpath data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

      Replace:

      - ``[PYTHON COMMAND]`` with the full command from the **Direct** tab of the relevant step
      - ``/path/to/reconeval-all.sif`` with the absolute path to your image

   .. tab-item:: Docker

      .. code-block:: bash

         docker run --rm --gpus all \
             -v "$PWD:/work" \
             -v "$(realpath data):$(realpath data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

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
             --config-name luca \
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
         sbatch custom_datasets_demo/preprocessing/prepare_dataset.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         apptainer exec --cleanenv \
             --bind "$PWD:/work" \
             --bind "$(realpath data):$(realpath data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         docker run --rm \
             -v "$PWD:/work" \
             -v "$(realpath data):$(realpath data)" \
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
             data/luca/demo/expression.zarr

   .. tab-item:: Slurm

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/preprocessing/zarr_to_h5ad.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         apptainer exec --cleanenv \
             --bind "$PWD:/work" \
             --bind "$(realpath data):$(realpath data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         docker run --rm \
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
         sbatch custom_datasets_demo/01_end_to_end/train.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         apptainer exec --cleanenv --nv \
             --bind "$PWD:/work" \
             --bind "$(realpath data):$(realpath data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         docker run --rm --gpus all \
             -v "$PWD:/work" \
             -v "$(realpath data):$(realpath data)" \
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
             data=custom_luca_demo \
             model=train/PCA \
             trainer=PCA \
             'trainer.temp_dir=${weights.dir}/pca-work' \
             model.model_args.n_components=50 \
             weights.dir=results/luca-demo/reference-pca

   .. tab-item:: Slurm

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/01_end_to_end/reference_pca.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         apptainer exec --cleanenv --nv \
             --bind "$PWD:/work" \
             --bind "$(realpath data):$(realpath data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         docker run --rm --gpus all \
             -v "$PWD:/work" \
             -v "$(realpath data):$(realpath data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Outputs:** ``results/luca-demo/reference-pca/mean.zarr``, ``pc_50.zarr``

For configuration details see :doc:`Reference PCA <../end_to_end/reference_pca>`.


3. Evaluate
-----------------

Reconstruct held-out expression and score it. Runs distributional and
coexpression metrics for all trained models and latent dimensions.

.. tab-set::

   .. tab-item:: Direct

      Set ``<run>`` to your run folder and ``<checkpoint>`` to the checkpoint
      path inside it, without ``.ckpt``.

      **Distributional metrics**

      .. code-block:: bash

         # [PYTHON COMMAND]
         ## mlAE, latent dim 10, distributional metrics
         python experiments/01_end_to_end/codes/eval_distributional.py \
             --config-name base_eval_demo \
             model=eval/mlAE \
             metric=_distributional \
             'metric.projector.load.path=[results/luca-demo/reference-pca/mean.zarr,results/luca-demo/reference-pca/pc_50.zarr]' \
             "model.load.path='results/luca-demo/mlAE/10/<run>/<checkpoint>.ckpt'" \
             "model.load.model_name='<run>'" \
             output.save_path=results/luca-demo/mlAE/10/distributional.csv

      **Biological metrics**

      .. code-block:: bash

         # [PYTHON COMMAND]
         ## mlAE, latent dim 10, coexpression metrics
         python experiments/01_end_to_end/codes/eval_biological.py \
             --config-name base_eval_demo \
             model=eval/mlAE \
             metric=_coexpression \
             "model.load.path='results/luca-demo/mlAE/10/<run>/<checkpoint>.ckpt'" \
             "model.load.model_name='<run>'" \
             output.save_path=results/luca-demo/mlAE/10/coexpression.csv

   .. tab-item:: Slurm

      The script loops over all models and latent dimensions:

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/01_end_to_end/evaluate.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         apptainer exec --cleanenv \
             --bind "$PWD:/work" \
             --bind "$(realpath data):$(realpath data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         docker run --rm \
             -v "$PWD:/work" \
             -v "$(realpath data):$(realpath data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Outputs:** ``results/luca-demo/<model>/<latent>/distributional.csv``
and ``coexpression.csv``

For configuration details see :doc:`Evaluate <../end_to_end/evaluate>`.


4. Extract embeddings (optional)
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
             --ckpt "results/luca-demo/mlAE/10/<run>/<checkpoint>.ckpt" \
             --out results/luca-demo/embeddings/mlAE/10.zarr

   .. tab-item:: Slurm

      The script loops over all models and latent dimensions:

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/01_end_to_end/extract_embeddings.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         apptainer exec --cleanenv --nv \
             --bind "$PWD:/work" \
             --bind "$(realpath data):$(realpath data)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         docker run --rm --gpus all \
             -v "$PWD:/work" \
             -v "$(realpath data):$(realpath data)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Outputs:** ``results/luca-demo/embeddings/<model>/<latent>.zarr``

For configuration details see
:doc:`Extract embeddings <../end_to_end/extract_embeddings>`.
