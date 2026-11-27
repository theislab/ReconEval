"""Load SE decoder time-per-epoch summaries for the combined decoder figure."""
from pathlib import Path

import pandas as pd

ROOT = Path(__file__).resolve().parents[3]
RESULTS = ROOT / "runtime/02_foundation_model"


def load_summary(
    flops_path=RESULTS / "flops/grid.csv",
    runtime_csv=RESULTS / "measurements/complexity_runtime.csv",
):
    """Return sorted list of (tflops, mean_seconds_per_epoch, std_seconds_per_epoch).

    Reads the pre-validated complexity_runtime.csv built by summarize_runtime.py;
    no manifest cross-checks are needed here.
    """
    flops = (
        pd.read_csv(flops_path)
        .query("model == 'SE'")
        [["hidden_dim", "depth", "train_val_dense_tflops_per_epoch"]]
    )
    runs = (
        pd.read_csv(runtime_csv)
        .query("model == 'SE' and exit_code == 0 and epochs > 0")
    )
    runs["seconds_per_epoch"] = runs["seconds"] / runs["epochs"]
    df = runs.merge(flops, on=["hidden_dim", "depth"])

    grouped = df.groupby(["hidden_dim", "depth"])
    return sorted(
        (
            group["train_val_dense_tflops_per_epoch"].mean(),
            group["seconds_per_epoch"].mean(),
            group["seconds_per_epoch"].std(),
        )
        for _, group in grouped
    )
