#!/usr/bin/env bash
# Historical plot launcher for the completed fixed-latent 2048 study.
#SBATCH --job-name=luca-complexity-2048-grid9-plot
#SBATCH --partition=cpu_p
#SBATCH --qos=cpu_normal
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=logs/runtime_complexity/luca-complexity-2048-grid9-plot-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/42016471/reconeval-all.sif}
apptainer exec --cleanenv \
    --bind "$PWD:/work" \
    --pwd /work "$image" \
    conda run --no-capture-output -n reconeval \
    python runtime/01_end_to_end/codes/plot_time_vs_flops.py \
    --benchmark-dir runtime/01_end_to_end/complexity/fixed_latent_2048 \
    --benchmark-results-dir runtime/01_end_to_end/complexity/fixed_latent_2048 \
    --latent-dim 2048 \
    --pca-flops-dir runtime/01_end_to_end/flops \
    --measurements-dir runtime/01_end_to_end/measurements/fixed_latent_2048 \
    --figure-dir runtime/01_end_to_end/figures/fixed_latent_2048
