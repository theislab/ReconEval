#!/usr/bin/env bash
# Time one LuCA training run; called inside the container by train.sbatch.
# Usage: bash runtime/01_end_to_end/codes/train_runtime.sh TASK_ID
#   task_id = ((model * 5 + cells) * 5 + latent) * 3 + (repeat - 1)

set -euo pipefail
export WANDB_MODE=offline

# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------
task_id=${1:?Pass the Slurm array task ID}
models=(PCA mlAE nlscVI)
cell_counts=(500 1000 10000 100000 full)
latent_dims=(10 32 128 512 2048)

model=${models[$((task_id / 75))]}
n_cells=${cell_counts[$((task_id / 15 % 5))]}
latent_dim=${latent_dims[$((task_id / 3 % 5))]}
repeat=$((task_id % 3 + 1))

data_dir=data/luca/runtime/$n_cells
run_dir=results/luca-runtime/runs/$model/$n_cells/$latent_dim/repeat-$repeat
n_train=$(python -c "import zarr; print(zarr.open('$data_dir/train.zarr', mode='r')['X'].shape[0])")
echo "Task $task_id: $model, $n_cells cells ($n_train train), latent $latent_dim, repeat $repeat"

# ---------------------------------------------------------------------------
# Skip infeasible or finished runs
# ---------------------------------------------------------------------------
if [[ "$model" == PCA ]] && (( latent_dim >= n_train )); then
    echo "Skipping: PCA needs fewer components than training cells"
    exit 0
fi
if grep -qs '"exit_code": 0' "$run_dir/runtime.json"; then
    echo "Already finished: $run_dir"
    exit 0
fi
rm -rf "$run_dir"
mkdir -p "$run_dir"

# ---------------------------------------------------------------------------
# Hydra overrides
# ---------------------------------------------------------------------------
common=(
    --config-dir runtime/01_end_to_end/configs
    data=luca_runtime
    data.path="$data_dir"
    seed=42
    weights.dir="$run_dir/weights"
    logging.dir="$run_dir/logs"
    hydra.run.dir="$run_dir/hydra"
)

case "$model" in
PCA)
    args=(
        model=train/PCA
        trainer=PCA
        '+trainer.gpu_ids=${oc.env:CUDA_VISIBLE_DEVICES}'
        trainer.temp_dir="$run_dir/pca-work"
        model.model_args.n_components="$latent_dim"
    )
    ;;
mlAE)
    args=(
        model=train/AE
        trainer=AE
        trainer.accelerator=gpu
        +trainer.enable_progress_bar=false
        model.meta.name=mlAE
        model.model_args.library_size_mode=modeled
        'model.model_args.n_hidden=[1024]'
        model.model_args.n_latent="$latent_dim"
    )
    ;;
nlscVI)
    args=(
        model=train/nlscVI
        trainer=scVI
        trainer.accelerator=gpu
        +trainer.enable_progress_bar=false
        model.model_args.n_hidden=1024
        model.model_args.n_layers=1
        model.model_args.n_latent="$latent_dim"
    )
    ;;
esac

# ---------------------------------------------------------------------------
# Train and record wall time
# ---------------------------------------------------------------------------
start=$(date +%s.%N)
exit_code=0
python -u experiments/01_end_to_end/codes/train.py "${common[@]}" "${args[@]}" \
    > "$run_dir/train.log" 2>&1 || exit_code=$?
end=$(date +%s.%N)

gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
cat > "$run_dir/runtime.json" <<JSON
{"model": "$model", "n_cells": "$n_cells", "n_train": $n_train, "latent_dim": $latent_dim, "repeat": $repeat, "start": $start, "end": $end, "exit_code": $exit_code, "gpu": "$gpu", "host": "$(hostname)", "slurm_job": "${SLURM_ARRAY_JOB_ID:-}_${SLURM_ARRAY_TASK_ID:-}"}
JSON
cat "$run_dir/runtime.json"
exit "$exit_code"
