#!/usr/bin/env bash
# Submit from the repository root after embed.sbatch (see there for the
# dependency); each task needs the repeat-1 embedding run of its FM and cell count:
# sbatch runtime/02_foundation_model/submit/decoder.sbatch
# 315 array tasks = 7 FMs x 5 cell counts x 3 decoder sizes (1 layer x
# 1024/2048/4096 hidden) x 3 repeats; see codes/decoder_runtime.sh for the
# task mapping and command.
# Successful runs are skipped on resubmission; failed runs start from scratch.
# Timed: MLP decoder training. Not timed: container startup and Slurm queueing.
#SBATCH --job-name=luca-runtime-fm-decoder
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=20
#SBATCH --mem=128G
#SBATCH --time=24:00:00
#SBATCH --array=0-314
#SBATCH --output=logs/runtime/luca-runtime-fm-decoder-%A_%a.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/43406461/reconeval-all.sif}
task_tmp="results/luca-runtime-fm/tmp/decoder_${SLURM_ARRAY_JOB_ID:?}_${SLURM_ARRAY_TASK_ID:?}"
mkdir -p "$task_tmp"

export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"

# ---------------------------------------------------------------------------
# Run — mount the repository and the external data path
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
    --pwd /work \
    "$image" \
    bash runtime/02_foundation_model/codes/decoder_runtime.sh "$SLURM_ARRAY_TASK_ID"
