#!/usr/bin/env bash
# Submit from the repository root:
# mkdir -p logs
# sbatch custom_datasets_demo/01_end_to_end/submit/evaluate.sbatch
# Edit paths, metrics, and parameters in CMD below.
#SBATCH --job-name=luca-demo-eval
#SBATCH --partition=cpu_p
#SBATCH --qos=cpu_normal
#SBATCH --cpus-per-task=18
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=logs/luca-demo-eval-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/41522356/reconeval-all.sif}

# ---------------------------------------------------------------------------
# Commands to run inside the container
# ---------------------------------------------------------------------------
CMD=$(cat <<'COMMAND'
mkdir -p "results/luca-demo"

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

## Distributional metrics (R2, MSE, MMD, energy distance)
for latent in 10 32 128; do

    ## PCA
    python -u experiments/01_end_to_end/codes/eval_distributional.py \
        --config-dir custom_datasets_demo/01_end_to_end/configs \
        --config-name base_eval_demo \
        model=eval/PCA \
        metric=_distributional \
        "metric.projector.load.path=[results/luca-demo/reference-pca/mean.zarr,results/luca-demo/reference-pca/pc_50.zarr]" \
        "model.load.path=[results/luca-demo/PCA/$latent/mean.zarr,results/luca-demo/PCA/$latent/pc_${latent}.zarr]" \
        "model.load.model_name=pc_$latent" \
        "output.save_path=results/luca-demo/PCA/$latent/distributional.csv"

    ## mlAE
    python -u experiments/01_end_to_end/codes/eval_distributional.py \
        --config-dir custom_datasets_demo/01_end_to_end/configs \
        --config-name base_eval_demo \
        model=eval/AE \
        model.meta.name=mlAE \
        metric=_distributional \
        "metric.projector.load.path=[results/luca-demo/reference-pca/mean.zarr,results/luca-demo/reference-pca/pc_50.zarr]" \
        "model.load.path='${mlae_checkpoints[$latent]}'" \
        "model.load.model_name='100_[1024]_${latent}_20261024'" \
        "output.save_path=results/luca-demo/mlAE/$latent/distributional.csv"

    ## nlscVI
    python -u experiments/01_end_to_end/codes/eval_distributional.py \
        --config-dir custom_datasets_demo/01_end_to_end/configs \
        --config-name base_eval_demo \
        model=eval/nlscVI \
        metric=_distributional \
        "metric.projector.load.path=[results/luca-demo/reference-pca/mean.zarr,results/luca-demo/reference-pca/pc_50.zarr]" \
        "model.load.path='${nlscvi_checkpoints[$latent]}'" \
        "model.load.model_name='100_1024_${latent}_1_0.1_20261024'" \
        "output.save_path=results/luca-demo/nlscVI/$latent/distributional.csv"
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
    --bind "$(realpath data):$(readlink data)" \
    --bind "$(realpath ~/.cache):$(readlink ~/.cache)" \
    --pwd /work \
    "$image" \
    conda run --no-capture-output -n reconeval \
    bash -e -c "$CMD"
