#!/usr/bin/env bash
# Submit from the repository root:
# mkdir -p logs/runtime
# sbatch runtime/01_end_to_end/submit/prepare_dataset.sbatch
# Prepare datasets for both end-to-end and FM runtime; include raw counts for FMs.
# 15 array tasks = 5 cell counts x 3 timing repeats, all with seed 42:
#   task_id = cells * 3 + (repeat - 1)
# Cell counts: random 500, 1000, 10000, 100000 and all (892296) LuCA cells,
# each with the 5983 precomputed HVGs.
# Repeat 1 is kept in data/luca/runtime/<n_cells> and used for training.
# Repeats 2-3 only measure timing noise: they are written next to repeat 1
# (same filesystem) and deleted afterwards. Timed repeats are skipped.
# Wall times of both steps (including container startup) are written to
# results/luca-runtime/prep/<n_cells>/repeat-<r>.json. Runs on the same H100
# nodes (Xeon Platinum 8480+) as training; the preprocessing itself is CPU-only.
#SBATCH --job-name=luca-runtime-prep
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=20
#SBATCH --mem=128G
#SBATCH --time=04:00:00
#SBATCH --array=0-14
#SBATCH --output=logs/runtime/luca-runtime-prep-%A_%a.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/43406461/reconeval-all.sif}
cell_counts=(500 1000 10000 100000 full)
n_cells=${cell_counts[$((SLURM_ARRAY_TASK_ID / 3))]}
repeat=$((SLURM_ARRAY_TASK_ID % 3 + 1))
input_file=data/luca/core_250130.h5ad
if (( repeat == 1 )); then
    output_dir=data/luca/runtime/$n_cells
else
    output_dir=data/luca/runtime/$n_cells.repeat-$repeat
fi
timing_file=results/luca-runtime/prep/$n_cells/repeat-$repeat.json

if [[ -f "$timing_file" ]]; then
    echo "Already timed: $timing_file"
    exit 0
elif [[ -e "$output_dir" || -L "$output_dir" ]]; then
    echo "Incomplete dataset, remove it and resubmit: $output_dir" >&2
    exit 1
fi
mkdir -p "$output_dir"

if [[ "$n_cells" == full ]]; then
    subsample=(demo=false)
else
    subsample=(demo=true demo_cells="$n_cells" demo_genes=null)
fi

echo "LuCA runtime subset: $n_cells cells x 5983 precomputed HVGs, repeat $repeat"
echo "Input: $input_file"
echo "Output: $output_dir"

# ---------------------------------------------------------------------------
# Run — mount the repository and preserve the external data path
# ---------------------------------------------------------------------------
task_tmp="results/luca-runtime/tmp/prep_${SLURM_ARRAY_JOB_ID:?}_${SLURM_ARRAY_TASK_ID}"
mkdir -p "$task_tmp"
run() {
    apptainer exec --cleanenv \
        --env TMPDIR="/work/$task_tmp" \
        --env PYTHONPATH=/work/src \
        --bind "$PWD:/work" \
        --bind "$(realpath results):$(realpath results)" \
        --bind "$(realpath data):$(readlink data)" \
        --pwd /work \
        "$image" \
        conda run --no-capture-output -n reconeval "$@"
}

start=$(date +%s.%N)
run python -u experiments/preprocessing/prepare_dataset.py \
    --config-name data/luca \
    utils=experiments/preprocessing/utils/luca.py \
    input="$input_file" \
    output="$output_dir" \
    "${subsample[@]}" \
    seed=42 \
    split.strategy=combination \
    split.path=null \
    +save_counts=true \
    hydra.run.dir="$output_dir/logs" \
    hydra.job.chdir=false
prepared=$(date +%s.%N)

# PCA trains on the same training cells as the neural models.
run python -u experiments/preprocessing/zarr_to_h5ad.py "$output_dir/train.zarr"
test -f "$output_dir/train.h5ad"
end=$(date +%s.%N)

# ---------------------------------------------------------------------------
# Record timing; drop the extra copies
# ---------------------------------------------------------------------------
mkdir -p "$(dirname "$timing_file")"
cat > "$timing_file" <<JSON
{"n_cells": "$n_cells", "repeat": $repeat, "start": $start, "prepared": $prepared, "end": $end, "cpu": "$(lscpu | sed -n 's/^Model name: *//p')", "n_cpus": $SLURM_CPUS_PER_TASK, "host": "$(hostname)", "slurm_job": "${SLURM_ARRAY_JOB_ID}_${SLURM_ARRAY_TASK_ID}"}
JSON
cat "$timing_file"

if (( repeat > 1 )); then
    rm -rf "$output_dir"
fi
