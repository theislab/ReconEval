#!/usr/bin/env bash
# Submit from the repository root after download_checkpoints.sbatch completes:
# mkdir -p logs
# sbatch custom_datasets_demo/02_foundation_model/submit/extract_embeddings.sbatch
# Embed all demo groups with SE, scGPT, scConcept, and SCimilarity.
#SBATCH --job-name=luca-demo-fm-emb
#SBATCH --partition=gpu_p
#SBATCH --qos=gpu_normal
#SBATCH --gres=gpu:h100:1
#SBATCH --cpus-per-task=8
#SBATCH --mem=128G
#SBATCH --time=04:00:00
#SBATCH --output=logs/luca-demo-fm-emb-%j.out

set -euo pipefail
cd "${SLURM_SUBMIT_DIR:?}"

# ---------------------------------------------------------------------------
# Paths
# ---------------------------------------------------------------------------
image=/lustre/scratch/users/olga.novitskaia/reconeval-images/42016471/reconeval-all.sif
data_dir=$(realpath data)
pretrained_dir=$(realpath checkpoints/pretrained)
mkdir -p data/luca/demo/embeddings/{SE,scGPT,scConcept,scimilarity}
mkdir -p checkpoints/pretrained/scConcept/Corpus-30M/cache

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
        model_args.checkpoint_path=checkpoints/pretrained/SE/se600m_epoch16.ckpt \
        model_args.protein_embeds_path=checkpoints/pretrained/SE/protein_embeddings.pt \
        data_args.comb_meta_root=data/luca/demo/expression.zarr \
        data_args.split_meta_root=data/luca/demo/split_metadata.zarr \
        data_args.target_key=null \
        data_args.output_dir=data/luca/demo/embeddings/SE/grouped.zarr \
        parts=1 \
        total_parts=1

## scGPT
conda run --no-capture-output -n reconeval-scgpt \
    python -u experiments/02_foundation_model/codes/scGPT_emb.py \
        model_args.checkpoint_path=checkpoints/pretrained/scGPT \
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
        model_args.checkpoint_path=checkpoints/pretrained/scConcept/Corpus-30M \
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
        model_args.checkpoint_path=checkpoints/pretrained/scimilarity/model_v1.1 \
        model_args.gene_overlap_threshold=400 \
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
# Run — mount the repository (including checkpoints) and external data
# ---------------------------------------------------------------------------
mkdir -p results/luca-demo/tmp
apptainer exec --cleanenv --nv \
    --env TMPDIR=/work/results/luca-demo/tmp \
    --bind "$PWD:/work" \
    --bind "$(realpath results):$(realpath results)" \
    --bind "$pretrained_dir:$(readlink checkpoints/pretrained)" \
    --bind "$data_dir:$(readlink data)" \
    --pwd /work \
    "$image" \
    bash -e -c "$CMD"
