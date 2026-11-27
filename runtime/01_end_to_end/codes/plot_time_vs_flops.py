"""Plot neural training time and PCA runtime against their FLOP estimates.

Uses the selected architectures and their existing runtime repeats.
Time is full-run wall time, including startup and checkpoints.
Per-epoch time is full-run wall time divided by completed epochs.
PCA uses fit-only FLOPs and full-run wall time; it has no epochs.
The default study fixes latent dimension at 2048, including its three PCA runs.
Error bars show sample SD: across repeats for each neural configuration,
including the three selected PCA repeats, not uncertainty in the FLOP count.
A broken log x-axis separates PCA from neural models without moving points.
Time per epoch or PCA fit uses a linear y-axis.
"""
import argparse
import json
import os
import sys
from pathlib import Path

os.environ.setdefault("MPLCONFIGDIR", "/tmp/reconeval-runtime-review/matplotlib")
import matplotlib
matplotlib.use("Agg")
import matplotlib.pyplot as plt
from matplotlib.ticker import NullFormatter, NullLocator
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "runtime/01_end_to_end"
BENCHMARK = ROOT / "runtime/01_end_to_end/complexity/fixed_latent_2048"
FLOPS_DIR = RESULTS / "flops"

sys.path.insert(0, str(Path(__file__).parent))
from summarize_runtime import MODELS, LABELS, LATENTS, FULL_CELLS

KEYS = ["model", "latent_dim", "hidden_dim", "depth"]
FLOPS = "train_val_dense_tflops_per_epoch"


def load_neural_runs(manifest, metadata, runtime_csv):
    """Join preserved measurements; run_dir is a provenance identifier only."""
    measurements = pd.read_csv(runtime_csv)
    keys = [*KEYS, "repeat", "run_dir"]
    runs = manifest.merge(measurements, on=keys, how="left", validate="one_to_one")
    assert (runs.exit_code == 0).all(), "Missing or unsuccessful measurements"
    assert (runs.gpu == metadata["gpu"]).all()
    assert (runs.n_train == metadata["n_train"]).all()
    assert (runs.epochs > 0).all() and (runs.seconds > 0).all()
    return runs[[*manifest.columns, "seconds", "epochs", "gpu"]]


def load_pca(config, metadata, latents=None, *, flops_dir=FLOPS_DIR,
             runtime_csv=RESULTS / "measurements/runtime.csv"):
    report = json.loads((flops_dir / "pca_flops_estimate.json").read_text())
    assert report["include_transform"] is False
    estimates = pd.read_csv(flops_dir / "pca_flops.csv")
    estimates = estimates[estimates.eigh_method == report["plot_eigh_method"]]
    estimates = estimates.set_index("latent_dim", verify_integrity=True)
    assert set(estimates.index) == set(LATENTS)
    assert (estimates.n_cells == metadata["n_train"]).all()
    assert (estimates.n_genes == metadata["n_genes"]).all()
    assert (estimates.fit_flops == estimates.total_flops).all()
    timings = pd.read_csv(runtime_csv)
    timings = timings[(timings.model == "PCA") & (timings.n_cells == FULL_CELLS)]
    timings = timings.set_index(["latent_dim", "repeat"], verify_integrity=True)
    records = []
    for latent in (LATENTS if latents is None else latents):
        for repeat in range(1, config["repeats"] + 1):
            directory = (ROOT / config["existing_runtime_dir"] / "PCA" / "full"
                         / str(latent) / f"repeat-{repeat}")
            record = timings.loc[(latent, repeat)]
            assert record["exit_code"] == 0, directory
            assert record["gpu"] == metadata["gpu"], directory
            assert record["n_train"] == metadata["n_train"], directory
            records.append({
                "model": "PCA", "latent_dim": latent, "repeat": repeat,
                "source": "existing", "run_dir": str(directory.relative_to(ROOT)),
                "seconds": record["seconds"], "gpu": record["gpu"],
                "fit_tflops": estimates.loc[latent, "fit_tflops"],
            })
    runs = pd.DataFrame(records)
    assert (runs.seconds > 0).all() and (runs.fit_tflops > 0).all()
    assert runs.fit_tflops.nunique() == 1
    # Equal repeat counts give each latent dimension equal weight in this mean.
    summary = runs.groupby("model", as_index=False).agg(
        fit_tflops=("fit_tflops", "first"), n_runs=("seconds", "size"),
        n_latents=("latent_dim", "nunique"),
        mean_seconds=("seconds", "mean"), std_seconds=("seconds", "std"),
    )
    return runs, summary


