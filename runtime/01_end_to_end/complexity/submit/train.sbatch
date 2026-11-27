#!/usr/bin/env bash
# Submit from the repository root:
# mkdir -p logs/runtime_complexity
# sbatch runtime/01_end_to_end/complexity/submit/train.sbatch
# Fixed latent 2048: 2 models x 9 architectures x 3 repeats = 54 runs.
# Task IDs 0-41 cover the 42 non-reused entries; 12 entries are reused.
# Historical task mapping; successful completed tasks are skipped.
# Time train.py including imports, data loading, fitting, validation and
# checkpointing; exclude container startup and queueing, as in runtime/.
#SBATCH --job-name=luca-complexity
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=20
#SBATCH --mem=128G
#SBATCH --time=04:00:00
#SBATCH --array=0-41
#SBATCH --output=logs/runtime_complexity/luca-complexity-%A_%a.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/42016471/reconeval-all.sif}
benchmark=${RECONEVAL_BENCHMARK_DIR:-runtime/01_end_to_end/complexity/fixed_latent_2048}
task_tmp="results/luca-runtime-complexity/tmp/${SLURM_ARRAY_JOB_ID:?}_${SLURM_ARRAY_TASK_ID:?}"
mkdir -p "$task_tmp"
export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"

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
    python runtime/01_end_to_end/complexity/codes/train_runtime.py "$SLURM_ARRAY_TASK_ID" \
    --benchmark-dir "$benchmark"
