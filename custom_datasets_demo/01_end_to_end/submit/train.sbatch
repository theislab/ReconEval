#!/usr/bin/env bash
# Submit from the repository root:
# mkdir -p logs
# sbatch custom_datasets_demo/01_end_to_end/submit/train.sbatch
# Array tasks: PCA 0-2, mlAE 3-5, nlscVI 6-8; latent dimensions 10, 32, 128.
#SBATCH --job-name=luca-demo-train
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=20
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --array=0-8
#SBATCH --output=logs/luca-demo-train-%A_%a.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/42016471/reconeval-all.sif}
output_dir=results/luca-demo
mkdir -p "$output_dir/logs"

export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"

# ---------------------------------------------------------------------------
# Commands to run inside the container
# ---------------------------------------------------------------------------
CMD=$(cat <<'COMMAND'
export WANDB_MODE=offline
task_id=${1:?Pass the Slurm array task ID}
models=(PCA mlAE nlscVI)
latent_dims=(10 32 128)
model=${models[$((task_id / 3))]}
latent_dim=${latent_dims[$((task_id % 3))]}
echo "Training $model with latent dimension $latent_dim (array task $task_id)"

case "$model" in
PCA)
python -u experiments/01_end_to_end/codes/train.py \
    --config-dir custom_datasets_demo/01_end_to_end/configs \
    data=custom_luca_demo \
    model=train/PCA \
    trainer=PCA \
    '+trainer.gpu_ids=${oc.env:CUDA_VISIBLE_DEVICES}' \
    'trainer.temp_dir=${weights.dir}/pca-work' \
    model.model_args.n_components="$latent_dim" \
    'weights.dir=results/luca-demo/PCA/${model.model_args.n_components}' \
    logging.dir=results/luca-demo/logs \
    hydra.run.dir="results/luca-demo/hydra/PCA/$latent_dim"
;;

mlAE)
python -u experiments/01_end_to_end/codes/train.py \
    --config-dir custom_datasets_demo/01_end_to_end/configs \
    data=custom_luca_demo \
    model=train/AE \
    trainer=AE \
    model.meta.name=mlAE \
    model.model_args.library_size_mode=modeled \
    'model.model_args.n_hidden=[1024]' \
    model.model_args.n_latent="$latent_dim" \
    'weights.dir=results/luca-demo/mlAE/${model.model_args.n_latent}' \
    logging.dir=results/luca-demo/logs \
    hydra.run.dir="results/luca-demo/hydra/mlAE/$latent_dim"
;;

nlscVI)
python -u experiments/01_end_to_end/codes/train.py \
    --config-dir custom_datasets_demo/01_end_to_end/configs \
    data=custom_luca_demo \
    model=train/nlscVI \
    trainer=scVI \
    model.model_args.n_hidden=1024 \
    model.model_args.n_layers=1 \
    model.model_args.n_latent="$latent_dim" \
    'weights.dir=results/luca-demo/nlscVI/${model.model_args.n_latent}' \
    logging.dir=results/luca-demo/logs \
    hydra.run.dir="results/luca-demo/hydra/nlscVI/$latent_dim"
;;
esac
COMMAND
)

# ---------------------------------------------------------------------------
# Run — mount the repository and preserve the external data path
# ---------------------------------------------------------------------------
task_tmp="results/luca-demo/tmp/${SLURM_ARRAY_JOB_ID:?}_${SLURM_ARRAY_TASK_ID:?}"
mkdir -p "$task_tmp"
apptainer exec --cleanenv --nv \
    --env TMPDIR="/work/$task_tmp" \
    --bind "$PWD:/work" \
    --bind "$(realpath results):$(realpath results)" \
    --bind "$(realpath data):$(readlink data)" \
    --pwd /work \
    "$image" \
    conda run --no-capture-output -n reconeval \
    bash -e -c "$CMD" -- "$SLURM_ARRAY_TASK_ID"
