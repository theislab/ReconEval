#!/usr/bin/env bash
# Submit from the repository root:
# mkdir -p logs
# sbatch custom_datasets_demo/preprocessing/submit/prepare_dataset.sbatch
# Override the image with RECONEVAL_IMAGE if needed.
#SBATCH --job-name=luca-demo
#SBATCH --partition=cpu_p
#SBATCH --qos=cpu_normal
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=04:00:00
#SBATCH --output=logs/luca-demo-%j.out

set -euo pipefail
: "${SLURM_JOB_ID:?Submit this script with sbatch}"
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/41522356/reconeval-all.sif}
data_dir=$(realpath data)
input_file=data/luca/core_250130.h5ad
output_dir=data/luca/demo
mkdir -p "$output_dir"

echo "LuCA demo:"
echo "Input: $input_file"
echo "Output: $output_dir"

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
  python -u experiments/preprocessing/prepare_dataset.py \
    --config-name data/luca \
    utils=experiments/preprocessing/utils/luca.py \
    input="$input_file" \
    output="$output_dir" \
    demo=true \
    demo_cells=500 \
    demo_genes=500 \
    seed=42 \
    split.strategy=combination \
    split.path=null \
    hydra.run.dir="$output_dir/logs" \
    hydra.job.chdir=false
