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
`scimilarity`, `cellflow`, `geneformer`, `uce`, `scfoundation`.

Exports `reconeval-<target>.tar` and `.sif` to `output_dir`.
Logs go to `logs/slurm/`.

STATE, scGPT, scConcept and CellFlow apply the matching `docker/*_overrides.yaml` to their copied recipes.
scGPT also uses [scgpt_requirements.txt](scgpt_requirements.txt) to preserve its Torch and NumPy versions.
Copied recipes replace `defaults` with `pytorch` to provide `pytorch-cuda` and avoid
the cluster's certificate error. The scGPT and scimilarity copies also add `nvidia` for CUDA libraries.
Repository YAMLs are unchanged.

Geneformer, UCE and scFoundation use `envs/geneformer.txt`, `envs/uce.txt`
and `envs/scfoundation.txt`. The Python-version mapping in [setup.sh](setup.sh)
selects Python 3.10 for these environments and Python 3.12 for metrics.
The TXT files use `packaging>=23.0`; local source references from the exports
are replaced by installing ReconEval from `/opt/ReconEval` and model code below.

Geneformer, UCE and scFoundation code is pinned to upstream commits in
[setup.sh](setup.sh). UCE and scFoundation live in `/opt/foundation_models`
(override with `UCE_DIR` and `SCFOUNDATION_DIR`); Geneformer is installed as a package.
Their weights are not in the image; fetch them with
`experiments/02_foundation_model/codes/download_checkpoints.py`.

To add these three environments to an existing `reconeval-all.sif` without
rebuilding the others:

```bash
sbatch docker/add_fm_envs.sbatch /absolute/path/reconeval-all.sif
```

It writes `reconeval-all.fm-<jobid>.sif` next to the input and fails if any
existing environment's packages change.

## Run

Replace `reconeval` with the environment for your task.
Use `reconeval-state` for STATE and `reconeval-pancellflow` for CellFlow;
their scikit-learn requirements need separate environments. Use
`reconeval-geneformer`, `reconeval-uce` and `reconeval-scfoundation` for those models.

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
