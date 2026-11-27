"""Print and save mean metrics for the foundation-model demo runs.

Run from the repository root after evaluate.sbatch completes.
Each evaluated test group has equal weight. The table is printed to the terminal
and saved to summary.csv in the results directory, with four decimal places
and rows sorted by descending R².
"""

import argparse
import csv
import math
from pathlib import Path
from statistics import mean


MODELS = ("SE", "scGPT", "scConcept", "scimilarity", "Geneformer", "UCE", "scFoundation")
METRICS = ("r2_score", "mse", "mmd_rbf", "energy_distance")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--results-dir", type=Path, default=Path("results/luca-demo/fm")
    )
    args = parser.parse_args()

    summaries = []
    for model in MODELS:
        path = args.results_dir / model / "distributional.csv"
        with path.open(newline="", encoding="utf-8") as handle:
            rows = list(csv.DictReader(handle))
        if not rows:
            raise ValueError(f"No metric rows in {path}")

        means = []
        for metric in METRICS:
            values = [float(row[metric]) for row in rows]
            if not all(math.isfinite(value) for value in values):
                raise ValueError(f"Non-finite values for {metric} in {path}")
            means.append(mean(values))
        summaries.append((model, means))

    summaries.sort(key=lambda row: row[1][0], reverse=True)

    summary_path = args.results_dir / "summary.csv"
    with summary_path.open("w", newline="", encoding="utf-8") as handle:
        writer = csv.writer(handle)
        writer.writerow(["Model", "R² (↑)", "MSE (↓)", "MMD (↓)", "Energy distance (↓)"])
        for model, values in summaries:
            writer.writerow([model, *(f"{value:.4f}" for value in values)])

    print("Mean metrics across test groups (equal weight per group)")
    print(
        f"{'Model':<14} {'R² (↑)':>10} {'MSE (↓)':>10} {'MMD (↓)':>10} {'Energy distance (↓)':>19}"
    )
    for model, values in summaries:
        r2, mse, mmd, energy = values
        print(f"{model:<14} {r2:>10.4f} {mse:>10.4f} {mmd:>10.4f} {energy:>19.4f}")
    print("Higher R² is better; lower MSE, MMD, and energy distance are better.")
    print(f"Saved summary table to {summary_path}")


if __name__ == "__main__":
    main()
