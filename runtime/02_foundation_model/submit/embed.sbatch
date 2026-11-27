#!/usr/bin/env bash
# Submit after runtime/01_end_to_end/submit/prepare_dataset.sbatch prepared
# data/luca/runtime/<n_cells>, including counts. Gene IDs are written per FM run.
# The datasets are only read here, using the same FM inputs as custom_datasets_demo.
# See ../README.md for submitting only the three added models.
# Submit decoder.sbatch after this array:
# mkdir -p logs/runtime
# jid=$(sbatch --parsable runtime/02_foundation_model/submit/embed.sbatch)
# sbatch --dependency=afterany:$jid runtime/02_foundation_model/submit/decoder.sbatch
# 105 array tasks = 7 FMs x 5 cell counts
# x 3 repeats; see codes/embed_runtime.sh for the task mapping and commands.
# Successful runs are skipped on resubmission; failed runs start from scratch.
# Timed per step: FM embedding, combining. Not timed: container startup and
# Slurm queueing.
#SBATCH --job-name=luca-runtime-fm-embed
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=20
#SBATCH --mem=128G
#SBATCH --time=24:00:00
#SBATCH --array=0-104
#SBATCH --output=logs/runtime/luca-runtime-fm-embed-%A_%a.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/43406461/reconeval-all.sif}
task_tmp="results/luca-runtime-fm/tmp/embed_${SLURM_ARRAY_JOB_ID:?}_${SLURM_ARRAY_TASK_ID:?}"
mkdir -p "$task_tmp"

export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"

# ---------------------------------------------------------------------------
# Run — mount the repository, checkpoints and the external data path
# ---------------------------------------------------------------------------
apptainer exec --cleanenv --nv \
    --env TMPDIR="/work/$task_tmp" \
    --env PYTHONPATH=/work/src \
    --env RECONEVAL_IMAGE="$image" \
    --env SLURM_ARRAY_JOB_ID="$SLURM_ARRAY_JOB_ID" \
    --env SLURM_ARRAY_TASK_ID="$SLURM_ARRAY_TASK_ID" \
    --env OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" \
    --bind "$PWD:/work" \
    --bind "$(realpath results):$(realpath results)" \
    --bind "$(realpath data):$(readlink data):ro" \
    --bind "$(realpath checkpoints/pretrained):$(readlink checkpoints/pretrained)" \
    --pwd /work \
    "$image" \
    bash runtime/02_foundation_model/codes/embed_runtime.sh "$SLURM_ARRAY_TASK_ID"
