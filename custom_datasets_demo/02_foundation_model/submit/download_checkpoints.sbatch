#!/usr/bin/env bash
# Submit from the repository root:
# mkdir -p logs
# sbatch custom_datasets_demo/02_foundation_model/submit/download_checkpoints.sbatch
#SBATCH --job-name=luca-demo-fm-download
#SBATCH --partition=cpu_p
#SBATCH --qos=cpu_normal
#SBATCH --cpus-per-task=4
#SBATCH --mem=16G
#SBATCH --time=04:00:00
#SBATCH --output=logs/luca-demo-fm-download-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

image=/lustre/scratch/users/olga.novitskaia/reconeval-images/42016471/reconeval-all.sif
pretrained_dir=$(realpath checkpoints/pretrained)

apptainer exec --cleanenv \
    --bind "$PWD:/work" \
    --bind "$pretrained_dir:$(readlink checkpoints/pretrained)" \
    --pwd /work \
    "$image" \
    conda run --no-capture-output -n reconeval \
    python -u experiments/02_foundation_model/codes/download_checkpoints.py \
        --model all \
        --output-dir checkpoints/pretrained
