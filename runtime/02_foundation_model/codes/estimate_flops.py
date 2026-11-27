"""Recompute the FM decoder grid with PyTorch FlopCounterMode."""
from __future__ import annotations

import csv
import json
from itertools import product
from pathlib import Path
import sys
from typing import TYPE_CHECKING

import pandas as pd

if TYPE_CHECKING:
    import torch

ROOT = Path(__file__).resolve().parents[3]
FLOPS_PER_TFLOP = 10**12

sys.path.insert(0, str(ROOT / "src"))


# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------

def build_model(genes: int, hidden: int, latent: int, depth: int):
    from sc_reconstruction.decoders.reconmlp import MLPDecoder

    return MLPDecoder(
        n_input=latent, n_output=genes, n_hidden=[hidden] * depth,
        distribution="normal", library_size_mode="none",
    )


def compute_loss(net, x: torch.Tensor, z: torch.Tensor) -> torch.Tensor:
    return net.compute_loss(x, net(z))


# ---------------------------------------------------------------------------
# FLOP counting
# ---------------------------------------------------------------------------

def count_flops(
    train_x: torch.Tensor,
    val_x: torch.Tensor,
    train_z: torch.Tensor,
    val_z: torch.Tensor,
    hidden: int,
    depth: int,
) -> tuple[int, int, int]:
    """Return forward, backward, and validation FLOPs per cell."""
    import torch
    from torch.utils.flop_counter import FlopCounterMode

    torch.manual_seed(42)
    torch.set_float32_matmul_precision("high")

    net = build_model(train_x.shape[1], hidden, train_z.shape[1], depth).to(train_x.device)

    # Train pass: forward + backward
    net.train()
    with FlopCounterMode(display=False) as counter:
        value = compute_loss(net, train_x, train_z)
        forward = counter.get_total_flops()
        value.backward()
        backward = counter.get_total_flops() - forward

    # Validation pass
    net.eval()
    with torch.no_grad(), FlopCounterMode(display=False) as counter:
        compute_loss(net, val_x, val_z)
        validation = counter.get_total_flops()

    assert forward % len(train_x) == backward % len(train_x) == validation % len(val_x) == 0
    return forward // len(train_x), backward // len(train_x), validation // len(val_x)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

GRID = list(product(
    ("scimilarity", "scGPT", "scConcept", "Geneformer", "UCE", "SE", "scFoundation"),
    (1024, 2048, 4096),  # hidden dim
    range(1, 5),        # depth
))

CSV_HEADER = [
    "model", "latent_dim", "hidden_dim", "depth",
    "train_dense_flops_per_epoch", "train_val_dense_flops_per_epoch",
    "train_dense_tflops_per_epoch", "train_val_dense_tflops_per_epoch",
    "workload_source", "workload_depth", "n_runs",
    "train_cells_per_epoch", "val_cells_per_epoch",
]


