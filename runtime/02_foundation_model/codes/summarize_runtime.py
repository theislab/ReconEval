"""Collect LuCA foundation-model runtimes into CSV tables and one log-log plot.

Run from the repository root after embed.sbatch and decoder.sbatch complete.
Only successful runs enter the summaries and plot; failed runs stay in the
per-run tables (embed_runtime.csv, decoder_runtime.csv).
Also refresh complexity_runtime.csv from the SE decoder manifest.
"""

import argparse
import json
import os
from pathlib import Path
import re
import warnings

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import pandas as pd

ROOT = Path(__file__).resolve().parents[3]


# Panel and legend order follows the saved embedding widths, smallest first.
MODELS = {
    "scimilarity": ("#e7298a", "D"),  # 128
    "scGPT": ("#d95f02", "s"),       # 512
    "scConcept": ("#7570b3", "^"),   # 512
    "Geneformer": ("#a6761d", "X"),  # 1152
    "UCE": ("#e6ab02", "P"),         # 1280
    "SE": ("#1b9e77", "o"),          # 2058
    "scFoundation": ("#1f78b4", "v"), # 3072
}
LATENT_DIMS = {
    "scimilarity": 128, "scGPT": 512, "scConcept": 512,
    "Geneformer": 1152, "UCE": 1280, "SE": 2058, "scFoundation": 3072,
}
HIDDEN_COLORS = {1024: "#a6bddb", 2048: "#3690c0", 4096: "#034e7b"}
LAYER_MARKERS = {1: "o", 2: "s", 3: "^", 4: "D"}
FULL_CELLS = 892296


def collect_workload(directory, record):
    """Read decoder step counts; archived training batches are all full batches."""
    empty = dict.fromkeys(
        ["n_val", "train_cells_per_epoch", "val_cells_per_epoch",
         "train_batches_per_epoch", "val_batches_per_epoch"],
        float("nan"),
    )
    if record["exit_code"] != 0 or record.get("epochs", 0) <= 0:
        return empty
    try:
        log = (directory / "decoder.log").read_text()
        config = (directory / "MLP/config.yaml").read_text()
        batch_size = int(re.findall(r"^batch_size:\s*(\d+)", config, re.M)[0])
        last_epoch, global_steps = map(int, re.findall(r"Epoch (\d+), global step (\d+)", log)[-1])
        epochs = record["epochs"]
        if last_epoch + 1 != epochs:
            raise ValueError("Incomplete decoder log")
        n_val = int(re.findall(r"Val: X\((\d+),", log)[0])
        val_batches = max(map(int, re.findall(r"Validation DataLoader 0:.*?\|\s*(\d+)/", log)))
        return dict(
            n_val=n_val,
            train_cells_per_epoch=global_steps * batch_size / epochs,
            val_cells_per_epoch=min(n_val, val_batches * batch_size),
            train_batches_per_epoch=global_steps / epochs,
            val_batches_per_epoch=val_batches,
        )
    except (OSError, ValueError, IndexError) as error:
        warnings.warn(f"Workload unavailable for {directory}: {error}")
        return empty


def load(pattern, results_dir, with_workload=False):
    """Load all runtime.json files matching *pattern* under *results_dir*."""
    records = []
    for path in sorted(results_dir.glob(pattern)):
        record = json.loads(path.read_text())
        if with_workload:
            record["run_dir"] = os.path.relpath(path.parent, ROOT)
            record.update(collect_workload(path.parent, record))
        records.append(record)
    if not records:
        raise SystemExit(f"No runtime.json files matching {results_dir / pattern}")
    runs = pd.DataFrame(records)
    runs["n_cells"] = runs.n_cells.replace("full", FULL_CELLS).astype(int)
    return runs


def summarize(runs, keys, columns):
    """Aggregate runtime runs: mean and std of each column, grouped by keys."""
    agg = {"n_train": ("n_train", "first"), "n_runs": (columns[0], "size")}
    agg.update({f"mean_{c}": (c, "mean") for c in columns})
    agg.update({f"std_{c}":  (c, "std")  for c in columns})
    return runs.groupby(keys).agg(**agg).reset_index()


def collect_complexity():
    """Refresh the existing SE complexity table from its run manifest."""
    manifest = pd.read_csv(ROOT / "runtime/02_foundation_model/complexity/run_manifest.csv")
    records = []
    for run in manifest.to_dict("records"):
        directory = ROOT / run["run_dir"]
        runtime_path = directory / "runtime.json"
        if not runtime_path.is_file():
            warnings.warn(f"Skipping missing complexity record: {runtime_path}")
            continue
        record = json.loads(runtime_path.read_text())
        records.append({
            "model": run["model"], "latent_dim": run["latent_dim"],
            "hidden_dim": run["n_hidden"], "depth": run["n_layers"],
            "repeat": run["repeat"], "n_train": record["n_train"],
            "epochs": record["epochs"], "seconds": record["end"] - record["start"],
            "exit_code": record["exit_code"], "gpu": record["gpu"], "run_dir": run["run_dir"],
            **collect_workload(directory, record),
        })
    return pd.DataFrame(records)


