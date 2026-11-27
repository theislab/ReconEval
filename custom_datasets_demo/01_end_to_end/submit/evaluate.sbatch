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
## Set the absolute path to your Apptainer image
image=/path/to/reconeval-all.sif

# ---------------------------------------------------------------------------
# Commands to run inside the container
# ---------------------------------------------------------------------------
CMD=$(cat <<'COMMAND'
mkdir -p "results/luca-demo"

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
        "model.load.model_name=mlAE_$latent" \
        "output.save_path=results/luca-demo/mlAE/$latent/distributional.csv"

    ## nlscVI
    python -u experiments/01_end_to_end/codes/eval_distributional.py \
        --config-dir custom_datasets_demo/01_end_to_end/configs \
        --config-name base_eval_demo \
        model=eval/nlscVI \
        metric=_distributional \
        "metric.projector.load.path=[results/luca-demo/reference-pca/mean.zarr,results/luca-demo/reference-pca/pc_50.zarr]" \
        "model.load.path='${nlscvi_checkpoints[$latent]}'" \
        "model.load.model_name=nlscVI_$latent" \
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
    --bind "$(realpath results):$(realpath results)" \
    --bind "$(realpath data):$(readlink data)" \
    --pwd /work \
    "$image" \
    conda run --no-capture-output -n reconeval \
    bash -e -c "$CMD"
