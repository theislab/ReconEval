#!/usr/bin/env bash
# Submit from the repository root:
# mkdir -p logs
# sbatch custom_datasets_demo/02_foundation_model/submit/evaluate.sbatch
# Set each model's checkpoint path in the checkpoints list below.
# Reuse the reference PCA from custom_datasets_demo/01_end_to_end/submit/reference_pca.sbatch.
#SBATCH --job-name=luca-demo-fm-eval
#SBATCH --partition=cpu_p
#SBATCH --qos=cpu_normal
#SBATCH --cpus-per-task=18
#SBATCH --mem=64G
#SBATCH --time=04:00:00
#SBATCH --output=logs/luca-demo-fm-eval-%j.out

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
## Set the saved decoder checkpoint path for each model.
declare -A checkpoints=(
    [SE]='results/luca-demo/fm/SE/MLP/<checkpoint>.ckpt'
    [scGPT]='results/luca-demo/fm/scGPT/MLP/<checkpoint>.ckpt'
    [scConcept]='results/luca-demo/fm/scConcept/MLP/<checkpoint>.ckpt'
    [scimilarity]='results/luca-demo/fm/scimilarity/MLP/<checkpoint>.ckpt'
)

for model in SE scGPT scConcept scimilarity; do
    ## Distributional metrics (R2, MSE, MMD, energy distance)
    python -u experiments/02_foundation_model/codes/eval_decoder_statistical.py \
        --config-dir custom_datasets_demo/02_foundation_model/configs \
        --config-name base_eval_decode_demo \
        "pretrained=$model" \
        decoder=MLP \
        metric=decode_statistical_demo \
        "decoder.load.path='${checkpoints[$model]}'" \
        'metric.projector.load.path=[results/luca-demo/reference-pca/mean.zarr,results/luca-demo/reference-pca/pc_50.zarr]' \
        "output.save_path=results/luca-demo/fm/$model/distributional.csv"

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
