#!/usr/bin/env bash
# Submit from the repository root after embed.sbatch and decoder.sbatch complete:
# sbatch runtime/02_foundation_model/submit/summarize.sbatch
# Reads original results/luca-runtime-fm records; writes measurement CSVs and
# figures/luca_runtime_fm.svg under runtime/02_foundation_model/.
# Also refreshes complexity_runtime.csv from the 27-run SE decoder manifest.
#SBATCH --job-name=luca-runtime-fm-summary
#SBATCH --partition=cpu_p
#SBATCH --qos=cpu_normal
#SBATCH --cpus-per-task=1
#SBATCH --mem=4G
#SBATCH --time=00:10:00
#SBATCH --output=logs/runtime/luca-runtime-fm-summary-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/43406461/reconeval-all.sif}
mkdir -p runtime/02_foundation_model/tmp
apptainer exec --cleanenv \
    --env TMPDIR=/work/runtime/02_foundation_model/tmp \
    --bind "$PWD:/work" \
    --bind "$(realpath results):$(realpath results)" \
    --pwd /work \
    "$image" \
    conda run --no-capture-output -n reconeval \
    python runtime/02_foundation_model/codes/summarize_runtime.py \
    --results-dir results/luca-runtime-fm \
    --measurements-dir runtime/02_foundation_model/measurements \
    --figure-dir runtime/02_foundation_model/figures
