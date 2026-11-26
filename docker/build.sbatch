#!/usr/bin/env bash
# Submit from the repository root:
# mkdir -p logs/slurm
# sbatch docker/build.sbatch

# 1. Slurm settings
#SBATCH --job-name=reconeval-image
#SBATCH --partition=cpu_p
#SBATCH --constraint=amd_epyc_9745
#SBATCH --qos=cpu_normal
#SBATCH --nodes=1
#SBATCH --ntasks=1
#SBATCH --cpus-per-task=8
#SBATCH --mem=64G
#SBATCH --time=1-00:00:00
#SBATCH --output=logs/slurm/reconeval-build-%j.log

set -euo pipefail
cd "$SLURM_SUBMIT_DIR"

# 2. Build settings
target=all
build_root="/localscratch/$USER/reconeval-build-$SLURM_JOB_ID"
output_dir="/lustre/scratch/users/$USER/reconeval-images/$SLURM_JOB_ID"
image="localhost/reconeval:$target"
artifact="reconeval-$target"

mkdir -p "$output_dir"
if [[ -e "$output_dir/$artifact.tar" || -e "$output_dir/$artifact.sif" ]]; then
    echo "Images already exist in $output_dir. Choose a new output_dir." >&2
    exit 2
fi

# 3. Rootless Podman storage (keep build_root on node-local scratch)
mkdir -p "$build_root"/{storage,run,tmp,xdg}
chmod 700 "$build_root/xdg"
export XDG_RUNTIME_DIR="$build_root/xdg"
export TMPDIR="$build_root/tmp"
export APPTAINER_TMPDIR="$build_root/tmp"
podman_cmd=(podman
    --root "$build_root/storage"
    --runroot "$build_root/run"
    --storage-driver vfs
    --storage-opt vfs.ignore_chown_errors=true
    --cgroup-manager cgroupfs
    --events-backend file
    --tmpdir "$build_root/tmp"
)

# 4. Build the image
"${podman_cmd[@]}" build --network host --format docker --layers \
    --jobs 1 --target "$target" --tag "$image" .

# 5. Export .tar and .sif
"${podman_cmd[@]}" save --format docker-archive \
    --output "$output_dir/$artifact.tar" "$image"

apptainer build --disable-cache \
    --mksquashfs-args "-processors $SLURM_CPUS_PER_TASK -mem 8G" \
    "$output_dir/$artifact.sif" \
    "docker-archive:$output_dir/$artifact.tar"

echo "Images: $output_dir"
