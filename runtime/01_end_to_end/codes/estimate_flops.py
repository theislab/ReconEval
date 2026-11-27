"""Recompute the existing AE/VAE grid with PyTorch FlopCounterMode."""
import csv
import json
from itertools import product
from pathlib import Path
import sys

import torch
import zarr
from torch.utils.flop_counter import FlopCounterMode

ROOT = Path(__file__).resolve().parents[3]
FLOPS_PER_TFLOP = 10**12

sys.path.insert(0, str(ROOT / "src"))
from sc_reconstruction.models.reconae import Autoencoder
from sc_reconstruction.models.reconnlscvi import NormalVAE
from scvi import REGISTRY_KEYS


# ---------------------------------------------------------------------------
# Model helpers
# ---------------------------------------------------------------------------

def build_model(model: str, genes: int, hidden: int, latent: int, depth: int):
    if model == "mlAE":
        return Autoencoder(
            genes, [hidden] * depth, latent,
            distribution="normal", library_size_mode="modeled",
        )
    if model == "nlscVI":
        return NormalVAE(
            n_input=genes, n_batch=1, n_labels=1,
            n_hidden=hidden, n_latent=latent, n_layers=depth,
            gene_likelihood="normal", use_observed_lib_size=True,
        )
    raise ValueError(f"Unknown model: {model!r}")


def compute_loss(model: str, net, x: torch.Tensor) -> torch.Tensor:
    if model == "mlAE":
        return net.compute_loss(x, net(x))
    batch = {
        REGISTRY_KEYS.X_KEY:      x,
        REGISTRY_KEYS.BATCH_KEY:  torch.zeros(len(x), 1, dtype=torch.long, device=x.device),
        REGISTRY_KEYS.LABELS_KEY: torch.zeros(len(x), 1, dtype=torch.long, device=x.device),
    }
    return net(batch)[2].loss


# ---------------------------------------------------------------------------
# FLOP counting
# ---------------------------------------------------------------------------

def count_flops(
    model: str,
    train_x: torch.Tensor,
    val_x: torch.Tensor,
    hidden: int,
    latent: int,
    depth: int,
) -> tuple[int, int, int]:
    """Return forward, backward, and validation FLOPs per cell."""
    torch.manual_seed(42)
    torch.set_float32_matmul_precision("high")

    net = build_model(model, train_x.shape[1], hidden, latent, depth).to(train_x.device)

    # Train pass: forward + backward
    net.train()
    with FlopCounterMode(display=False) as counter:
        value = compute_loss(model, net, train_x)
        forward = counter.get_total_flops()
        value.backward()
        backward = counter.get_total_flops() - forward

    # Validation pass
    net.eval()
    with torch.no_grad(), FlopCounterMode(display=False) as counter:
        compute_loss(model, net, val_x)
        validation = counter.get_total_flops()

    assert forward % len(train_x) == backward % len(train_x) == validation % len(val_x) == 0
    return forward // len(train_x), backward // len(train_x), validation // len(val_x)


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------

GRID = list(product(
    ("mlAE", "nlscVI"),          # model
    (10, 32, 128, 512, 2048),    # latent dim
    (1024, 2048, 4096),          # hidden dim
    range(1, 5),                 # depth
))

CSV_HEADER = [
    "model", "latent_dim", "hidden_dim", "depth",
    "train_dense_flops_per_epoch", "train_val_dense_flops_per_epoch",
    "train_dense_tflops_per_epoch", "train_val_dense_tflops_per_epoch",
]


def main():
    config = json.loads(
        (ROOT / "runtime/01_end_to_end/complexity/fixed_latent_2048/configs/benchmark.json").read_text()
    )

    def load_split(split: str) -> torch.Tensor:
        data = zarr.open(str(ROOT / config["data_dir"] / f"{split}.zarr"), mode="r")["X"]
        return data, torch.as_tensor(data[: config["batch_size"]], device="cuda")

    train_data, train_x = load_split("train")
    val_data,   val_x   = load_split("val")

    rows = []
    for model, latent, hidden, depth in GRID:
        forward, backward, validation = count_flops(model, train_x, val_x, hidden, latent, depth)
        train = (forward + backward) * train_data.shape[0]
        total = train + validation * val_data.shape[0]
        rows.append([
            model, latent, hidden, depth,
            train, total,
            train / FLOPS_PER_TFLOP,
            total / FLOPS_PER_TFLOP,
        ])
        print(
            f"{len(rows)}/{len(GRID)} {model} {latent}/{hidden}/{depth}: "
            f"{total / FLOPS_PER_TFLOP:.4f} TFLOPs/epoch",
            flush=True,
        )

    out_dir = ROOT / "runtime/01_end_to_end/flops"
    out_dir.mkdir(parents=True, exist_ok=True)
    with (out_dir / "grid.csv").open("w", newline="") as fh:
        writer = csv.writer(fh)
        writer.writerow(CSV_HEADER)
        writer.writerows(rows)

    metadata = {
        "method":               "FlopCounterMode",
        "torch_version":        torch.__version__,
        "gpu":                  torch.cuda.get_device_name(),
        "n_genes":              train_data.shape[1],
        "n_train":              train_data.shape[0],
        "n_val":                val_data.shape[0],
        "data_dir":             config["data_dir"],
        "profile_batch_size":   config["batch_size"],
        "scope": (
            "Supported matrix FLOPs; first real LuCA train/validation batches, "
            "scaled to full-data epochs; multiply-add = 2"
        ),
    }
    (out_dir / "metadata.json").write_text(json.dumps(metadata, indent=2) + "\n")


if __name__ == "__main__":
    main()
