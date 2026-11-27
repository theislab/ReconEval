"""Compare neural epoch FLOPs with the supplied PCA fit-only estimate.

python runtime/01_end_to_end/codes/plot_flops_with_pca.py --input data/luca/full/train.h5ad

Read the actual CSR structure without loading expression values. PCA counts
are analytical estimates; they are not measured GPU instruction counts.
Use --reuse-pca-estimates to plot existing estimates without reading the
expression dataset or rewriting the PCA CSV/JSON files.
"""

import argparse
import json
import math
import os
import sys
from pathlib import Path
from types import SimpleNamespace

import h5py
import numpy as np
import pandas as pd

os.environ.setdefault("MPLCONFIGDIR", "/tmp/reconeval-runtime-review/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt


ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "runtime/01_end_to_end"
FLOPS_DIR = RESULTS / "flops"

sys.path.insert(0, str(Path(__file__).parent))
from summarize_runtime import MODELS, LABELS, LATENTS
from estimate_pca_flops import estimate_pca_flops

ARCHITECTURES = [(hidden, depth) for hidden in (1024, 2048, 4096) for depth in (1, 2, 3, 4)]


def estimate_pca(input_path, *, flops_dir=FLOPS_DIR):
    """Pass real CSR shape, nnz, and row pointers to the supplied estimator."""
    with h5py.File(input_path, "r") as source:
        x = source["X"]
        if x.attrs.get("encoding-type") != "csr_matrix":
            raise ValueError(f"Expected CSR-encoded X in {input_path}")
        shape = tuple(map(int, x.attrs["shape"]))
        indptr = x["indptr"][:]
        nnz = int(x["data"].shape[0])
        assert len(indptr) == shape[0] + 1 and indptr[0] == 0
        assert int(indptr[-1]) == nnz == x["indices"].shape[0]
        assert np.all(np.diff(indptr) >= 0)
    reference = json.loads((flops_dir / "metadata.json").read_text())
    assert shape == (reference["n_train"], reference["n_genes"])

    # The estimator only reads these four CSR properties; values are unnecessary.
    structure = SimpleNamespace(shape=shape, indptr=indptr, nnz=nnz, format="csr")
    row_nnz = np.diff(indptr).astype(np.float64)
    stats = {
        "source_h5ad": str(input_path.resolve()),
        "shape": shape,
        "n_nonzero": nnz,
        "density": nnz / math.prod(shape),
        "mean_nnz_per_cell": float(row_nnz.mean()),
        "sum_row_nnz_squared": float(np.square(row_nnz).sum()),
        "source": "Actual CSR X/indptr, X/data length, and X shape; no synthetic matrix.",
    }
    (flops_dir / "pca_input_statistics.json").write_text(json.dumps(stats, indent=2) + "\n")

    estimates, rows = [], []
    for method in ("divide_and_conquer",):
        for latent in LATENTS:
            est = estimate_pca_flops(structure, n_comps=latent, eigh_method=method,
                                     include_transform=False)
            estimates.append({"eigh_method": method, **est})
            fit = sum(v for key, v in est["flops"].items() if key != "transform")
            rows.append({
                "eigh_method": method, "latent_dim": latent,
                "n_cells": shape[0], "n_genes": shape[1], "nnz": nnz,
                **{f"{key}_flops": v for key, v in est["flops"].items()},
                "fit_flops": fit, "total_flops": est["total_flops"],
                "fit_tflops": fit / 1e12, "total_tflops": est["total_flops"] / 1e12,
            })
    pd.DataFrame(rows).to_csv(flops_dir / "pca_flops.csv", index=False)
    report = {
        "estimator": "runtime/01_end_to_end/codes/estimate_pca_flops.py:estimate_pca_flops",
        "input_statistics": stats,
        "upper_triangle_only": False,
        "include_transform": False,
        "plot_eigh_method": "divide_and_conquer",
        "scope": "One PCA fit, excluding projection of the training cells (include_transform=False).",
        "comparison_note": "Neural curves show one training+validation epoch; PCA shows one fit. These are different work units.",
        "status": "Analytical FLOP estimates, not measured GPU instructions or throughput.",
        "estimates": estimates,
    }
    (flops_dir / "pca_flops_estimate.json").write_text(json.dumps(report, indent=2) + "\n")
    return {row["latent_dim"]: row["total_tflops"] for row in rows
            if row["eigh_method"] == report["plot_eigh_method"]}


def load_pca_estimates(flops_dir):
    """Read the saved fit-only estimates without recalculation or writes."""
    report = json.loads((flops_dir / "pca_flops_estimate.json").read_text())
    metadata = json.loads((flops_dir / "metadata.json").read_text())
    if report["include_transform"] is not False:
        raise ValueError("The figure requires PCA fit-only estimates")
    df = pd.read_csv(flops_dir / "pca_flops.csv")
    df = df[df["eigh_method"] == report["plot_eigh_method"]].copy()
    if df["latent_dim"].duplicated().any():
        raise ValueError("Duplicate PCA estimates")
    if not ((df["n_cells"] == metadata["n_train"]) & (df["n_genes"] == metadata["n_genes"])).all():
        raise ValueError("PCA estimates and neural FLOP metadata use different inputs")
    if not (df["fit_flops"] == df["total_flops"]).all():
        raise ValueError("Expected fit-only estimates (fit_flops != total_flops)")
    df["total_tflops"] = df["total_flops"] / 1e12
    if not (df["total_tflops"] > 0).all():
        raise ValueError("Invalid PCA estimates")
    if set(df["latent_dim"]) != set(LATENTS):
        raise ValueError(f"Expected saved PCA estimates for {LATENTS}")
    return dict(zip(df["latent_dim"], df["total_tflops"]))


def create_figure(values, pca):
    """Return the FLOPs-per-latent figure (one panel per latent dimension).

    *values*: dict keyed by (model, latent_dim, hidden_dim, depth) → TFLOPs/epoch.
    *pca*:    dict keyed by latent_dim → fit-only TFLOPs.
    """
    fig, axes = plt.subplots(1, len(LATENTS), figsize=(4 * len(LATENTS), 4),
                             sharey=True, layout="constrained")
    for ax, latent in zip(axes, LATENTS):
        for model in ("mlAE", "nlscVI"):
            color, marker = MODELS[model]
            ys = [values[model, latent, hidden, depth] for hidden, depth in ARCHITECTURES]
            ax.plot(range(len(ARCHITECTURES)), ys, color=color, marker=marker,
                    label=f"{LABELS[model]} / epoch")
        ax.axhline(pca[latent], color=MODELS["PCA"][0],
                   linestyle="--", label="PCA / fit (approx.)")
        ax.set(yscale="log", ylim=(0.7, 1000), xlabel="Hidden width × depth",
               title=f"Latent dimension {latent}")
        ax.set_xticks(
            range(len(ARCHITECTURES)),
            [f"{hidden}×{depth}" for hidden, depth in ARCHITECTURES],
            rotation=90, fontsize=8,
        )
        ax.grid(linestyle="--", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("TFLOPs per epoch or fit")
    axes[0].set_yticks([1, 10, 100, 1000], ["1", "10", "100", "1000"])
    axes[0].legend(frameon=False, loc="center right")
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--input", type=Path,
                        default=ROOT / "data/luca/runtime/full/train.h5ad")
    parser.add_argument("--flops-dir", type=Path, default=FLOPS_DIR)
    parser.add_argument("--figure-dir", type=Path, default=RESULTS / "figures")
    parser.add_argument("--reuse-pca-estimates", action="store_true",
                        help="Plot saved PCA estimates without recalculating or rewriting them.")
    args = parser.parse_args()
    if not args.reuse_pca_estimates:
        args.flops_dir.mkdir(parents=True, exist_ok=True)
    args.figure_dir.mkdir(parents=True, exist_ok=True)

    grid = pd.read_csv(args.flops_dir / "grid.csv")
    assert len(grid) == 120 and (grid["train_val_dense_tflops_per_epoch"] > 0).all()
    values = {
        (row.model, row.latent_dim, row.hidden_dim, row.depth): row.train_val_dense_tflops_per_epoch
        for row in grid.itertuples()
    }
    pca = (load_pca_estimates(args.flops_dir) if args.reuse_pca_estimates
           else estimate_pca(args.input, flops_dir=args.flops_dir))

    fig = create_figure(values, pca)
    for extension in ("png", "svg"):
        output = args.figure_dir / f"flops_with_pca.{extension}"
        fig.savefig(output, dpi=180)
        print(output)
    plt.close(fig)
    for latent, tflops in pca.items():
        print(f"PCA fit only, k={latent}: {tflops:.6f} TFLOPs")


if __name__ == "__main__":
    main()
