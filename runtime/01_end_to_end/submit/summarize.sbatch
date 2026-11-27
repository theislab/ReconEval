#!/usr/bin/env bash
# Submit from the repository root after train.sbatch completes:
# sbatch runtime/01_end_to_end/submit/summarize.sbatch
# Reads original results/luca-runtime records; writes runtime{,_summary}.csv
# under runtime/01_end_to_end/measurements and figures/luca_runtime.svg.
# Also refreshes complexity_runtime.csv from both complexity manifests.
#SBATCH --job-name=luca-runtime-summary
#SBATCH --partition=cpu_p
#SBATCH --qos=cpu_normal
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=logs/runtime/luca-runtime-summary-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/42016471/reconeval-all.sif}
mkdir -p runtime/01_end_to_end/tmp
apptainer exec --cleanenv \
    --env TMPDIR=/work/runtime/01_end_to_end/tmp \
    --bind "$PWD:/work" \
    --bind "$(realpath results):$(realpath results)" \
    --pwd /work \
    "$image" \
    conda run --no-capture-output -n reconeval \
    python runtime/01_end_to_end/codes/summarize_runtime.py \
    --results-dir results/luca-runtime \
    --measurements-dir runtime/01_end_to_end/measurements \
    --figure-dir runtime/01_end_to_end/figures
