#!/usr/bin/env bash
# Submit from the repository root after evaluate.sbatch completes.
# sbatch custom_datasets_demo/01_end_to_end/submit/plot_metrics.sbatch
#SBATCH --job-name=luca-demo-plots
#SBATCH --partition=cpu_p
#SBATCH --qos=cpu_normal
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=logs/luca-demo-plots-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/41522356/reconeval-all.sif}
mkdir -p results/luca-demo/tmp
apptainer exec --cleanenv \
    --env TMPDIR=/work/results/luca-demo/tmp \
    --bind "$PWD:/work" \
    --pwd /work \
    "$image" \
    conda run --no-capture-output -n reconeval \
    python custom_datasets_demo/01_end_to_end/codes/plot_metrics.py
