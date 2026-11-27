"""Prepare selected architectures, FLOPs and references to existing runtime runs.

Run from the repository root: python runtime/01_end_to_end/complexity/codes/prepare.py
Only uses the standard library; does not train models or copy checkpoints.
"""

import argparse
import csv
from collections import defaultdict
import json
from pathlib import Path
import re
from statistics import mean, stdev


ROOT = Path(__file__).resolve().parents[4]
BENCHMARK = ROOT / "runtime/01_end_to_end/complexity/fixed_latent_2048"
RESULTS = ROOT / "runtime/01_end_to_end"
OUTPUT = RESULTS / "complexity/fixed_latent_2048"


def load_config(benchmark_dir=BENCHMARK):
    return json.loads((Path(benchmark_dir) / "configs/benchmark.json").read_text())


def architecture_overrides(model, setting):
    latent, hidden, depth = (setting[k] for k in ("latent_dim", "hidden_dim", "depth"))
    if model == "mlAE":
        widths = "[" + ",".join([str(hidden)] * depth) + "]"
        return [f"model.model_args.n_hidden={widths}", f"model.model_args.n_latent={latent}"]
    if model == "nlscVI":
        return [f"model.model_args.n_hidden={hidden}", f"model.model_args.n_layers={depth}",
                f"model.model_args.n_latent={latent}"]
    raise ValueError(f"Unknown model: {model}")


def planned_runs(config):
    task_id = 0
    for model in config["models"]:
        for setting in config["configurations"]:
            latent, hidden, depth = (setting[k] for k in ("latent_dim", "hidden_dim", "depth"))
            for repeat in range(1, config["repeats"] + 1):
                reused = setting["reuse_existing"]
                directory = (f"{config['existing_runtime_dir']}/{model}/full/{latent}/repeat-{repeat}"
                             if reused else
                             f"{config['results_dir']}/runs/{model}/full/{latent}_{hidden}_{depth}/repeat-{repeat}")
                if "run_dir" in setting:
                    directory = setting["run_dir"].format(model=model, repeat=repeat)
                yield dict(task_id="" if reused else task_id, model=model,
                           latent_dim=latent, hidden_dim=hidden, depth=depth,
                           repeat=repeat, source="existing" if reused else "new",
                           run_dir=directory)
                if not reused:
                    task_id += 1


def existing_result(run, config):
    directory = ROOT / run["run_dir"]
    record = json.loads((directory / "runtime.json").read_text())
    for key in ("model", "latent_dim", "repeat"):
        if record[key] != run[key]:
            raise ValueError(f"{directory}: mismatched {key}")
    if record["exit_code"] != 0 or record["n_cells"] != "full" or record["n_train"] != config["n_train"]:
        raise ValueError(f"{directory}: not a successful full-data run")
    # Check the actual saved architecture, rather than inferring it from the path.
    overrides = {line.removeprefix("- ").strip()
                 for line in (directory / "hydra/.hydra/overrides.yaml").read_text().splitlines()}
    required = architecture_overrides(run["model"], run) + [
        f"seed={config['seed']}", f"data.path={config['data_dir']}"]
    if not set(required).issubset(overrides):
        raise ValueError(f"{directory}: saved configuration differs from the benchmark")
    found = re.findall(r"wandb:\s+epoch\s+(\d+)",
                       (directory / "train.log").read_text(errors="replace"))
    return dict(model=run["model"], latent_dim=run["latent_dim"],
                hidden_dim=run["hidden_dim"], depth=run["depth"], repeat=run["repeat"],
                seconds=record["end"] - record["start"],
                epochs=int(found[-1]) + 1 if found else "",
                gpu=record["gpu"], runtime_json=f"{run['run_dir']}/runtime.json")


def write_csv(path, rows):
    with path.open("w", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--benchmark-dir", type=Path, default=BENCHMARK,
                        help="Benchmark configuration directory; read only.")
    parser.add_argument("--flops-dir", type=Path, default=RESULTS / "flops")
    parser.add_argument("--output-dir", type=Path, default=OUTPUT,
                        help="Destination for the manifest and selected FLOP/summary tables.")
    args = parser.parse_args()
    config = load_config(args.benchmark_dir)
    runs = list(planned_runs(config))
    baseline = [existing_result(run, config) for run in runs if run["source"] == "existing"]
    # Reuse the counted grid; preparing the run manifest needs no PyTorch/GPU.
    grid_path = args.flops_dir / "grid.csv"
    metadata = json.loads(grid_path.with_name("metadata.json").read_text())
    if metadata.get("method") != "FlopCounterMode" or any(
            metadata.get(k) != config[k] for k in ("n_genes", "n_train", "n_val")):
        raise ValueError(f"Regenerate {grid_path} with FlopCounterMode and matching data dimensions")
    with grid_path.open() as handle:
        grid = {(row["model"], *(int(row[k]) for k in ("latent_dim", "hidden_dim", "depth"))): row
                for row in csv.DictReader(handle)}
    flop_rows = []
    for model in config["models"]:
        for setting in config["configurations"]:
            key = (model, *(setting[k] for k in ("latent_dim", "hidden_dim", "depth")))
            if key not in grid:
                raise ValueError(f"Missing architecture {key}; regenerate {grid_path}")
            row = grid[key]
            flop_rows.append(row)
    baseline_groups = defaultdict(list)
    for row in baseline:
        key = tuple(row[k] for k in ("model", "latent_dim", "hidden_dim", "depth"))
        baseline_groups[key].append(row)
    summaries = []
    for (model, latent, hidden, depth), rows in baseline_groups.items():
        seconds = [r["seconds"] for r in rows]
        summaries.append(dict(model=model, latent_dim=latent, hidden_dim=hidden, depth=depth,
                              n_runs=len(rows), mean_seconds=mean(seconds),
                              std_seconds=stdev(seconds)))
    args.output_dir.mkdir(parents=True, exist_ok=True)
    write_csv(args.output_dir / "run_manifest.csv", runs)
    write_csv(args.output_dir / "existing_runs.csv", baseline)
    write_csv(args.output_dir / "existing_summary.csv", summaries)
    write_csv(args.output_dir / "flops.csv", flop_rows)
    print(f"{len(runs)} runs: {len(baseline)} existing, {len(runs) - len(baseline)} new")
    print(f"Verified existing architectures and wrote tables to {args.output_dir}")


if __name__ == "__main__":
    main()
