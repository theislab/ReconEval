Foundation model reconstruction
===============================

:doc:`Back to examples <../examples>`

This example runs the foundation model workflow with SE on 500 cells and
500 genes from the LuCA dataset.

The Slurm scripts also run scGPT, scConcept, SCimilarity, Geneformer, UCE,
and scFoundation.

How to run
----------

Run from the repository root. Containers use the same paths as **Direct**.

.. tab-set::

   .. tab-item:: Direct

      Activate the environment for the step:

      .. code-block:: bash

         conda activate <reconeval-state | reconeval>

      - ``<reconeval-state | reconeval>``: use ``reconeval-state`` for SE embedding
        extraction and ``reconeval`` for all other steps. Other models extract
        embeddings in ``reconeval-<model>``, e.g. ``reconeval-geneformer``.

      Then, from the repository root, run ``[PYTHON COMMAND]`` shown in the
      **Direct** tab of each step.

   .. tab-item:: Slurm

      Submit the scripts in ``custom_datasets_demo/02_foundation_model/submit/``
      from the repository root. See the :doc:`Slurm guide <../slurm>`.

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
             conda run --no-capture-output -n <reconeval-state | reconeval> \
             bash -e -c "$CMD"

      Submit the script from the repository root:

      .. code-block:: bash

         mkdir -p logs
         sbatch [SLURM SCRIPT]

      .. dropdown:: Note: Placeholder info
         :icon: info
         :color: info

         - ``[SLURM HEADERS]``: Slurm job settings under ``#SBATCH``
         - ``[PATHS AND APPTAINER SETUP]``: define the required paths and environment settings

         - ``[PYTHON COMMANDS]``: the full Python commands from the relevant **Direct** tabs
         - ``<reconeval-state | reconeval>``: use ``reconeval-state`` for SE embedding
           extraction and ``reconeval`` for all other steps.
         - ``[APPTAINER OPTIONS]``:

           - ``--bind "$PWD:/work"``: mount the repository at ``/work``
           - ``--bind "$(realpath results):$(realpath results)"``: mount the canonical results target
           - ``--bind "$(realpath data):$(readlink data)"``: mount the target of the external data symlink
           - ``--bind "$(realpath checkpoints/pretrained):$(readlink checkpoints/pretrained)"``: mount the target of the checkpoint symlink
           - ``--pwd /work``: set the working directory
           - ``--nv``: enable NVIDIA GPU access

         - ``/path/to/reconeval-all.sif``: absolute path to your Apptainer image
         - ``[SLURM SCRIPT]``: the path to the ``.sbatch`` file for the step,
           e.g. ``custom_datasets_demo/02_foundation_model/submit/train.sbatch``

   .. tab-item:: Apptainer

      For steps with two Python commands, run this template once for each command,
      in the order shown.

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         apptainer exec --cleanenv --nv \
             --env TMPDIR=/work/results/luca-demo/tmp \
             --bind "$PWD:/work" \
             --bind "$(realpath results):$(realpath results)" \
             --bind "$(realpath data):$(readlink data)" \
             --bind "$(realpath checkpoints/pretrained):$(readlink checkpoints/pretrained)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n <reconeval-state | reconeval> [PYTHON COMMAND]

      - Temporary files use ``results/luca-demo/tmp``
      - ``data`` is a symlink here; omit the extra mount if it is a regular folder
      - ``results`` is a symlink here; omit the extra mount if it is a regular folder
      - ``checkpoints/pretrained`` is a symlink here; omit the extra mount if it is a regular folder

      Replace:

      - ``<reconeval-state | reconeval>`` with ``reconeval-state`` for SE embedding
        extraction and ``reconeval`` for all other steps.
      - ``[PYTHON COMMAND]`` with one full command from the **Direct** tab of the relevant step
      - ``/path/to/reconeval-all.sif`` with the absolute path to your image

   .. tab-item:: Docker

      For steps with two Python commands, run this template once for each command,
      in the order shown.

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         docker run --rm --gpus all \
             -e TMPDIR=/work/results/luca-demo/tmp \
             -v "$PWD:/work" \
             -v "$(realpath results):$(realpath results)" \
             -v "$(realpath data):$(readlink data)" \
             -v "$(realpath checkpoints/pretrained):$(readlink checkpoints/pretrained)" \
             -w /work \
             reconeval:latest \
             -n <reconeval-state | reconeval> [PYTHON COMMAND]

      - Temporary files use ``results/luca-demo/tmp``
      - ``data`` is a symlink here; omit the extra mount if it is a regular folder
      - ``results`` is a symlink here; omit the extra mount if it is a regular folder
      - ``checkpoints/pretrained`` is a symlink here; omit the extra mount if it is a regular folder

      Replace:

      - ``<reconeval-state | reconeval>`` with ``reconeval-state`` for SE embedding
        extraction and ``reconeval`` for all other steps.
      - ``[PYTHON COMMAND]`` with the full command from the **Direct** tab of the relevant step
      - ``reconeval:latest`` with the name and tag of your Docker image

