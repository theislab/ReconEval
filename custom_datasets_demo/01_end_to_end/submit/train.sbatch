#!/usr/bin/env bash
# Submit from the repository root:
# mkdir -p logs
# sbatch custom_datasets_demo/01_end_to_end/submit/train.sbatch
# Edit CMD below to choose models and parameters.
#SBATCH --job-name=luca-demo-train
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=20
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/luca-demo-train-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/41522356/reconeval-all.sif}
output_dir=results/luca-demo
mkdir -p "$output_dir/logs"

export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"

# ---------------------------------------------------------------------------
# Commands to run inside the container
# ---------------------------------------------------------------------------
CMD=$(cat <<'COMMAND'
export WANDB_MODE=offline

## PCA
python -u experiments/01_end_to_end/codes/train.py --multirun \
    --config-dir custom_datasets_demo/01_end_to_end/configs \
    data=custom_luca_demo \
    model=train/PCA \
    trainer=PCA \
    'trainer.temp_dir=${weights.dir}/pca-work' \
    model.model_args.n_components=10,32,128 \
    'weights.dir=results/luca-demo/PCA/${model.model_args.n_components}' \
    logging.dir=results/luca-demo/logs \
    hydra.sweep.dir=results/luca-demo/hydra/PCA \
    'hydra.sweep.subdir=${model.model_args.n_components}'

## mlAE
python -u experiments/01_end_to_end/codes/train.py --multirun \
    --config-dir custom_datasets_demo/01_end_to_end/configs \
    data=custom_luca_demo \
    model=train/AE \
    trainer=AE \
    model.meta.name=mlAE \
    model.model_args.library_size_mode=modeled \
    'model.model_args.n_hidden=[1024]' \
    model.model_args.n_latent=10,32,128 \
    'weights.dir=results/luca-demo/mlAE/${model.model_args.n_latent}' \
    logging.dir=results/luca-demo/logs \
    hydra.sweep.dir=results/luca-demo/hydra/mlAE \
    'hydra.sweep.subdir=${model.model_args.n_latent}'

## nlscVI
python -u experiments/01_end_to_end/codes/train.py --multirun \
    --config-dir custom_datasets_demo/01_end_to_end/configs \
    data=custom_luca_demo \
    model=train/nlscVI \
    trainer=scVI \
    model.model_args.n_hidden=1024 \
    model.model_args.n_layers=1 \
    model.model_args.n_latent=10,32,128 \
    'weights.dir=results/luca-demo/nlscVI/${model.model_args.n_latent}' \
    logging.dir=results/luca-demo/logs \
    hydra.sweep.dir=results/luca-demo/hydra/nlscVI \
    'hydra.sweep.subdir=${model.model_args.n_latent}'
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
