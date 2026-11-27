#!/usr/bin/env bash
# Count AE/VAE FLOPs on H100; refresh the full grid and selected configurations.
# mkdir -p logs/runtime
#SBATCH --job-name=luca-flop-count
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=20
#SBATCH --mem=128G
#SBATCH --time=01:00:00
#SBATCH --output=logs/runtime/luca-runtime-flops-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/42016471/reconeval-all.sif}
work="runtime/01_end_to_end/tmp/flop_counter/${SLURM_JOB_ID:?}"
mkdir -p "$work/temp" "$work/cache"
export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"
apptainer exec --cleanenv --nv \
    --env TMPDIR="/work/$work/temp" \
    --env XDG_CACHE_HOME="/work/$work/cache" \
    --env MPLCONFIGDIR="/work/$work/cache/matplotlib" \
    --env NUMBA_CACHE_DIR="/work/$work/cache/numba" \
    --env CUDA_CACHE_PATH="/work/$work/cache/cuda" \
    --env PYTHONDONTWRITEBYTECODE=1 \
    --env OMP_NUM_THREADS="$SLURM_CPUS_PER_TASK" \
    --bind "$PWD:/work" \
    --bind "$(realpath results):$(realpath results)" \
    --bind "$(realpath data):$(readlink data):ro" \
    --pwd /work "$image" \
    conda run --no-capture-output -n reconeval bash -c '
        set -e
        python -B -u runtime/01_end_to_end/codes/estimate_flops.py
        python -B -u runtime/01_end_to_end/complexity/codes/prepare.py \
            --benchmark-dir runtime/01_end_to_end/complexity/fixed_latent_2048 \
            --flops-dir runtime/01_end_to_end/flops \
            --output-dir runtime/01_end_to_end/complexity/fixed_latent_2048
    '