In a nutshell
-------------

The full pipeline from **Direct** tabs:

.. code-block:: bash

   # Activate environment
   # SE embedding extraction uses reconeval-state; all other steps use reconeval.
   conda activate <reconeval-state | reconeval>

   # 0. Prerequisites: run the end-to-end prerequisites first
   # (prepare_dataset.py and zarr_to_h5ad.py; see end-to-end example)

   # 1. Prepare checkpoints
   conda activate reconeval
   python experiments/02_foundation_model/codes/download_checkpoints.py \
       --model all \
       --output-dir checkpoints/pretrained

   # 2. Prepare embeddings: extract SE embeddings
   conda activate reconeval-state
   python experiments/02_foundation_model/codes/SE_emb.py \
       model_args.checkpoint_path=checkpoints/pretrained/SE/se600m_epoch16.ckpt \
       model_args.protein_embeds_path=checkpoints/pretrained/SE/protein_embeddings.pt \
       data_args.comb_meta_root=data/luca/demo/expression.zarr \
       data_args.split_meta_root=data/luca/demo/split_metadata.zarr \
       data_args.target_key=null \
       data_args.output_dir=data/luca/demo/embeddings/SE/grouped.zarr \
       parts=1 \
       total_parts=1

   # 2. Prepare embeddings: combine expression and embeddings
   conda activate reconeval
   python experiments/preprocessing/combine_emb_zarr.py \
       --expression-zarr data/luca/demo/expression.zarr \
       --split-meta-zarr data/luca/demo/split_metadata.zarr \
       --embedding-zarr data/luca/demo/embeddings/SE/grouped.zarr \
       --embedding-key SE \
       --out-dir results/luca-demo/fm/SE/emb_combined

   # 3. Train MLP decoder
   python experiments/02_foundation_model/codes/train_decoder_from_embedding.py \
       --emb-train-zarr results/luca-demo/fm/SE/emb_combined/train.zarr \
       --emb-val-zarr results/luca-demo/fm/SE/emb_combined/val.zarr \
       --all-genes-zarr data/luca/demo/expression.zarr \
       --target-genes-zarr data/luca/demo/expression.zarr \
       --embedding-key SE \
       --reshuffle \
       --out results/luca-demo/fm/SE/MLP

   # 4. Reference PCA: reuse from end-to-end example

   # 5. Evaluate (distributional metrics, SE + MLP decoder)
   python experiments/02_foundation_model/codes/eval_decoder_statistical.py \
       --config-dir custom_datasets_demo/02_foundation_model/configs \
       --config-name base_eval_decode_demo \
       pretrained=SE \
       decoder=MLP \
       metric=decode_statistical_demo \
       "decoder.load.path='results/luca-demo/fm/SE/MLP/<checkpoint>'" \
       'metric.projector.load.path=[results/luca-demo/reference-pca/mean.zarr,results/luca-demo/reference-pca/pc_50.zarr]' \
       output.save_path=results/luca-demo/fm/SE/distributional.csv

0. Prerequisites
----------------

Prepare the dataset and convert the expression store as described in the
:ref:`end-to-end prerequisites <end-to-end-prerequisites>`.
Reuse ``data/luca/demo/`` if those steps are already complete.

1. Prepare checkpoints
----------------------

Download SE, scGPT, scConcept, SCimilarity, Geneformer, UCE, and scFoundation
checkpoints:

