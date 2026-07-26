"""Reproduce a paper decoder from a released FM embedding.

Self-contained argparse driver (no Hydra) for training an MLP decoder on
top of pre-computed foundation-model embeddings. Intended for users who
downloaded the released FM embeddings from Hugging Face and want to
regenerate the corresponding decoder checkpoint with one command, one env.

Assumes:
  - FM embeddings live in a zarr store with keys `X` (gene expression) and
    `<embedding_key>` (cell embeddings), e.g. `SE`, `scGPT`, `scConcept`,
    `scimilarity`.
  - Two zarr stores describe the gene axes:
      * `all_genes_zarr.attrs['var_names']`     — the full gene set the
        embeddings were computed against
      * `target_genes_zarr.attrs['var_names']`  — the HVG subset the
        decoder is trained to reconstruct
    The intersection is used as the decoder output.

Canonical path layout on the release bucket (and matching lustre mirror):
  --emb-train-zarr    <dataset>_<FM>/ag/<split>/train.zarr
  --emb-val-zarr      <dataset>_<FM>/ag/<split>/val.zarr
  --all-genes-zarr    <dataset>_w_ag/comb_w_obs.zarr
  --target-genes-zarr <dataset>/comb_w_obs.zarr
"""
from __future__ import annotations

import argparse
import json
import os
import sys
from pathlib import Path

# Ensure the local sc_reconstruction is importable without PYTHONPATH.
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))

import numpy as np
import torch
import zarr
from lightning.pytorch import seed_everything
from lightning.pytorch.callbacks import ModelCheckpoint

from sc_reconstruction.dataloaders.datamodules import SubsetDaskDecodeOnlyDataModule
from sc_reconstruction.decoders.reconmlp import ReconMLPDecoder


def matching_gene_space(all_genes: list[str], target_genes: list[str]) -> np.ndarray:
    return np.array([all_genes.index(g) for g in target_genes if g in all_genes])


def parse_args() -> argparse.Namespace:
    p = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    # ---- data ----
    p.add_argument("--emb-train-zarr", required=True, type=Path,
                   help="Zarr store with `X` + `<embedding_key>` for train split")
    p.add_argument("--emb-val-zarr", required=True, type=Path,
                   help="Zarr store with `X` + `<embedding_key>` for val split")
    p.add_argument("--all-genes-zarr", required=True, type=Path,
                   help="Zarr whose attrs.var_names lists ALL genes the FM saw")
    p.add_argument("--target-genes-zarr", required=True, type=Path,
                   help="Zarr whose attrs.var_names lists the HVG SUBSET to decode")
    p.add_argument("--embedding-key", required=True,
                   choices=["SE", "scGPT", "scConcept", "scimilarity"],
                   help="Which FM embedding to read from the zarr")
    # ---- model ----
    p.add_argument("--latent-dim", type=int, default=None,
                   help="FM embedding dim. If omitted, auto-detected from the "
                        "train zarr as `zarr[<embedding_key>].shape[1]`. "
                        "Actual paper dims: SE=2058, scGPT=512, scConcept=512, "
                        "scimilarity=128.")
    p.add_argument("--n-layers", type=int, default=1)
    p.add_argument("--hidden", type=int, default=4096)
    p.add_argument("--distribution", default="normal",
                   choices=["normal", "huber", "l1",
                            "normal_mle_fixed", "normal_mle_gene"],
                   help="Loss family; must match ReconMLPDecoder.compute_loss.")
    p.add_argument("--library-size-mode", default="none", choices=["none"],
                   help="Only 'none' is honored for decoder-only training.")
    # ---- training ----
    p.add_argument("--epochs", type=int, default=500)
    p.add_argument("--lr", type=float, default=1e-4)
    p.add_argument("--batch-size", type=int, default=256)
    p.add_argument("--chunk-size", type=int, default=5_000)
    p.add_argument("--num-workers", type=int, default=16)
    p.add_argument("--seed", type=int, default=42)
    p.add_argument("--precision", default="high",
                   choices=["highest", "high", "medium"],
                   help="torch.set_float32_matmul_precision")
    # ---- CI / smoke-test escape hatches (forwarded to Lightning Trainer) ----
    p.add_argument("--limit-train-batches", type=float, default=None,
                   help="Lightning Trainer.limit_train_batches (int or 0-1 frac)")
    p.add_argument("--limit-val-batches", type=float, default=None,
                   help="Lightning Trainer.limit_val_batches (int or 0-1 frac)")
    p.add_argument("--max-steps", type=int, default=None,
                   help="Lightning Trainer.max_steps; overrides --epochs when set")
    # ---- output ----
    p.add_argument("--out", required=True, type=Path,
                   help="Directory for checkpoints + config.yaml (created if absent)")
    return p.parse_args()


