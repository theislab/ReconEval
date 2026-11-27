#!/usr/bin/env bash
# Time one LuCA foundation-model embedding run; called inside the container by embed.sbatch.
# Each step uses its own conda env, since the FM packages conflict.
# Usage: bash runtime/02_foundation_model/codes/embed_runtime.sh TASK_ID
#   task_id = (model * 5 + cells) * 3 + (repeat - 1)
# Two timed steps, each in its own process:
#   embed   - frozen FM embeds all cells (train, val, test)
#   combine - flat train/val stores with expression + embedding
# Repeat 1 keeps its stores for decoder_runtime.sh. Repeats 2-3 measure
# runtime variation and delete their stores.

set -euo pipefail
export WANDB_MODE=offline

# ---------------------------------------------------------------------------
# Grid
# ---------------------------------------------------------------------------
task_id=${1:?Pass the Slurm array task ID}
models=(SE scGPT scConcept scimilarity UCE Geneformer scFoundation)
cell_counts=(500 1000 10000 100000 full)

model=${models[$((task_id / 15))]}
n_cells=${cell_counts[$((task_id / 3 % 5))]}
repeat=$((task_id % 3 + 1))

data_dir=data/luca/runtime/$n_cells
run_dir=results/luca-runtime-fm/embed/$model/$n_cells/repeat-$repeat
pretrained=checkpoints/pretrained
n_train=$(conda run -n reconeval python -c "import zarr; print(zarr.open('$data_dir/train.zarr', mode='r')['X'].shape[0])")
echo "Task $task_id: $model, $n_cells cells ($n_train train), repeat $repeat"

# ---------------------------------------------------------------------------
# Skip finished runs
# ---------------------------------------------------------------------------
if grep -qs '"exit_code": 0' "$run_dir/runtime.json"; then
    echo "Already finished: $run_dir"
    exit 0
fi
counts_dir=$data_dir/counts.zarr
if [[ "$model" == UCE || "$model" == Geneformer ]]; then
    if [[ ! -d "$counts_dir" ]]; then
        echo "Raw counts missing: use runtime/01_end_to_end/submit/prepare_dataset.sbatch ($counts_dir)" >&2
        exit 1
    fi
fi
rm -rf "$run_dir"
mkdir -p "$run_dir"

# Gene-ID metadata belongs to the FM run; prepared datasets stay read-only.
# This step is outside the embedding timing, like dataset preparation.
gene_ids_dir=$run_dir/gene_ids.zarr
if [[ "$model" == scConcept || "$model" == Geneformer ]]; then
    conda run --no-capture-output -n reconeval \
        python -u runtime/02_foundation_model/codes/write_gene_ids.py \
        --expression-zarr "$data_dir/expression.zarr" \
        --source-h5ad data/luca/core_250130.h5ad \
        --out "$gene_ids_dir"
fi

# Keep the last state of each progress-bar line so logs stay small.
logged() {
    local name=$1
    shift
    "$@" 2>&1 | awk -F'\r' '{ print $NF; fflush() }' > "$run_dir/$name.log"
}