def create_figure(summary, pca_summary, latent_dim=None):
    """Return the broken-axis time-vs-FLOPs figure.

    Left panel: single PCA point; right panel: neural errorbar curves.
    *latent_dim* is used only for the figure title.
    """
    fig, (pca_ax, neural_ax) = plt.subplots(
        1, 2, sharey=True, figsize=(8.5, 4.8), layout="constrained",
        gridspec_kw={"width_ratios": [1.1, 4.8], "wspace": 0.06},
    )
    if latent_dim is not None:
        fig.suptitle(f"Latent dimension {latent_dim}")

    for model, rows in summary.groupby("model", sort=False):
        rows = rows.sort_values("tflops_per_epoch")
        color, marker = MODELS[model]
        neural_ax.errorbar(rows.tflops_per_epoch, rows.mean_seconds_per_epoch,
                           yerr=rows.std_seconds_per_epoch, color=color, marker=marker,
                           capsize=3, linewidth=1.7, markersize=6,
                           label=f"{LABELS[model]} / epoch")
    color, marker = MODELS["PCA"]
    pca_ax.errorbar(pca_summary.fit_tflops, pca_summary.mean_seconds,
                    yerr=pca_summary.std_seconds, color=color, marker=marker,
                    linestyle="none", capsize=3, markersize=6,
                    label="PCA / fit (approx.)")

    for ax in (pca_ax, neural_ax):
        ax.set_xscale("log", base=10)
        ax.xaxis.set_minor_formatter(NullFormatter())
        ax.grid(linestyle="--", linewidth=0.7, alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
        ax.set_axisbelow(True)
    pca_ax.set(xlim=(1.12, 1.57), ylabel="Time per epoch or fit (s)")
    pca_ax.set_xticks([pca_summary.fit_tflops.iloc[0]],
                      [f"{pca_summary.fit_tflops.iloc[0]:.3f}"])
    pca_ax.xaxis.set_minor_locator(NullLocator())
    neural_ax.set_xlim(45, 900)
    neural_ax.set_xticks([50, 100, 200, 500], ["50", "100", "200", "500"])
    neural_ax.spines["left"].set_visible(False)
    neural_ax.tick_params(axis="y", which="both", left=False, labelleft=False)

    # Diagonal marks explicitly show the omitted x-range between panels.
    for ax, edge in ((pca_ax, 1), (neural_ax, 0)):
        ax.plot(edge, 0, transform=ax.transAxes, clip_on=False,
                marker=[(-1, -0.6), (1, 0.6)], markersize=11,
                linestyle="none", color="0.35", markeredgewidth=1)

    neural_handles, neural_labels = neural_ax.get_legend_handles_labels()
    pca_handles, pca_labels = pca_ax.get_legend_handles_labels()
    legend = fig.legend(neural_handles + pca_handles, neural_labels + pca_labels,
                        loc="upper left", bbox_to_anchor=(0, 1),
                        bbox_transform=pca_ax.transAxes, frameon=False)
    legend.set_in_layout(False)
    fig.supxlabel("TFLOPs", fontsize=10)
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=BENCHMARK,
                        help="Benchmark configuration directory; read only.")
    parser.add_argument("--benchmark-results-dir", type=Path,
                        default=RESULTS / "complexity/fixed_latent_2048",
                        help="Manifest and selected FLOP-table inputs.")
    parser.add_argument("--measurements-dir", type=Path,
                        default=RESULTS / "measurements/fixed_latent_2048")
    parser.add_argument("--figure-dir", type=Path,
                        default=RESULTS / "figures/fixed_latent_2048")
    parser.add_argument("--pca-flops-dir", type=Path, default=FLOPS_DIR)
    parser.add_argument("--runtime-dir", type=Path, default=RESULTS / "measurements",
                        help="Preserved runtime.csv and complexity_runtime.csv inputs.")
    parser.add_argument("--latent-dim", type=int, choices=LATENTS, default=2048)
    args = parser.parse_args()

    config = json.loads((args.benchmark_dir / "configs/benchmark.json").read_text())
    metadata = json.loads((args.pca_flops_dir / "metadata.json").read_text())
    manifest = pd.read_csv(args.benchmark_results_dir / "run_manifest.csv")
    if args.latent_dim is not None:
        manifest = manifest[manifest.latent_dim == args.latent_dim]
    if manifest.empty:
        parser.error("No matching runs in the selected benchmark")

    runs = load_neural_runs(manifest, metadata, args.runtime_dir / "complexity_runtime.csv")
    runs = runs.merge(pd.read_csv(args.benchmark_results_dir / "flops.csv"),
                      on=KEYS, how="left", validate="many_to_one")
    assert runs[FLOPS].notna().all()
    runs["seconds_per_epoch"] = runs.seconds / runs.epochs
    runs["seconds_per_tflop"] = runs.seconds_per_epoch / runs[FLOPS]
    runs["total_dense_tflops"] = runs[FLOPS] * runs.epochs
    summary = runs.groupby(KEYS, as_index=False).agg(
        tflops_per_epoch=(FLOPS, "first"), n_runs=("seconds", "size"),
        mean_epochs=("epochs", "mean"),
        mean_seconds=("seconds", "mean"), std_seconds=("seconds", "std"),
        mean_seconds_per_epoch=("seconds_per_epoch", "mean"),
        std_seconds_per_epoch=("seconds_per_epoch", "std"),
        mean_seconds_per_tflop=("seconds_per_tflop", "mean"),
        std_seconds_per_tflop=("seconds_per_tflop", "std"),
    )
    assert (summary.n_runs == config["repeats"]).all()

    latents = [args.latent_dim] if args.latent_dim is not None else None
    pca_runs, pca_summary = load_pca(config, metadata, latents, flops_dir=args.pca_flops_dir,
                                     runtime_csv=args.runtime_dir / "runtime.csv")

    args.measurements_dir.mkdir(parents=True, exist_ok=True)
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    # PCA has no epochs or neural architecture; those CSV fields stay empty.
    pd.concat([runs, pca_runs], ignore_index=True).to_csv(
        args.measurements_dir / "runtime_flops_runs.csv", index=False)
    pd.concat([summary, pca_summary], ignore_index=True).to_csv(
        args.measurements_dir / "runtime_flops_summary.csv", index=False)

    fig = create_figure(summary, pca_summary, latent_dim=args.latent_dim)
    for extension in ("png", "svg"):
        path = args.figure_dir / f"time_vs_flops_per_epoch.{extension}"
        fig.savefig(path, dpi=180)
        print(path)
    plt.close(fig)

    print(f"Used {len(runs)} successful runs across {len(summary)} model/configuration pairs.")
    print(f"PCA: one point averaging {len(pca_runs)} runs across "
          f"{pca_runs.latent_dim.nunique()} latent dimensions; "
          f"{pca_summary.mean_seconds.iloc[0]:.3f} ± "
          f"{pca_summary.std_seconds.iloc[0]:.3f} s (SD).")


if __name__ == "__main__":
    main()
