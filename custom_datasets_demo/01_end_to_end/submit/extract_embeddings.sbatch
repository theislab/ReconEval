#!/usr/bin/env bash
# Submit from the repository root:
# mkdir -p logs
# sbatch custom_datasets_demo/01_end_to_end/submit/extract_embeddings.sbatch
# Edit paths, models, and parameters in CMD below.
#SBATCH --job-name=luca-demo-embeddings
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=01:00:00
#SBATCH --output=logs/luca-demo-embeddings-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
## Set the absolute path to your Apptainer image
image=/path/to/reconeval-all.sif

export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"

# ---------------------------------------------------------------------------
# Commands to run inside the container
# ---------------------------------------------------------------------------
CMD=$(cat <<'COMMAND'
mkdir -p "results/luca-demo/embeddings"

## Set <run> to your training-run folder and <checkpoint> to the checkpoint path inside it.
declare -A mlae_checkpoints=(
    [10]='results/luca-demo/mlAE/10/<run>/<checkpoint>'
    [32]='results/luca-demo/mlAE/32/<run>/<checkpoint>'
    [128]='results/luca-demo/mlAE/128/<run>/<checkpoint>'
)
declare -A nlscvi_checkpoints=(
    [10]='results/luca-demo/nlscVI/10/<run>/<checkpoint>'
    [32]='results/luca-demo/nlscVI/32/<run>/<checkpoint>'
    [128]='results/luca-demo/nlscVI/128/<run>/<checkpoint>'
)

for latent in 10 32 128; do
    ## PCA
    python -u experiments/01_end_to_end/codes/extract_e2e_embeddings.py \
        --hvg_zarr data/luca/demo/expression.zarr \
        --model PCA \
        --pca_mean "results/luca-demo/PCA/$latent/mean.zarr" \
        --pca_pc "results/luca-demo/PCA/$latent/pc_$latent.zarr" \
        --out "results/luca-demo/embeddings/PCA/$latent.zarr"

    ## mlAE
    python -u experiments/01_end_to_end/codes/extract_e2e_embeddings.py \
        --hvg_zarr data/luca/demo/expression.zarr \
        --model AE \
        --ckpt "${mlae_checkpoints[$latent]}" \
        --out "results/luca-demo/embeddings/mlAE/$latent.zarr"

    ## nlscVI
    python -u experiments/01_end_to_end/codes/extract_e2e_embeddings.py \
        --hvg_zarr data/luca/demo/expression.zarr \
        --model nlscVI \
        --ckpt "${nlscvi_checkpoints[$latent]}" \
        --out "results/luca-demo/embeddings/nlscVI/$latent.zarr"
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
    --bind "$(realpath results):$(realpath results)" \
    --bind "$(realpath data):$(readlink data)" \
    --pwd /work \
    "$image" \
    conda run --no-capture-output -n reconeval \
    bash -e -c "$CMD"
