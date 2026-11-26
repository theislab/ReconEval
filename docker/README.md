# ReconEval container

Uses the root [envs/](../envs/) recipes. Run commands from the repository root.

## Build

Edit the Slurm settings, target, and paths in [build.sbatch](build.sbatch).
Keep `build_root` on node-local storage.

```bash
mkdir -p logs/slurm
sbatch docker/build.sbatch
```

Targets: `all` (default), `metrics`, `core`, `state`, `scgpt`, `scconcept`,
`scimilarity`, `cellflow`.

Exports `reconeval-<target>.tar` and `.sif` to `output_dir`.
Logs go to `logs/slurm/`.

STATE, scGPT, scConcept and CellFlow apply the matching `docker/*_overrides.yaml` to their copied recipes.
scGPT also uses [scgpt_requirements.txt](scgpt_requirements.txt) to preserve its Torch and NumPy versions.
Copied recipes replace `defaults` with `pytorch` to provide `pytorch-cuda` and avoid
the cluster's certificate error. The scGPT and scimilarity copies also add `nvidia` for CUDA libraries.
Repository YAMLs are unchanged.

## Run

Replace `reconeval` with the environment for your task.
Use `reconeval-state` for STATE and `reconeval-pancellflow` for CellFlow;
their scikit-learn requirements need separate environments.

**Apptainer**

```bash
apptainer exec --cleanenv --nv \
  --bind "$PWD:/work" --pwd /work \
  /path/to/reconeval-all.sif \
  conda run --no-capture-output -n reconeval python your_script.py
```

For Slurm GPU jobs, first run
`export APPTAINERENV_CUDA_VISIBLE_DEVICES="$CUDA_VISIBLE_DEVICES"`.

**Podman**

Requires node-local container storage and configured NVIDIA GPU support.

```bash
podman load -i /path/to/reconeval-all.tar
podman run --rm --gpus all \
  -v "$PWD:/work" -w /work localhost/reconeval:all \
  -n reconeval python your_script.py
```

For individual targets, use the matching image and tag. Omit `--nv` or
`--gpus all` for CPU runs. Add mounts for external data or models.