.. tab-set::

   .. tab-item:: Direct

      .. code-block:: bash

         conda activate reconeval
         python experiments/02_foundation_model/codes/download_checkpoints.py \
             --model all \
             --output-dir checkpoints/pretrained

   .. tab-item:: Slurm

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/02_foundation_model/submit/download_checkpoints.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         apptainer exec --cleanenv \
             --bind "$PWD:/work" \
             --bind "$(realpath checkpoints/pretrained):$(readlink checkpoints/pretrained)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval \
             python experiments/02_foundation_model/codes/download_checkpoints.py \
                 --model all \
                 --output-dir checkpoints/pretrained

   .. tab-item:: Docker

      .. code-block:: bash

         docker run --rm \
             -v "$PWD:/work" \
             -v "$(realpath checkpoints/pretrained):$(readlink checkpoints/pretrained)" \
             -w /work \
             reconeval:latest \
             -n reconeval \
             python experiments/02_foundation_model/codes/download_checkpoints.py \
                 --model all \
                 --output-dir checkpoints/pretrained


**Outputs:** pretrained checkpoints in ``checkpoints/pretrained/``


2. Prepare embeddings
---------------------

**Extract embeddings**

Run SE on all demo groups for decoder training and evaluation.

.. tab-set::

   .. tab-item:: Direct

      .. code-block:: bash

         # Activate the SE environment
         conda activate reconeval-state

         # [PYTHON COMMAND]
         python experiments/02_foundation_model/codes/SE_emb.py \
             model_args.checkpoint_path=checkpoints/pretrained/SE/se600m_epoch16.ckpt \
             model_args.protein_embeds_path=checkpoints/pretrained/SE/protein_embeddings.pt \
             data_args.comb_meta_root=data/luca/demo/expression.zarr \
             data_args.split_meta_root=data/luca/demo/split_metadata.zarr \
             data_args.target_key=null \
             data_args.output_dir=data/luca/demo/embeddings/SE/grouped.zarr \
             parts=1 \
             total_parts=1

   .. tab-item:: Slurm

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/02_foundation_model/submit/extract_embeddings.sbatch

   .. tab-item:: Apptainer

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         apptainer exec --cleanenv --nv \
             --env TMPDIR=/work/results/luca-demo/tmp \
             --bind "$PWD:/work" \
             --bind "$(realpath results):$(realpath results)" \
             --bind "$(realpath data):$(readlink data)" \
             --bind "$(realpath checkpoints/pretrained):$(readlink checkpoints/pretrained):ro" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval-state [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         mkdir -p results/luca-demo/tmp
         docker run --rm --gpus all \
             -e TMPDIR=/work/results/luca-demo/tmp \
             -v "$PWD:/work" \
             -v "$(realpath results):$(realpath results)" \
             -v "$(realpath data):$(readlink data)" \
             -v "$(realpath checkpoints/pretrained):$(readlink checkpoints/pretrained):ro" \
             -w /work \
             reconeval:latest \
             -n reconeval-state [PYTHON COMMAND]

**Outputs:** ``data/luca/demo/embeddings/SE/grouped.zarr``

Geneformer and UCE take raw counts: the Slurm script first writes
``data/luca/demo/counts.zarr`` from the ``count`` layer of the source h5ad,
with the same groups, cells, and genes as ``expression.zarr``.

For configuration details see
:doc:`Extract embeddings <../foundation_model/extract_embeddings>`.


**Combine expression and embeddings**

Combine expression and embeddings into stores for decoder training and validation.

.. tab-set::

   .. tab-item:: Direct

      .. code-block:: bash

         # Switch back to the reconeval environment
         conda activate reconeval

         # [PYTHON COMMAND]
         ## Combine expression and embeddings
         python experiments/preprocessing/combine_emb_zarr.py \
             --expression-zarr data/luca/demo/expression.zarr \
             --split-meta-zarr data/luca/demo/split_metadata.zarr \
             --embedding-zarr data/luca/demo/embeddings/SE/grouped.zarr \
             --embedding-key SE \
             --out-dir results/luca-demo/fm/SE/emb_combined

   .. tab-item:: Slurm

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/02_foundation_model/submit/combine_embeddings.sbatch

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

**Outputs:** ``results/luca-demo/fm/SE/emb_combined/train.zarr``, ``val.zarr``

For configuration details see
:doc:`Combine expression and embeddings <../foundation_model/combine_embeddings>`.


3. Train MLP decoder
--------------------

Train a one-layer MLP decoder.

.. tab-set::

   .. tab-item:: Direct

      .. code-block:: bash

         # [PYTHON COMMAND]
         ## Train MLP decoder
         python experiments/02_foundation_model/codes/train_decoder_from_embedding.py \
             --emb-train-zarr results/luca-demo/fm/SE/emb_combined/train.zarr \
             --emb-val-zarr results/luca-demo/fm/SE/emb_combined/val.zarr \
             --all-genes-zarr data/luca/demo/expression.zarr \
             --target-genes-zarr data/luca/demo/expression.zarr \
             --embedding-key SE \
             --reshuffle \
             --out results/luca-demo/fm/SE/MLP

   .. tab-item:: Slurm

      The script trains a decoder for each model:

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/02_foundation_model/submit/train.sbatch

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

**Outputs:** decoder checkpoints in ``results/luca-demo/fm/SE/MLP/``

For configuration details see :doc:`Train <../foundation_model/train>`.


4. Reference PCA
----------------

Reuse the reference PCA if available, or follow the
:ref:`end-to-end instructions <end-to-end-reference-pca>` to fit it.


5. Evaluate
-----------

Reconstruct held-out expression and compute distributional metrics.

.. tab-set::

   .. tab-item:: Direct

      Set ``<checkpoint>`` to your decoder checkpoint filename:

      **Distributional metrics**

      .. code-block:: bash

         # [PYTHON COMMAND]
         ## Distributional metrics
         python experiments/02_foundation_model/codes/eval_decoder_statistical.py \
             --config-dir custom_datasets_demo/02_foundation_model/configs \
             --config-name base_eval_decode_demo \
             pretrained=SE \
             decoder=MLP \
             metric=decode_statistical_demo \
             "decoder.load.path='results/luca-demo/fm/SE/MLP/<checkpoint>'" \
             'metric.projector.load.path=[results/luca-demo/reference-pca/mean.zarr,results/luca-demo/reference-pca/pc_50.zarr]' \
             output.save_path=results/luca-demo/fm/SE/distributional.csv

   .. tab-item:: Slurm

      Set the explicit checkpoint path for each model in the script’s
      ``checkpoints`` array, then submit it:

      .. code-block:: bash

         mkdir -p logs
         sbatch custom_datasets_demo/02_foundation_model/submit/evaluate.sbatch

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

**Outputs:** ``results/luca-demo/fm/<model>/distributional.csv``

For configuration details see :doc:`Evaluate <../foundation_model/evaluate>`.


6. Summarize metrics
--------------------

After evaluating all seven models:

.. tab-set::

   .. tab-item:: Direct

      .. code-block:: bash

         # [PYTHON COMMAND]
         python custom_datasets_demo/02_foundation_model/codes/print_metrics.py

   .. tab-item:: Slurm

      After the evaluation job finishes, use the **Direct** tab.

   .. tab-item:: Apptainer

      .. code-block:: bash

         apptainer exec --cleanenv \
             --bind "$PWD:/work" \
             --bind "$(realpath results):$(realpath results)" \
             --pwd /work \
             /path/to/reconeval-all.sif \
             conda run --no-capture-output -n reconeval [PYTHON COMMAND]

   .. tab-item:: Docker

      .. code-block:: bash

         docker run --rm \
             -v "$PWD:/work" \
             -v "$(realpath results):$(realpath results)" \
             -w /work \
             reconeval:latest \
             -n reconeval [PYTHON COMMAND]

**Outputs:** ``results/luca-demo/fm/summary.csv``

Means across test groups. Higher R² and lower other metrics are better.

.. csv-table::
   :file: foundation_model_summary.csv
   :header-rows: 1

Model performance may be limited by the small demo split.


Runtime
-------

Embedding extraction and MLP decoder training time on LuCA subsets:

- **Models:** SE, scGPT, scConcept, and SCimilarity
- **Embedding dimensions:** 2,058 (SE), 512 (scGPT, scConcept), 128 (SCimilarity)
- **Decoder:** 1 hidden layer of 1,024, 2,048, or 4,096 units, up to 500
  epochs with early stopping
- **Data:** 500, 1,000, 10,000, 100,000, and 892,296 cells; 5,983 HVGs
- **Split:** new 70/15/15 train/val/test split by combination per subset,
  not split 03
- **Hardware:** one NVIDIA H100 80GB GPU, 20 CPUs (Intel Xeon Platinum 8480+),
  128 GB RAM
- **Repeats:** 3 per run

.. figure:: /_static/demo/luca_runtime_fm.svg
   :width: 100%

   Mean ± SD over three runs. Left: embedding extraction; other panels:
   decoder training per model and hidden size.

On the full dataset, embedding extraction takes 7 minutes (SCimilarity),
9 minutes (scConcept), 31 minutes (scGPT), and 2.3 hours (SE); decoder
training takes 11-27 minutes.
