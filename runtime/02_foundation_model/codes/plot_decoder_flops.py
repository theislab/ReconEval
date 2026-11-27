"""Compare decoder FLOPs across models, alongside optional SE runtime."""
import argparse
import os
import sys
from pathlib import Path
import xml.etree.ElementTree as ET

os.environ.setdefault("MPLCONFIGDIR", "/tmp/reconeval-runtime-review/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "runtime/02_foundation_model"

sys.path.insert(0, str(Path(__file__).parent))
from summarize_runtime import MODELS, LATENT_DIMS


def create_figure(
    include_se_runtime=False,
    *,
    flops_dir=RESULTS / "flops",
    manifest_path=RESULTS / "complexity/run_manifest.csv",
    runtime_csv=RESULTS / "measurements/complexity_runtime.csv",
):
    grid = pd.read_csv(flops_dir / "grid.csv")
    models = [m for m in MODELS if m in set(grid.model)]

    if include_se_runtime:
        # Match the plotting area in the FM cell-count figure.
        reference = ET.parse(RESULTS / "figures/luca_runtime_fm.svg").find(
            ".//{*}clipPath/{*}rect")
        panel_width = float(reference.attrib["width"]) / 72
        panel_height = float(reference.attrib["height"]) / 72
        fig, axes = plt.subplots(1, 2, figsize=(10, panel_height + 1.1))
        fig.subplots_adjust(left=0.06, right=0.98,
                            bottom=0.8 / (panel_height + 1.1),
                            top=1 - 0.3 / (panel_height + 1.1),
                            wspace=(9.2 - 2 * panel_width) / panel_width)
    else:
        fig, axes = plt.subplots(1, 1, figsize=(5, 4), layout="constrained", squeeze=False)
        axes = axes.ravel()

    ax = axes[-1]
    for model in models:
        rows = grid[grid.model == model].sort_values(["hidden_dim", "depth"])
        color, marker = MODELS[model]
        name = "SCimilarity" if model == "scimilarity" else model
        ax.plot(range(len(rows)), rows.train_val_dense_tflops_per_epoch,
                color=color, marker=marker, label=f"{name} (latent {rows.latent_dim.iloc[0]})")
    ax.set(yscale="log", xlabel="Hidden width × depth",
           ylabel="TFLOPs per epoch", title="Decoder FLOPs")
    ax.set_xticks(
        range(len(rows)), [f"{h}×{d}" for h, d in zip(rows.hidden_dim, rows.depth)],
        rotation=90, fontsize=8,
    )
    ax.set_yticks([20, 50, 100, 200, 500], ["20", "50", "100", "200", "500"])
    ax.yaxis.set_minor_formatter(NullFormatter())
    ax.legend(loc="upper left", frameon=False)

    if include_se_runtime:
        from plot_se_time_vs_flops_per_epoch import load_summary
        ax = axes[0]
        x, mean, sd = zip(*load_summary(flops_path=flops_dir / "grid.csv",
                                        runtime_csv=runtime_csv))
        color, marker = MODELS["SE"]
        ax.errorbar(x, mean, yerr=sd, color=color, marker=marker,
                    capsize=3, linewidth=1.7, markersize=6, label="MLP")
        ax.set(
            xscale="log", xlim=(min(x) * 0.9, 500),
            xlabel="TFLOPs per epoch", ylabel="Time per epoch (s)",
            title=f"Decoder training (MLP, latent {LATENT_DIMS['SE']})",
        )
        ax.set_xticks([20, 50, 100, 200, 500], ["20", "50", "100", "200", "500"])
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.margins(y=0.15)
        ax.legend(loc="upper left", frameon=False)

    for ax in axes:
        ax.title.set_fontsize(12)
        ax.grid(linestyle="--", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_axisbelow(True)
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--include-se-runtime", action="store_true",
                        help="Add SE runtime as the first panel and save a combined figure.")
    parser.add_argument("--flops-dir", type=Path, default=RESULTS / "flops")
    parser.add_argument("--manifest", type=Path,
                        default=RESULTS / "complexity/run_manifest.csv")
    parser.add_argument("--runtime-csv", type=Path,
                        default=RESULTS / "measurements/complexity_runtime.csv")
    parser.add_argument("--figure-dir", type=Path, default=RESULTS / "figures")
    args = parser.parse_args()

    args.figure_dir.mkdir(parents=True, exist_ok=True)
    fig = create_figure(
        include_se_runtime=args.include_se_runtime,
        flops_dir=args.flops_dir,
        manifest_path=args.manifest,
        runtime_csv=args.runtime_csv,
    )
    name = "decoder_flops_with_se_runtime" if args.include_se_runtime else "decoder_flops"
    path = args.figure_dir / f"{name}.svg"
    fig.savefig(path)
    print(path)
    plt.close(fig)


if __name__ == "__main__":
    main()