# ---------------------------------------------------------------------------
# Steps
# ---------------------------------------------------------------------------
embed() {
    local common=(
        data_args.comb_meta_root="$data_dir/expression.zarr"
        data_args.split_meta_root="$data_dir/split_metadata.zarr"
        data_args.target_key=null
        data_args.output_dir="$run_dir/embeddings.zarr"
        parts=1
        total_parts=1
        hydra.run.dir="$run_dir/hydra"
    )
    case "$model" in
    SE)
        logged embed conda run --no-capture-output -n reconeval-state \
            python -u experiments/02_foundation_model/codes/SE_emb.py "${common[@]}" \
            model_args.checkpoint_path="$pretrained/SE/se600m_epoch16.ckpt" \
            model_args.protein_embeds_path="$pretrained/SE/protein_embeddings.pt"
        ;;
    scGPT)
        logged embed conda run --no-capture-output -n reconeval-scgpt \
            python -u experiments/02_foundation_model/codes/scGPT_emb.py "${common[@]}" \
            model_args.checkpoint_path="$pretrained/scGPT" \
            data_args.var_names_path="$data_dir/expression.zarr" \
            data_args.var_names_key=var_names \
            +model_args.gene_col=gene_name
        ;;
    scConcept)
        logged embed conda run --no-capture-output -n reconeval-scconcept \
            python -u experiments/02_foundation_model/codes/scConcept_emb.py "${common[@]}" \
            model_args.checkpoint_path="$pretrained/scConcept/Corpus-30M" \
            data_args.var_names_path="$gene_ids_dir" \
            data_args.var_names_key=var_ensembl_ids_38
        ;;
    scimilarity)
        logged embed conda run --no-capture-output -n reconeval-scimilarity \
            python -u experiments/02_foundation_model/codes/scimilarity_emb.py "${common[@]}" \
            model_args.checkpoint_path="$pretrained/scimilarity/model_v1.1" \
            data_args.var_names_path="$data_dir/expression.zarr" \
            data_args.var_names_key=var_names
        ;;
    UCE)
        logged embed conda run --no-capture-output -n reconeval-uce \
            python -u experiments/02_foundation_model/codes/UCE_emb.py "${common[@]}" \
            model_args.checkpoint_path="$pretrained/UCE" \
            data_args.comb_meta_root="$counts_dir" \
            data_args.var_names_path="$counts_dir" \
            data_args.var_names_key=var_names
        ;;
    Geneformer)
        logged embed conda run --no-capture-output -n reconeval-geneformer \
            python -u experiments/02_foundation_model/codes/Geneformer_emb.py "${common[@]}" \
            model_args.checkpoint_path="$pretrained/Geneformer/Geneformer-V2-316M" \
            data_args.comb_meta_root="$counts_dir" \
            data_args.var_names_path="$gene_ids_dir" \
            data_args.var_names_key=var_ensembl_ids_38
        ;;
    scFoundation)
        logged embed conda run --no-capture-output -n reconeval-scfoundation \
            python -u experiments/02_foundation_model/codes/scFoundation_emb.py "${common[@]}" \
            model_args.checkpoint_path="$pretrained/scFoundation" \
            data_args.var_names_path="$data_dir/expression.zarr" \
            data_args.var_names_key=var_names
        ;;
    esac
}

combine() {
    logged combine conda run --no-capture-output -n reconeval \
        python -u experiments/preprocessing/combine_emb_zarr.py \
        --expression-zarr "$data_dir/expression.zarr" \
        --split-meta-zarr "$data_dir/split_metadata.zarr" \
        --embedding-zarr "$run_dir/embeddings.zarr" \
        --embedding-key "$model" \
        --out-dir "$run_dir/emb_combined"
}

# ---------------------------------------------------------------------------
# Run and record wall times (a failed step skips the remaining one)
# ---------------------------------------------------------------------------
exit_code=0
failed_step=null
start=$(date +%s.%N)
embed || { exit_code=$?; failed_step='"embed"'; }
embedded=$(date +%s.%N)
if (( exit_code == 0 )); then
    combine || { exit_code=$?; failed_step='"combine"'; }
fi
end=$(date +%s.%N)

if (( repeat > 1 )); then
    rm -rf "$run_dir/embeddings.zarr" "$run_dir/emb_combined"
fi

gpu=$(nvidia-smi --query-gpu=name --format=csv,noheader | head -n 1)
cat > "$run_dir/runtime.json" <<JSON
{"model": "$model", "n_cells": "$n_cells", "n_train": $n_train, "repeat": $repeat, "start": $start, "embedded": $embedded, "end": $end, "exit_code": $exit_code, "failed_step": $failed_step, "gpu": "$gpu", "host": "$(hostname)", "image": "${RECONEVAL_IMAGE:-unknown}", "slurm_job": "${SLURM_ARRAY_JOB_ID:-}_${SLURM_ARRAY_TASK_ID:-}"}
JSON
cat "$run_dir/runtime.json"
exit "$exit_code"
