#!/usr/bin/env bash
# Submit from the repository root after combine_embeddings.sbatch completes:
# mkdir -p logs
# sbatch custom_datasets_demo/02_foundation_model/submit/train.sbatch
# Edit CMD below to choose decoder parameters.
#SBATCH --job-name=luca-demo-fm-train
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/luca-demo-fm-train-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/41522356/reconeval-all.sif}
data_dir=$(realpath data)

export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"

# ---------------------------------------------------------------------------
# Commands to run inside the container
# ---------------------------------------------------------------------------
CMD=$(cat <<'COMMAND'
for model in SE scGPT scConcept scimilarity; do
    ## Train the MLP decoder
    python -u experiments/02_foundation_model/codes/train_decoder_from_embedding.py \
        --emb-train-zarr "results/luca-demo/fm/$model/emb_combined/train.zarr" \
        --emb-val-zarr "results/luca-demo/fm/$model/emb_combined/val.zarr" \
        --all-genes-zarr data/luca/demo/expression.zarr \
        --target-genes-zarr data/luca/demo/expression.zarr \
        --embedding-key "$model" \
        --num-workers 8 \
        --out "results/luca-demo/fm/$model/MLP"
done
COMMAND
)

# ---------------------------------------------------------------------------
# Run — mount the repository and preserve the external data path
# ---------------------------------------------------------------------------
mkdir -p results/luca-demo/tmp
apptainer exec --cleanenv --nv \
    --env TMPDIR=/work/results/luca-demo/tmp \
    --bind "$PWD:/work" \
    --bind "$data_dir:$data_dir" \
    --pwd /work \
    "$image" \
    conda run --no-capture-output -n reconeval \
    bash -e -c "$CMD"
