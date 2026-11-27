#!/usr/bin/env bash
# Submit from the repository root after prepare_dataset.sbatch completes:
# mkdir -p logs/runtime
# sbatch runtime/01_end_to_end/submit/train.sbatch
# 225 array tasks = 3 models x 5 cell counts x 5 latent dimensions x 3 repeats;
# see codes/train_runtime.sh for the task mapping and the training commands.
# PCA tasks with latent >= training cells are skipped. Successful runs are
# skipped on resubmission; failed runs are retrained from scratch.
# Timed: the train.py process (imports, data loading, fitting, validation,
# checkpointing). Not timed: container startup and Slurm queueing.
#SBATCH --job-name=luca-runtime-train
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=20
#SBATCH --mem=128G
#SBATCH --time=04:00:00
#SBATCH --array=0-224
#SBATCH --output=logs/runtime/luca-runtime-train-%A_%a.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/42016471/reconeval-all.sif}
task_tmp="results/luca-runtime/tmp/${SLURM_ARRAY_JOB_ID:?}_${SLURM_ARRAY_TASK_ID:?}"
mkdir -p "$task_tmp"

export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"

# ---------------------------------------------------------------------------
# Run — mount the repository and preserve the external data path
# ---------------------------------------------------------------------------
apptainer exec --cleanenv --nv \
    --env TMPDIR="/work/$task_tmp" \
    --env SLURM_ARRAY_JOB_ID="$SLURM_ARRAY_JOB_ID" \
    --env SLURM_ARRAY_TASK_ID="$SLURM_ARRAY_TASK_ID" \
    --env OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" \
    --bind "$PWD:/work" \
    --bind "$(realpath results):$(realpath results)" \
    --bind "$(realpath data):$(readlink data):ro" \
    --pwd /work \
    "$image" \
    conda run --no-capture-output -n reconeval \
    bash runtime/01_end_to_end/codes/train_runtime.sh "$SLURM_ARRAY_TASK_ID"
