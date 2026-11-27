"""Collect LuCA training runtimes into CSV tables and one log-log plot.

Run from the repository root after train.sbatch completes.
Only successful runs enter the summary and plot; failed runs stay in runtime.csv.
Also refresh complexity_runtime.csv from both complexity manifests.
"""

import argparse
import json
from pathlib import Path
import re
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd


ROOT = Path(__file__).resolve().parents[3]


MODELS = {"PCA": ("#ffbf00", "D"), "mlAE": ("#2171b5", "^"), "nlscVI": ("#ae017e", "P")}
LABELS = {"PCA": "PCA", "mlAE": "AE", "nlscVI": "VAE"}
LATENTS = [10, 32, 128, 512, 2048]
FULL_CELLS = 892296


def epochs(log_path):
    """Final W&B epoch (zero-based) + 1; None for PCA or missing logs."""
    if not log_path.is_file():
        return None
    found = re.findall(r"wandb:\s+epoch\s+(\d+)", log_path.read_text(errors="replace"))
    return int(found[-1]) + 1 if found else None


def collect_complexity():
    """Refresh the existing complexity table from both run manifests."""
    manifest_dir = ROOT / "runtime/01_end_to_end/complexity"
    manifest = pd.concat([
        pd.read_csv(manifest_dir / "fixed_latent_2048/run_manifest.csv"),
        pd.read_csv(manifest_dir / "run_manifest.csv"),
    ]).drop_duplicates("run_dir")
    records = []
    for run in manifest.to_dict("records"):
        directory = ROOT / run["run_dir"]
        runtime_path = directory / "runtime.json"
        if not runtime_path.is_file():
            warnings.warn(f"Skipping missing complexity record: {runtime_path}")
            continue
        record = json.loads(runtime_path.read_text())
        records.append({
            **{key: run[key] for key in ("model", "latent_dim", "hidden_dim", "depth", "repeat")},
            "n_train": record["n_train"], "epochs": epochs(directory / "train.log"),
            "seconds": record.get("seconds", record["end"] - record["start"]),
            "exit_code": record["exit_code"],
            "gpu": record["gpu"], "run_dir": run["run_dir"],
        })
    return pd.DataFrame(records)


def create_figure(summary):
    """Return the runtime log-log figure (one panel per latent dimension)."""
    fig, axes = plt.subplots(1, len(LATENTS), figsize=(4 * len(LATENTS), 4),
                             sharey=True, layout="constrained")
    for ax, latent in zip(axes, LATENTS):
        for model, (color, marker) in MODELS.items():
            rows = summary[(summary.model == model) & (summary.latent_dim == latent)]
            ax.errorbar(rows.n_cells, rows.mean_seconds, yerr=rows.std_seconds,
                        color=color, marker=marker, capsize=3, label=LABELS[model])
        ax.set(xscale="log", yscale="log", xlabel="Number of cells",
               title=f"Latent dimension {latent}")
        ax.grid(linestyle="--", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Total time (s)")
    axes[0].legend(frameon=False, loc="lower right")
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results/luca-runtime",
                        help="Original raw run records; read only.")
    parser.add_argument("--measurements-dir", type=Path,
                        default=ROOT / "runtime/01_end_to_end/measurements")
    parser.add_argument("--figure-dir", type=Path,
                        default=ROOT / "runtime/01_end_to_end/figures")
    args = parser.parse_args()
    args.measurements_dir.mkdir(parents=True, exist_ok=True)
    args.figure_dir.mkdir(parents=True, exist_ok=True)

    # Complexity records
    complexity = collect_complexity()
    if not complexity.empty:
        complexity.to_csv(args.measurements_dir / "complexity_runtime.csv", index=False)
    else:
        print("No complexity records available; existing complexity CSV left unchanged.")
    print(f"Collected {len(complexity)} complexity run records")

    # Per-run runtimes
    records = []
    for path in sorted(args.results_dir.glob("runs/*/*/*/repeat-*/runtime.json")):
        record = json.loads(path.read_text())
        record["seconds"] = record.pop("end") - record.pop("start")
        record["epochs"] = epochs(path.parent / "train.log")
        records.append(record)
    if not records:
        raise SystemExit(f"No runtime.json files under {args.results_dir / 'runs'}")

    runs = pd.DataFrame(records)
    runs["n_cells"] = runs.n_cells.replace("full", FULL_CELLS).astype(int)
    runs = runs.sort_values(["model", "n_cells", "latent_dim", "repeat"])
    runs.to_csv(args.measurements_dir / "runtime.csv", index=False)

    ok = runs[runs.exit_code == 0]
    summary = (
        ok.groupby(["model", "n_cells", "latent_dim"])
          .agg(n_train=("n_train", "first"), n_runs=("seconds", "size"),
               mean_seconds=("seconds", "mean"), std_seconds=("seconds", "std"),
               mean_epochs=("epochs", "mean"))
          .reset_index()
    )
    summary.to_csv(args.measurements_dir / "runtime_summary.csv", index=False)
    print(f"Successful runs: {len(ok)}/{len(runs)}")
    print(summary.to_string(index=False))

    # Figure
    fig = create_figure(summary)
    output_path = args.figure_dir / "luca_runtime.svg"
    fig.savefig(output_path)
    plt.close(fig)
    print(f"Wrote {args.measurements_dir}/runtime{{,_summary}}.csv and {output_path}")


if __name__ == "__main__":
    main()
