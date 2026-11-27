"""Run one selected full-data training task, using the runtime protocol.

Preview without importing training dependencies or starting training:
    python runtime/01_end_to_end/complexity/codes/train_runtime.py 0 --dry-run
Run inside the existing reconeval container, normally via submit/train.sbatch.
"""

import argparse
import json
import os
from pathlib import Path
import shlex
import socket
import subprocess
import sys
import time

from prepare import BENCHMARK, ROOT, architecture_overrides, load_config, planned_runs


def training_command(run, config):
    run_dir = run["run_dir"]
    command = [
        sys.executable, "-u", "experiments/01_end_to_end/codes/train.py",
        "--config-dir", "runtime/01_end_to_end/configs",
        "data=luca_runtime", f"data.path={config['data_dir']}",
        f"seed={config['seed']}", f"weights.dir={run_dir}/weights",
        f"logging.dir={run_dir}/logs", f"hydra.run.dir={run_dir}/hydra",
        "trainer.accelerator=gpu", "+trainer.enable_progress_bar=false",
    ]
    if run["model"] == "mlAE":
        command += ["model=train/AE", "trainer=AE", "model.meta.name=mlAE",
                    "model.model_args.library_size_mode=modeled"]
    else:
        command += ["model=train/nlscVI", "trainer=scVI"]
    return command + architecture_overrides(run["model"], run)


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("task_id", type=int)
    parser.add_argument("--dry-run", action="store_true")
    parser.add_argument("--benchmark-dir", type=Path, default=BENCHMARK)
    args = parser.parse_args()
    config = load_config(args.benchmark_dir)
    tasks = {run["task_id"]: run for run in planned_runs(config) if run["source"] == "new"}
    if args.task_id not in tasks:
        parser.error(f"task_id must be between 0 and {max(tasks)}")
    run = tasks[args.task_id]
    command = training_command(run, config)
    print(json.dumps(run, indent=2), flush=True)
    print(shlex.join(command), flush=True)
    if args.dry_run:
        return

    directory = ROOT / run["run_dir"]
    result_path = directory / "runtime.json"
    if result_path.exists():
        result = json.loads(result_path.read_text())
        same = all(result.get(k) == run[k] for k in
                   ("model", "latent_dim", "hidden_dim", "depth", "repeat"))
        if same and result.get("exit_code") == 0:
            print(f"Already finished: {directory}")
            return
    if directory.exists():
        raise SystemExit(f"Existing unfinished run: {directory}. Move it aside before retrying.")

    # Match the existing data and GPU protocol; checks are outside the timer.
    import zarr

    for split, count in (("train", config["n_train"]), ("val", config["n_val"])):
        shape = zarr.open(str(ROOT / config["data_dir"] / f"{split}.zarr"), mode="r")["X"].shape
        if tuple(shape) != (count, config["n_genes"]):
            raise SystemExit(f"Unexpected {split} shape: {shape}")
    gpu = subprocess.check_output(
        ["nvidia-smi", "--query-gpu=name", "--format=csv,noheader"], text=True).splitlines()[0]
    directory.mkdir(parents=True)
    environment = dict(os.environ, WANDB_MODE="offline")
    with (directory / "train.log").open("w") as handle:
        start = time.time()
        timer = time.perf_counter()
        completed = subprocess.run(command, cwd=ROOT, env=environment,
                                   stdout=handle, stderr=subprocess.STDOUT)
        seconds = time.perf_counter() - timer
        end = time.time()
    record = dict(run, n_cells="full", n_train=config["n_train"], n_val=config["n_val"],
                  n_genes=config["n_genes"], batch_size=config["batch_size"], seed=config["seed"],
                  protocol="full_training", start=start, end=end, seconds=seconds,
                  exit_code=completed.returncode, gpu=gpu, host=socket.gethostname(),
                  slurm_job=f"{os.environ.get('SLURM_ARRAY_JOB_ID', '')}_{os.environ.get('SLURM_ARRAY_TASK_ID', '')}",
                  command=command)
    result_path.write_text(json.dumps(record, indent=2) + "\n")
    print(json.dumps(record, indent=2))
    raise SystemExit(completed.returncode)


if __name__ == "__main__":
    main()
