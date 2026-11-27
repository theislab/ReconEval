#!/usr/bin/env bash
# Full-LuCA SE decoder grid: hidden width x depth
# Hidden widths 1024, 2048, 4096 x depths 1, 2, 4; three repeats each.
# Tasks 0-2, 9-11 and 18-20 reuse runtime runs; submit only the 18 new tasks.
#SBATCH --job-name=luca-se-decoder-complexity
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=20
#SBATCH --mem=128G
#SBATCH --time=24:00:00
#SBATCH --array=3-8,12-17,21-26
#SBATCH --output=logs/runtime_complexity/luca-se-decoder-%A_%a.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

hidden_sizes=(1024 1024 1024 2048 2048 2048 4096 4096 4096)
depths=(1 2 4 1 2 4 1 2 4)
task_id=${SLURM_ARRAY_TASK_ID:?}
if (( task_id < 0 || task_id >= 27 )); then
    echo "Task ID must be in 0-26: $task_id" >&2
    exit 2
fi
setting=$((task_id / 3))
repeat=$((task_id % 3 + 1))
hidden=${hidden_sizes[$setting]}
depth=${depths[$setting]}
if (( depth == 1 )); then
    run_dir="results/luca-runtime-fm/decoder/SE/full/${depth}x$hidden/repeat-$repeat"
else
    run_dir="results/luca-runtime-complexity/decoder/SE/full/${depth}x$hidden/repeat-$repeat"
fi
args=(--run SE full "$depth" "$hidden" "$repeat" "$run_dir")
if [[ ${1:-} == --dry-run ]]; then
    bash runtime/02_foundation_model/codes/decoder_runtime.sh "${args[@]}" --dry-run
    exit 0
fi

image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/43406461/reconeval-all.sif}
task_tmp="results/luca-runtime-complexity/tmp/se_decoder_${SLURM_ARRAY_JOB_ID:?}_$task_id"
mkdir -p "$task_tmp"
export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"

apptainer exec --cleanenv --nv \
    --env TMPDIR="/work/$task_tmp" \
    --env PYTHONPATH=/work/src \
    --env RECONEVAL_IMAGE="$image" \
    --env SLURM_ARRAY_JOB_ID="$SLURM_ARRAY_JOB_ID" \
    --env SLURM_ARRAY_TASK_ID="$task_id" \
    --env OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" \
    --bind "$PWD:/work" \
    --bind "$(realpath results):$(realpath results)" \
    --bind "$(realpath data):$(readlink data):ro" \
    --pwd /work "$image" \
    bash runtime/02_foundation_model/codes/decoder_runtime.sh "${args[@]}"
