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
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/41522356/reconeval-all.sif}

export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"

# ---------------------------------------------------------------------------
# Commands to run inside the container
# ---------------------------------------------------------------------------
CMD=$(cat <<'COMMAND'
mkdir -p "results/luca-demo/embeddings"

# Best saved checkpoint for each latent dimension.
declare -A mlae_checkpoints=(
    [10]='results/luca-demo/mlAE/10/100_[1024]_10_20261024/epoch=60-val/loss_epoch=0.2118.ckpt'
    [32]='results/luca-demo/mlAE/32/100_[1024]_32_20261024/epoch=99-val/loss_epoch=0.1323.ckpt'
    [128]='results/luca-demo/mlAE/128/100_[1024]_128_20261024/epoch=21-val/loss_epoch=0.2196.ckpt'
)
declare -A nlscvi_checkpoints=(
    [10]='results/luca-demo/nlscVI/10/100_1024_10_1_0.1_20261024/2026-10-24_16-14-54_reconstruction_loss_validation/epoch=29-step=60-reconstruction_loss_validation=699.6322631835938.pt'
    [32]='results/luca-demo/nlscVI/32/100_1024_32_1_0.1_20261024/2026-10-24_16-15-43_reconstruction_loss_validation/epoch=22-step=46-reconstruction_loss_validation=719.306884765625.pt'
    [128]='results/luca-demo/nlscVI/128/100_1024_128_1_0.1_20261024/2026-10-24_16-16-30_reconstruction_loss_validation/epoch=25-step=52-reconstruction_loss_validation=728.876708984375.pt'
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
    --bind "$(realpath data):$(readlink data)" \
    --pwd /work \
    "$image" \
    conda run --no-capture-output -n reconeval \
    bash -e -c "$CMD"
