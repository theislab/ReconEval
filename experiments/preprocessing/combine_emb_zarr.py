"""Combine grouped expression and embedding zarr stores into flat train/val zarr.

SE_emb.py (and other FM embedding scripts) save embeddings as <group>/X in a
grouped zarr, one group per cell-type / dataset / origin combination. The
decoder training script (train_decoder_from_embedding.py) expects a flat zarr
with all training cells concatenated as top-level X (expression) and <emb_key>
(embedding) arrays.

This script reads:
  - expression.zarr : grouped expression store (<group>/X)
  - split_metadata.zarr : train/val/test group-name lists
  - grouped.zarr : grouped embedding store (<group>/X)

and writes:
  - <out_dir>/train.zarr : flat zarr with X (expression) and <emb_key>
  - <out_dir>/val.zarr   : flat zarr with X (expression) and <emb_key>

Usage:
  python experiments/preprocessing/combine_emb_zarr.py \
      --expression-zarr /path/to/expression.zarr \
      --split-meta-zarr /path/to/split_metadata.zarr \
      --embedding-zarr  /path/to/grouped.zarr \
      --embedding-key   SE \
      --out-dir         /path/to/embeddings/SE
"""

from __future__ import annotations
import argparse
from pathlib import Path

import numpy as np
import zarr


def combine(
    expression_zarr: Path,
    split_meta_zarr: Path,
    embedding_zarr: Path,
    embedding_key: str,
    out_dir: Path,
    chunk_size: int = 5_000,
) -> None:
    expr = zarr.open(str(expression_zarr), mode="r")
    embs = zarr.open(str(embedding_zarr), mode="r")
    meta = zarr.open(str(split_meta_zarr), mode="r")

    for split_name, split_key in [
        ("train", "train_combinations"),
        ("val",   "val_combinations"),
    ]:
        groups = list(meta.attrs[split_key])
        print(f"\n{split_name}: {len(groups)} groups")

        X_list  = [expr[g]["X"][:] for g in groups]
        SE_list = [embs[g]["X"][:] for g in groups]

        X   = np.concatenate(X_list,  axis=0).astype("float32")
        SE  = np.concatenate(SE_list, axis=0).astype("float32")
        print(f"  X={X.shape}, {embedding_key}={SE.shape}")

        out_path = out_dir / f"{split_name}.zarr"
        out = zarr.open(str(out_path), mode="w")
        out.create_dataset("X",           data=X,  chunks=(chunk_size, X.shape[1]))
        out.create_dataset(embedding_key, data=SE, chunks=(chunk_size, SE.shape[1]))
        print(f"  Saved to {out_path}")


def main() -> None:
    p = argparse.ArgumentParser(description=__doc__)
    p.add_argument("--expression-zarr", required=True, type=Path)
    p.add_argument("--split-meta-zarr", required=True, type=Path)
    p.add_argument("--embedding-zarr",  required=True, type=Path)
    p.add_argument("--embedding-key",   required=True)
    p.add_argument("--out-dir",         required=True, type=Path)
    p.add_argument("--chunk-size",      type=int, default=5_000)
    args = p.parse_args()

    args.out_dir.mkdir(parents=True, exist_ok=True)
    combine(
        expression_zarr=args.expression_zarr,
        split_meta_zarr=args.split_meta_zarr,
        embedding_zarr=args.embedding_zarr,
        embedding_key=args.embedding_key,
        out_dir=args.out_dir,
        chunk_size=args.chunk_size,
    )


if __name__ == "__main__":
    main()
