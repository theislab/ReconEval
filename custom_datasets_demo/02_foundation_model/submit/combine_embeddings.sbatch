#!/usr/bin/env bash
# Submit from the repository root after extract_embeddings.sbatch completes:
# mkdir -p logs
# sbatch custom_datasets_demo/02_foundation_model/submit/combine_embeddings.sbatch
# Combine grouped embeddings and expression into flat train/val stores.
#SBATCH --job-name=luca-demo-fm-combine
#SBATCH --partition=cpu_p
#SBATCH --qos=cpu_normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/luca-demo-fm-combine-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/41522356/reconeval-all.sif}
data_dir=$(realpath data)

# ---------------------------------------------------------------------------
# Commands to run inside the container
# ---------------------------------------------------------------------------
CMD=$(cat <<'COMMAND'
for model in SE scGPT scConcept scimilarity; do
    python -u experiments/preprocessing/combine_emb_zarr.py \
        --expression-zarr data/luca/demo/expression.zarr \
        --split-meta-zarr data/luca/demo/split_metadata.zarr \
        --embedding-zarr "data/luca/demo/embeddings/$model/grouped.zarr" \
        --embedding-key "$model" \
        --out-dir "results/luca-demo/fm/$model/emb_combined"
done
COMMAND
)

# ---------------------------------------------------------------------------
# Run — mount the repository and preserve the external data path
# ---------------------------------------------------------------------------
mkdir -p results/luca-demo/tmp
apptainer exec --cleanenv \
    --env TMPDIR=/work/results/luca-demo/tmp \
    --bind "$PWD:/work" \
    --bind "$data_dir:$data_dir" \
    --pwd /work \
    "$image" \
    conda run --no-capture-output -n reconeval \
    bash -e -c "$CMD"