def create_figure(embed_summary, decoder_summary):
    """Return the runtime log-log figure (one embed panel + one decoder panel per FM)."""
    fig, axes = plt.subplots(2, 4, figsize=(18, 8), sharey=True, layout="constrained")
    axes = axes.ravel()

    for model, (color, marker) in MODELS.items():
        rows = embed_summary[embed_summary.model == model]
        axes[0].errorbar(rows.n_cells, rows.mean_embed_seconds, yerr=rows.std_embed_seconds,
                         color=color, marker=marker, capsize=3,
                         label="SCimilarity" if model == "scimilarity" else model)
    axes[0].set_title("Embedding extraction")
    axes[0].legend(frameon=False)

    for ax, model in zip(axes[1:], MODELS):
        name = "SCimilarity" if model == "scimilarity" else model
        for (n_layers, n_hidden), rows in decoder_summary[decoder_summary.model == model].groupby(
                ["n_layers", "n_hidden"]):
            ax.errorbar(rows.n_cells, rows.mean_decoder_seconds, yerr=rows.std_decoder_seconds,
                        color=HIDDEN_COLORS[n_hidden], marker=LAYER_MARKERS[n_layers],
                        capsize=3, label=f"{n_layers}x{n_hidden}")
        ax.set_title(f"Decoder training ({name}, latent {LATENT_DIMS[model]})")
        if model == "scConcept":
            ax.legend(frameon=False, fontsize="small", ncols=1, loc="upper right")

    for ax in axes:
        ax.set(xscale="log", yscale="log", xlabel="Number of cells")
        ax.grid(linestyle="--", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
    axes[0].set_ylabel("Total time (s)")
    return fig


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=ROOT / "results/luca-runtime-fm",
                        help="Original raw run records; read only.")
    parser.add_argument("--measurements-dir", type=Path,
                        default=ROOT / "runtime/02_foundation_model/measurements")
    parser.add_argument("--figure-dir", type=Path,
                        default=ROOT / "runtime/02_foundation_model/figures")
    args = parser.parse_args()
    args.measurements_dir.mkdir(parents=True, exist_ok=True)
    args.figure_dir.mkdir(parents=True, exist_ok=True)
    out = args.measurements_dir

    # Complexity (SE decoder) records
    complexity = collect_complexity()
    if not complexity.empty:
        complexity.to_csv(out / "complexity_runtime.csv", index=False)
    else:
        print("No complexity records available; existing complexity CSV left unchanged.")
    print(f"Collected {len(complexity)} SE complexity run records")

    # Embedding runtimes
    embed = load("embed/*/*/repeat-*/runtime.json", args.results_dir)
    embed["embed_seconds"]   = embed["embedded"] - embed["start"]
    embed["combine_seconds"] = embed["end"]      - embed["embedded"]
    embed = embed.drop(columns=["start", "embedded", "end"])
    embed = embed.sort_values(["model", "n_cells", "repeat"])
    embed.to_csv(out / "embed_runtime.csv", index=False)
    embed_ok      = embed[embed.exit_code == 0]
    embed_summary = summarize(embed_ok, ["model", "n_cells"], ["embed_seconds", "combine_seconds"])
    embed_summary.to_csv(out / "embed_runtime_summary.csv", index=False)
    print(f"Successful embedding runs: {len(embed_ok)}/{len(embed)}")
    print(embed_summary.to_string(index=False))

    # Decoder runtimes
    decoder = load("decoder/*/*/*/repeat-*/runtime.json", args.results_dir, with_workload=True)
    decoder["decoder_seconds"]   = decoder["end"] - decoder["start"]
    decoder["seconds_per_epoch"] = decoder["decoder_seconds"] / decoder["epochs"].where(decoder["epochs"] > 0)
    decoder = decoder.drop(columns=["start", "end"])
    decoder = decoder.sort_values(["model", "n_cells", "n_layers", "n_hidden", "repeat"])
    decoder.to_csv(out / "decoder_runtime.csv", index=False)
    decoder_ok      = decoder[decoder.exit_code == 0]
    decoder_summary = summarize(decoder_ok, ["model", "n_cells", "n_layers", "n_hidden"],
                                ["decoder_seconds", "epochs", "seconds_per_epoch"])
    decoder_summary.to_csv(out / "decoder_runtime_summary.csv", index=False)
    print(f"\nSuccessful decoder runs: {len(decoder_ok)}/{len(decoder)}")
    print(decoder_summary.to_string(index=False))

    # Figure
    fig = create_figure(embed_summary, decoder_summary)
    output_path = args.figure_dir / "luca_runtime_fm.svg"
    fig.savefig(output_path)
    plt.close(fig)
    print(f"\nWrote {out}/{{embed,decoder}}_runtime{{,_summary}}.csv and {output_path}")


if __name__ == "__main__":
    main()
