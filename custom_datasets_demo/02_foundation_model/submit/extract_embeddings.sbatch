#!/usr/bin/env bash
# Submit from the repository root:
# mkdir -p logs
# sbatch custom_datasets_demo/02_foundation_model/submit/extract_embeddings.sbatch
# Embed all demo groups with SE, scGPT, scConcept, and SCimilarity.
#SBATCH --job-name=luca-demo-fm-emb
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=32G
#SBATCH --time=04:00:00
#SBATCH --output=logs/luca-demo-fm-emb-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=${RECONEVAL_IMAGE:-/lustre/scratch/users/olga.novitskaia/reconeval-images/41522356/reconeval-all.sif}
data_dir=$(realpath data)
model_dir=/lustre/groups/ml01/workspace/xiaotong.fu/data/reconstruction/sup
mkdir -p data/luca/demo/embeddings/{SE,scGPT,scConcept,scimilarity}
mkdir -p results/luca-demo/fm/scConcept/cache

export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"

# ---------------------------------------------------------------------------
# Commands to run inside the container
# ---------------------------------------------------------------------------
CMD=$(cat <<'COMMAND'
## Add the Ensembl IDs needed by scConcept, in expression-column order.
conda run --no-capture-output -n reconeval python - <<'PY'
import h5py
import zarr
from anndata.io import read_elem

with h5py.File("data/luca/core_250130.h5ad", "r") as source:
    var = read_elem(source["var"])
gene_ids = dict(zip(var["feature_name"], var.index))
expression = zarr.open("data/luca/demo/expression.zarr", mode="r+")
expression.attrs["var_ensembl_ids_38"] = [
    gene_ids[gene].split(".")[0] for gene in expression.attrs["var_names"]
]
PY

## SE
conda run --no-capture-output -n reconeval-state \
    python -u experiments/02_foundation_model/codes/SE_emb.py \
        data_args.comb_meta_root=data/luca/demo/expression.zarr \
        data_args.split_meta_root=data/luca/demo/split_metadata.zarr \
        data_args.target_key=null \
        data_args.output_dir=data/luca/demo/embeddings/SE/grouped.zarr \
        parts=1 \
        total_parts=1

## scGPT
conda run --no-capture-output -n reconeval-scgpt \
    python -u experiments/02_foundation_model/codes/scGPT_emb.py \
        data_args.comb_meta_root=data/luca/demo/expression.zarr \
        data_args.split_meta_root=data/luca/demo/split_metadata.zarr \
        data_args.target_key=null \
        data_args.output_dir=data/luca/demo/embeddings/scGPT/grouped.zarr \
        data_args.var_names_path=data/luca/demo/expression.zarr \
        data_args.var_names_key=var_names \
        +model_args.gene_col=gene_name \
        parts=1 \
        total_parts=1

## scConcept
conda run --no-capture-output -n reconeval-scconcept \
    python -u experiments/02_foundation_model/codes/scConcept_emb.py \
        data_args.comb_meta_root=data/luca/demo/expression.zarr \
        data_args.split_meta_root=data/luca/demo/split_metadata.zarr \
        data_args.target_key=null \
        data_args.output_dir=data/luca/demo/embeddings/scConcept/grouped.zarr \
        data_args.var_names_path=data/luca/demo/expression.zarr \
        data_args.var_names_key=var_ensembl_ids_38 \
        parts=1 \
        total_parts=1

## scimilarity
conda run --no-capture-output -n reconeval-scimilarity \
    python -u experiments/02_foundation_model/codes/scimilarity_emb.py \
        data_args.comb_meta_root=data/luca/demo/expression.zarr \
        data_args.split_meta_root=data/luca/demo/split_metadata.zarr \
        data_args.target_key=null \
        data_args.output_dir=data/luca/demo/embeddings/scimilarity/grouped.zarr \
        data_args.var_names_path=data/luca/demo/expression.zarr \
        data_args.var_names_key=var_names \
        parts=1 \
        total_parts=1

COMMAND
)

# ---------------------------------------------------------------------------
# Run — mount the repository, external data, model files, and scConcept cache
# ---------------------------------------------------------------------------
mkdir -p results/luca-demo/tmp
apptainer exec --cleanenv --nv \
    --env TMPDIR=/work/results/luca-demo/tmp \
    --bind "$PWD:/work" \
    --bind "$data_dir:$data_dir" \
    --bind "$model_dir:$model_dir:ro" \
    --bind "$PWD/results/luca-demo/fm/scConcept/cache:$model_dir/scconcept/Corpus-30M/cache" \
    --pwd /work \
    "$image" \
    bash -e -c "$CMD"