def main():
    import torch
    import zarr
    from summarize_runtime import summarize

    config = json.loads(
        (ROOT / "runtime/01_end_to_end/complexity/fixed_latent_2048/configs/benchmark.json").read_text()
    )
    directory = ROOT / "runtime/02_foundation_model/measurements"
    runs = pd.concat([
        pd.read_csv(directory / name).rename(columns={"n_hidden": "hidden_dim", "n_layers": "depth"})
        for name in ("decoder_runtime.csv", "complexity_runtime.csv")
    ], ignore_index=True)
    runs = runs[(runs.exit_code == 0) & (runs.epochs > 0)
                & (runs.n_train == config["n_train"]) & (runs.n_val == config["n_val"])].drop_duplicates("run_dir")
    keys = ["model", "hidden_dim", "depth"]
    workloads = summarize(runs, keys, ["train_cells_per_epoch", "val_cells_per_epoch"]).set_index(keys)
    data_dir = ROOT / "results/luca-runtime-fm/embed"

    def load_split(model: str, split: str):
        store = zarr.open(str(data_dir / model / "full/repeat-1/emb_combined" / f"{split}.zarr"), mode="r")
        data, embeddings = store["X"], store[model]
        assert data.shape == (config[f"n_{split}"], config["n_genes"])
        assert embeddings.shape[0] == data.shape[0]
        return (data,
                torch.as_tensor(data[: config["batch_size"]], dtype=torch.float32, device="cuda"),
                torch.as_tensor(embeddings[: config["batch_size"]], dtype=torch.float32, device="cuda"))

    rows, sources = [], {}
    current_model = None
    for model, hidden, depth in GRID:
        source_depth = depth if (model, hidden, depth) in workloads.index else 1
        counts = workloads.loc[(model, hidden, source_depth)]
        workload = dict(train_cells_per_epoch=counts.mean_train_cells_per_epoch,
                        val_cells_per_epoch=counts.mean_val_cells_per_epoch,
                        n_runs=int(counts.n_runs), workload_depth=source_depth,
                        workload_source="recorded" if source_depth == depth else "depth_1_estimate")
        if not (0 < workload["train_cells_per_epoch"] <= config["n_train"]
                and 0 < workload["val_cells_per_epoch"] <= config["n_val"]):
            raise ValueError(f"Unverified epoch workload: {(model, hidden, depth)}")
        # Load real expression/embedding batches once per FM.
        if model != current_model:
            assert json.loads((data_dir / model / "full/repeat-1/runtime.json").read_text())["exit_code"] == 0
            train_data, train_x, train_z = load_split(model, "train")
            val_data,   val_x,   val_z   = load_split(model, "val")
            latent = train_z.shape[1]
            assert val_z.shape[1] == latent
            sources[model] = {"path": f"results/luca-runtime-fm/embed/{model}/full/repeat-1/emb_combined",
                              "latent_dim": latent}
            current_model = model

        forward, backward, validation = count_flops(train_x, val_x, train_z, val_z, hidden, depth)
        train = (forward + backward) * workload["train_cells_per_epoch"]
        total = train + validation * workload["val_cells_per_epoch"]
        rows.append(dict(
            model=model, latent_dim=latent, hidden_dim=hidden, depth=depth,
            train_dense_flops_per_epoch=train, train_val_dense_flops_per_epoch=total,
            train_dense_tflops_per_epoch=train / FLOPS_PER_TFLOP,
            train_val_dense_tflops_per_epoch=total / FLOPS_PER_TFLOP,
            **workload,
        ))
        print(
            f"{len(rows)}/{len(GRID)} {model} {latent}/{hidden}/{depth}: "
            f"{total / FLOPS_PER_TFLOP:.4f} TFLOPs/epoch",
            flush=True,
        )

    out_dir = ROOT / "runtime/02_foundation_model/flops"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "grid.csv").open("w", newline="") as fh:
        writer = csv.DictWriter(fh, fieldnames=CSV_HEADER)
        writer.writeheader()
        writer.writerows(rows)

    metadata = {
        "method":               "FlopCounterMode",
        "torch_version":        torch.__version__,
        "gpu":                  torch.cuda.get_device_name(),
        "decoder":              "MLPDecoder",
        "n_genes":              train_data.shape[1],
        "n_train":              train_data.shape[0],
        "n_val":                val_data.shape[0],
        "data_dir":             str(data_dir.relative_to(ROOT)),
        "profile_batch_size":   config["batch_size"],
        "sources":              sources,
        "scope": (
            "Supported matrix FLOPs; first real LuCA expression/embedding batches, "
            "scaled to saved epoch workloads; multiply-add = 2"
        ),
        "scaling": "Mean training/validation cells processed per epoch; unmeasured depths use depth 1 of the same model and width",
        "excluded": ["FM embedding creation", "Optimizer steps", "Unsupported elementwise operations and I/O"],
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
