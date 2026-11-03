#!/usr/bin/env bash
set -euo pipefail

# Environment
recipe=${1:?Pass an environment YAML or requirements file}
env_name=${2:?Pass the environment name}
overrides_file=${3:-}
env_dir="/opt/conda/envs/$env_name"
env_python="$env_dir/bin/python"

# Apply optional overrides to the recipe copied into the image.
if [[ -n "$overrides_file" ]]; then
    # Read "package: replacement" entries, skipping blank lines and comments.
    while IFS=': ' read -r package replacement; do
        if [[ -z "$package" || "$package" == "#"* ]]; then
            continue
        fi

        # Find the package's dependency line and replace its current pin.
        line_pattern="^ *- $package="
        pin_pattern="$package=[^ ]*"
        sed -i "/$line_pattern/s|$pin_pattern|$replacement|" "$recipe"
    done < "$overrides_file"
fi

# Installation
if [[ "$recipe" == *.txt ]]; then
    conda create --yes --prefix "$env_dir" --override-channels --channel conda-forge python=3.12 pip
    "$env_python" -m pip install -r "$recipe" /opt/ReconEval
else
    # Use the PyTorch channel for pytorch-cuda; defaults has a cluster TLS error.
    sed -i 's/  - defaults/  - pytorch/' "$recipe"
    # MuData needs scverse-misc's settings dependencies when importing scvi.
    if [[ "$env_name" == reconeval ]]; then
        sed -i '/^dependencies:$/a\  - python-dotenv\n  - pydantic-settings' "$recipe"
        sed -i '/^  - pip:$/a\      - rapids-singlecell==0.13.0' "$recipe"
    fi
    # These recipes also need NVIDIA's CUDA libraries.
    if [[ "$env_name" == reconeval-scgpt || "$env_name" == reconeval-scimilarity ]]; then
        sed -i '/^  - pytorch$/a\  - nvidia' "$recipe"
    fi
    # Keep scGPT's Torch and NumPy versions during pip dependency resolution.
    if [[ "$env_name" == reconeval-scgpt ]]; then
        sed -i '/^  - pip:$/a\      - -r /opt/ReconEval/docker/scgpt_requirements.txt' "$recipe"
    fi
    # STATE uses reconeval-state; its scikit-learn requirement conflicts with CellFlow.
    if [[ "$env_name" == reconeval-pancellflow ]]; then
        sed -i -e '/^      - arc-state$/d' -e '/^      - cell-load$/d' "$recipe"
    fi
    conda env create --prefix "$env_dir" --file "$recipe"
fi

# scConcept
if [[ "$env_name" == reconeval-scconcept ]]; then
    scconcept_commit=1201700aea9e1e4fed88acb26ba5b8a6dbcee607
    # Match envs/scconcept_env.yaml: Python 3.10, Conda Torch 2.6, CUDA 12, C++11 ABI.
    flash_attn_wheel='https://github.com/Dao-AILab/flash-attention/releases/download/v2.8.3/flash_attn-2.8.3+cu12torch2.6cxx11abiTRUE-cp310-cp310-linux_x86_64.whl#sha256=0a6d13b01818ff2758bdb9dc87362c72016303a7c26dd4f497e9e82006744209'
    "$env_python" -m pip install --no-deps \
        "git+https://github.com/theislab/lamin_dataloader.git@v0.1.0" \
        "git+https://github.com/theislab/scConcept.git@$scconcept_commit" "$flash_attn_wheel"
fi

# Runtime caches
mkdir -p "$env_dir/etc/conda/activate.d"
cat > "$env_dir/etc/conda/activate.d/reconeval.sh" <<'ACTIVATE'
export XDG_CACHE_HOME=${XDG_CACHE_HOME:-${TMPDIR:-/tmp}/reconeval-$(id -u)/cache}
export NUMBA_CACHE_DIR=${NUMBA_CACHE_DIR:-$XDG_CACHE_HOME/numba}
export MPLCONFIGDIR=${MPLCONFIGDIR:-$XDG_CACHE_HOME/matplotlib}
ACTIVATE

conda clean --all --yes
