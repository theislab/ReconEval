#!/usr/bin/env bash
# Submit from the repository root:
# mkdir -p logs
# sbatch custom_datasets_demo/preprocessing/submit/zarr_to_h5ad.sbatch
#SBATCH --job-name=luca-demo-h5ad
#SBATCH --partition=cpu_p
#SBATCH --qos=cpu_normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=00:30:00
#SBATCH --output=logs/luca-demo-h5ad-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/41522356/reconeval-all.sif}

# ---------------------------------------------------------------------------
# Run — mount the repository and preserve the external data path
# ---------------------------------------------------------------------------
mkdir -p results/luca-demo/tmp
apptainer exec --cleanenv \
    --env TMPDIR=/work/results/luca-demo/tmp \
  --bind "$PWD:/work" \
  --bind "$(realpath data):$(realpath data)" \
  --pwd /work \
  "$image" \
  conda run --no-capture-output -n reconeval \
  env PYTHONPATH=/work/src \
  python -u experiments/preprocessing/zarr_to_h5ad.py \
    "$(realpath data)/luca/demo/expression.zarr"
