# End-to-end runtime

**PCA · AE · VAE | LuCA | 3 repeats | H100**

| Folder | Purpose |
| --- | --- |
| [measurements/](measurements/) | Timing CSVs |
| [flops/](flops/) | FLOP grids |
| [figures/](figures/) | Plots |
| [complexity/](complexity/README.md) | Width × depth |
| [submit/](submit/) | Training / FLOP jobs |

**Inputs (repo paths):** `data/luca/runtime/`, `results/luca-runtime*`.
**Timing:** wall time, including loading/checkpoints.
**FLOPs:** AE/VAE full train+val epoch; PCA fit only.

**Refresh (repository root):**

```bash
# Logs → CSVs + cell-count plot
python runtime/01_end_to_end/codes/summarize_runtime.py
# CSVs → FLOP plots
python runtime/01_end_to_end/codes/plot_time_vs_flops.py
python runtime/01_end_to_end/codes/plot_flops_with_pca.py --reuse-pca-estimates
```

**Slurm image:** `RECONEVAL_IMAGE`. **Estimates:** [notebook and tables](../estimates/README.md).
