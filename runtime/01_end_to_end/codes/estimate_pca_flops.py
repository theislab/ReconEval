"""Estimate floating-point operations (flops) for PCA_sparse.fit (covariance_eigh path)
plus the projection step, as used by rapids_singlecell for sparse input.

Works with cupyx.scipy.sparse (GPU) and scipy.sparse (CPU) CSR matrices, or an AnnData.

Counting convention: 1 multiply + 1 add = 2 flops.
"""

from __future__ import annotations

import numpy as np


def _xp(arr):
    """Return cupy if arr is a CuPy array, else numpy."""
    try:
        import cupy as cp

        if isinstance(arr, cp.ndarray):
            return cp
    except ImportError:
        pass
    return np


def estimate_pca_flops(
    X,
    n_comps: int = 50,
    *,
    upper_triangle_only: bool = False,
    eigh_method: str = "divide_and_conquer",
    include_transform: bool = True,
) -> dict:
    """Estimate flops for sparse covariance_eigh PCA.

    Parameters
    ----------
    X
        CSR matrix (cells x genes), cupyx or scipy, or an AnnData (uses .X).
    n_comps
        Number of principal components (only affects the projection cost).
    upper_triangle_only
        True if the Gram kernel computes only the upper triangle of X^T X
        (halves the Gram cost).
    eigh_method
        "divide_and_conquer" -> ~4.7 d^3 (cuSOLVER syevd, worst case)
        "qr"                 -> ~9 d^3   (classic symmetric QR, upper bound)
    include_transform
        Add the projection X @ V - mean @ V (n x k scores).
    """
    if hasattr(X, "X") and hasattr(X, "obs"):  # AnnData
        X = X.X
    if not hasattr(X, "indptr"):
        raise TypeError("Expected a CSR sparse matrix (or AnnData with sparse .X).")
    if X.format != "csr":
        X = X.tocsr()

    xp = _xp(X.indptr)
    n, d = X.shape
    k = min(n_comps, d)
    nnz = int(X.nnz)

    # nnz_i per cell; float64 avoids integer overflow when squaring and summing
    nnz_i = xp.diff(X.indptr).astype(xp.float64)
    sum_sq = float((nnz_i**2).sum())

    # 1) gene means: one add per nonzero, plus d divisions
    means = nnz + d

    # 2) Gram X^T X: each cell adds an nnz_i x nnz_i block of multiply-adds
    if upper_triangle_only:
        gram = float((nnz_i * (nnz_i + 1)).sum())  # 2 * nnz_i(nnz_i+1)/2
    else:
        gram = 2.0 * sum_sq

    # 3) centering: C = G/n - mu mu^T  (divide, multiply, subtract per entry)
    center = 3.0 * d * d

    # 4) symmetric eigendecomposition with all eigenvectors
    const = {"divide_and_conquer": 4.0 / 3 + 4.0 / 3 + 2.0, "qr": 9.0}[eigh_method]
    eigh = const * d**3

    # 5) explained-variance ratio: sum of d eigenvalues + d divisions
    ratio = 2.0 * d

    parts = {
        "means": float(means),
        "gram": gram,
        "center": center,
        "eigh": eigh,
        "ratio": ratio,
    }

    # 6) transform: sparse X @ V (2*nnz*k) + mean @ V (2*d*k) + subtract (n*k)
    if include_transform:
        parts["transform"] = 2.0 * nnz * k + 2.0 * d * k + float(n * k)

    total = sum(parts.values())
    return {
        "shape": (n, d),
        "nnz": nnz,
        "density": nnz / (n * d),
        "mean_nnz_per_cell": nnz / n,
        "n_comps": k,
        "flops": parts,
        "total_flops": total,
        "share": {key: v / total for key, v in parts.items()},
    }


def print_report(est: dict, seconds: float | None = None) -> None:
    """Pretty-print an estimate; pass measured seconds to get achieved FLOP/s."""
    n, d = est["shape"]
    print(f"cells={n:,}  genes={d:,}  nnz={est['nnz']:.3e}  "
          f"density={est['density']:.1%}  nnz/cell={est['mean_nnz_per_cell']:.0f}  k={est['n_comps']}")
    for key, v in est["flops"].items():
        print(f"  {key:<10} {v:10.3e}  ({est['share'][key]:6.1%})")
    print(f"  {'TOTAL':<10} {est['total_flops']:10.3e}")
    if seconds:
        print(f"  measured {seconds:.3f} s  ->  {est['total_flops'] / seconds / 1e12:.2f} TFLOP/s achieved")