def main():
    args = parse_args()
    seed_everything(args.seed, workers=True)
    torch.set_float32_matmul_precision(args.precision)
    args.out.mkdir(parents=True, exist_ok=True)

    # --- auto-detect latent dim from the train zarr if not given, or verify ---
    emb_train_root = zarr.open(str(args.emb_train_zarr), mode="r")
    if args.embedding_key not in emb_train_root:
        raise KeyError(
            f"Embedding key {args.embedding_key!r} not found in "
            f"{args.emb_train_zarr}. Available keys: {list(emb_train_root.array_keys())}"
        )
    detected_latent = int(emb_train_root[args.embedding_key].shape[1])
    if args.latent_dim is None:
        args.latent_dim = detected_latent
        print(f"[data] --latent-dim auto-detected as {args.latent_dim}")
    elif args.latent_dim != detected_latent:
        raise ValueError(
            f"--latent-dim={args.latent_dim} does not match the on-disk "
            f"{args.embedding_key} width ({detected_latent}) at {args.emb_train_zarr}."
        )

    # --- resolve HVG gene subset ---
    all_genes = list(zarr.open(str(args.all_genes_zarr), mode="r").attrs["var_names"])
    target_genes = list(zarr.open(str(args.target_genes_zarr), mode="r").attrs["var_names"])
    gene_idx = matching_gene_space(all_genes, target_genes)
    gene_dim = int(len(gene_idx))
    print(f"[data] all genes: {len(all_genes)} | target HVG: {len(target_genes)} | matched: {gene_dim}")

    # --- data ---
    dm = SubsetDaskDecodeOnlyDataModule(
        train_path=str(args.emb_train_zarr),
        val_path=str(args.emb_val_zarr),
        expression_key="X",
        latent_key=args.embedding_key,
        chunk_size=args.chunk_size,
        chunks_per_worker=5,
        minibatch_size=args.batch_size,
        num_workers=args.num_workers,
        target_feature_indices=gene_idx,
    )

    # --- model ---
    decoder = ReconMLPDecoder(
        n_input=args.latent_dim,
        n_output=gene_dim,
        n_layers=args.n_layers,
        n_hidden=args.hidden,
        distribution=args.distribution,
        library_size_mode=args.library_size_mode,
        learning_rate=args.lr,
        reduce_lr_on_plateau=True,
        lr_factor=0.6,
        lr_patience=5,
        lr_threshold=5e-5,
        lr_min=0.0,
    )

    # --- write a config.yaml sidecar so the run is self-describing ---
    (args.out / "config.yaml").write_text(_config_yaml(args, gene_dim))

    # --- train ---
    # Sanitise the metric name in the filename template: Lightning treats a
    # literal "/" inside `filename` as a subdirectory separator, which both
    # nests every ckpt under a stray `val/` dir and breaks flat `out/*.ckpt`
    # globbing. Use `val_loss_epoch` — Lightning replaces the slashed metric.
    ckpt_cb = ModelCheckpoint(
        monitor="val/loss_epoch",
        filename="{epoch:02d}-val_loss_epoch={val_loss_epoch:.4f}",
        auto_insert_metric_name=False,
        dirpath=str(args.out),
        save_top_k=1,
        mode="min",
        save_last=False,
        every_n_epochs=1,
        verbose=True,
    )
    trainer_kwargs = dict(max_epochs=args.epochs, logger=False, callbacks=[ckpt_cb])
    if args.limit_train_batches is not None:
        trainer_kwargs["limit_train_batches"] = args.limit_train_batches
    if args.limit_val_batches is not None:
        trainer_kwargs["limit_val_batches"] = args.limit_val_batches
    if args.max_steps is not None:
        trainer_kwargs["max_steps"] = args.max_steps
    print(f"[train] epochs={args.epochs} lr={args.lr} hidden={args.hidden} "
          f"layers={args.n_layers} latent_dim={args.latent_dim} gene_dim={gene_dim}")
    decoder.train(datamodule=dm, **trainer_kwargs)
    print(f"[done] best ckpt at {ckpt_cb.best_model_path}")


def _config_yaml(args: argparse.Namespace, gene_dim: int) -> str:
    d = {
        **{k: (str(v) if isinstance(v, Path) else v) for k, v in vars(args).items()},
        "gene_dim": gene_dim,
        "decoder_class": "sc_reconstruction.decoders.reconmlp.ReconMLPDecoder",
    }
    lines = ["# generated by train_decoder_from_embedding.py"]
    for k, v in d.items():
        lines.append(f"{k}: {json.dumps(v)}")
    return "\n".join(lines) + "\n"


if __name__ == "__main__":
    main()
