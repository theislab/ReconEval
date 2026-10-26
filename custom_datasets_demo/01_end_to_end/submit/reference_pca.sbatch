#!/usr/bin/env bash
# Submit from the repository root after converting expression.zarr to expression.h5ad:
# mkdir -p logs
# sbatch custom_datasets_demo/01_end_to_end/submit/reference_pca.sbatch
# Edit CMD below to choose the reference PCA parameters.
# Fit the reference PCA on all demo expression data.
#SBATCH --job-name=luca-demo-reference-pca
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=20
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/luca-demo-reference-pca-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/41522356/reconeval-all.sif}
output_dir=results/luca-demo/reference-pca
mkdir -p "$output_dir/logs"

export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"

# ---------------------------------------------------------------------------
# Commands to run inside the container
# ---------------------------------------------------------------------------
CMD=$(cat <<'COMMAND'
export WANDB_MODE=offline

python -u experiments/01_end_to_end/codes/train.py \
    --config-dir custom_datasets_demo/01_end_to_end/configs \
    data=custom_luca_demo \
    model=train/PCA \
    trainer=PCA \
    'trainer.temp_dir=${weights.dir}/pca-work' \
    model.model_args.n_components=50 \
    weights.dir=results/luca-demo/reference-pca \
    logging.dir=results/luca-demo/reference-pca/logs \
    hydra.run.dir=results/luca-demo/reference-pca/hydra
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
