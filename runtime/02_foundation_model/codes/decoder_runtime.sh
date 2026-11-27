#!/usr/bin/env bash
# Time one LuCA MLP decoder run; called inside the container by decoder.sbatch.
# Usage: bash runtime/02_foundation_model/codes/decoder_runtime.sh TASK_ID
# Explicit architecture: --run MODEL CELLS LAYERS HIDDEN REPEAT RUN_DIR [--dry-run]
# Add --dry-run after TASK_ID to preview the original runtime task as well.
#   task_id = ((model * 5 + cells) * 3 + hidden) * 3 + (repeat - 1)
#   hidden in (1024 2048 4096), one hidden layer
# Trains on the repeat-1 stores of embed_runtime.sh: up to 500 epochs with early
# stopping (patience 10), reshuffled every epoch, 16 loader workers, seed 42.

set -euo pipefail
export WANDB_MODE=offline

# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------
explicit_run=false
if [[ ${1:-} == --run ]]; then
    if (( $# < 7 || $# > 8 )); then
        echo 'Usage: --run MODEL CELLS LAYERS HIDDEN REPEAT RUN_DIR [--dry-run]' >&2
        exit 2
    fi
    explicit_run=true
    model=$2
    n_cells=$3
    n_layers=$4
    n_hidden=$5
    repeat=$6
    run_dir=$7
    preview=${8:-}
else
    task_id=${1:?Pass the Slurm array task ID}
    models=(SE scGPT scConcept scimilarity UCE Geneformer scFoundation)
    cell_counts=(500 1000 10000 100000 full)
    hidden_sizes=(1024 2048 4096)
    model=${models[$((task_id / 45))]}
    n_cells=${cell_counts[$((task_id / 9 % 5))]}
    n_layers=1
    n_hidden=${hidden_sizes[$((task_id / 3 % 3))]}
    repeat=$((task_id % 3 + 1))
    run_dir=results/luca-runtime-fm/decoder/$model/$n_cells/${n_layers}x$n_hidden/repeat-$repeat
    preview=${2:-}
fi
if [[ -n "$preview" && "$preview" != --dry-run ]]; then
    echo "Unknown argument: $preview" >&2
    exit 2
fi

data_dir=data/luca/runtime/$n_cells
embed_dir=results/luca-runtime-fm/embed/$model/$n_cells/repeat-1
command=(conda run --no-capture-output -n reconeval
    python -u experiments/02_foundation_model/codes/train_decoder_from_embedding.py
    --emb-train-zarr "$embed_dir/emb_combined/train.zarr"
    --emb-val-zarr "$embed_dir/emb_combined/val.zarr"
    --all-genes-zarr "$data_dir/expression.zarr"
    --target-genes-zarr "$data_dir/expression.zarr"
    --embedding-key "$model" --n-layers "$n_layers" --hidden "$n_hidden"
    --reshuffle --seed 42 --out "$run_dir/MLP")
if [[ "$preview" == --dry-run ]]; then
    printf '%q ' "${command[@]}"
    printf '\n'
    exit 0
fi
n_train=$(conda run -n reconeval python -c "import zarr; print(zarr.open('$data_dir/train.zarr', mode='r')['X'].shape[0])")
echo "$model, $n_cells cells ($n_train train), decoder ${n_layers}x$n_hidden, repeat $repeat"

# ---------------------------------------------------------------------------
# Skip finished runs; require the embedding run
# ---------------------------------------------------------------------------
if grep -qs '"exit_code": 0' "$run_dir/runtime.json"; then
    echo "Already finished: $run_dir"
    exit 0
fi
if ! grep -qs '"exit_code": 0' "$embed_dir/runtime.json"; then
    echo "Embedding run missing or failed, run embed.sbatch first: $embed_dir" >&2
    exit 1
fi
if [[ "$explicit_run" == true && ( -e "$run_dir" || -L "$run_dir" ) ]]; then
    echo "Existing unfinished run: $run_dir. Move it aside before retrying." >&2
    exit 1
fi
rm -rf "$run_dir"
mkdir -p "$run_dir"

# ---------------------------------------------------------------------------
# Train and record wall time
# ---------------------------------------------------------------------------
start=$(date +%s.%N)
exit_code=0
"${command[@]}" \
    2>&1 | awk -F'\r' '{ print $NF; fflush() }' > "$run_dir/decoder.log" || exit_code=$?
end=$(date +%s.%N)

# Lightning's stopped_epoch is 0-based; runs without early stopping use all 500.
stopped=$(sed -n 's/^\[done\] early stopped at epoch //p' "$run_dir/decoder.log")
epochs=$(( exit_code == 0 ? (${stopped:-499} + 1) : 0 ))

# Only the timing matters; checkpoints of the large decoders take ~1 GB each.
rm -f "$run_dir"/MLP/*.ckpt

gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
cat > "$run_dir/runtime.json" <<JSON
{"model": "$model", "n_cells": "$n_cells", "n_train": $n_train, "n_layers": $n_layers, "n_hidden": $n_hidden, "repeat": $repeat, "start": $start, "end": $end, "epochs": $epochs, "exit_code": $exit_code, "gpu": "$gpu", "host": "$(hostname)", "image": "${RECONEVAL_IMAGE:-unknown}", "slurm_job": "${SLURM_ARRAY_JOB_ID:-}_${SLURM_ARRAY_TASK_ID:-}"}
JSON
cat "$run_dir/runtime.json"
exit "$exit_code"
