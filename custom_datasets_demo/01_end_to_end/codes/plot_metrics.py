"""Save all demo distributional metrics in one four-panel SVG.

Run from the repository root after evaluate.sbatch completes.
Each point is the unweighted mean over evaluated combinations; NaNs are omitted.
"""

import argparse
from pathlib import Path

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt
import numpy as np
import pandas as pd


MODELS = {"PCA": ("#ffbf00", "D"), "mlAE": ("#2171b5", "^"), "nlscVI": ("#ae017e", "P")}
LATENTS = [10, 32, 128]
METRICS = {
    "r2_score": "R² (higher is better)",
    "mse": "MSE (lower is better)",
    "mmd_rbf": "MMD RBF (lower is better)",
    "energy_distance": "Energy distance (lower is better)",
}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--results-dir", type=Path, default=Path("results/luca-demo"))
    args = parser.parse_args()
    records = []
    for model in MODELS:
        for latent in LATENTS:
            path = args.results_dir / model / str(latent) / "distributional.csv"
            frame = pd.read_csv(path)
            for metric in METRICS:
                values = pd.to_numeric(frame[metric], errors="raise")
                if np.isinf(values).any() or values.notna().sum() == 0:
                    raise ValueError(f"No usable finite summary for {metric} in {path}")
                records.append({
                    "model": model, "latent": latent, "metric": metric,
                    "mean": values.mean(),
                })
    summary = pd.DataFrame(records)
    output = args.results_dir / "plots"
    output.mkdir(parents=True, exist_ok=True)

    def draw(ax, metric):
        for model, (color, marker) in MODELS.items():
            rows = summary[(summary.model == model) & (summary.metric == metric)]
            ax.plot(rows.latent, rows["mean"], color=color, marker=marker,
                    linewidth=1.5, markersize=6, label=model)
        ax.set(xticks=LATENTS, xlabel="Latent dimension",
               ylabel=METRICS[metric], title="LuCA demo")
        ax.grid(linestyle="--", alpha=0.3)
        ax.spines[["top", "right"]].set_visible(False)
        ax.legend(frameon=False)

    fig, axes = plt.subplots(2, 2, figsize=(11, 7.6), layout="constrained")
    for ax, metric in zip(axes.flat, METRICS):
        draw(ax, metric)
    output_path = output / "scaling_latent_distributional.svg"
    fig.savefig(output_path)
    plt.close(fig)
    print(f"Saved all four metrics to {output_path}")


if __name__ == "__main__":
    main()
