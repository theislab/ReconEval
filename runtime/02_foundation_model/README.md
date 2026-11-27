# Foundation-model runtime

**Embeddings + MLP | LuCA | 7 FMs | 3 repeats | H100**

| Folder | Purpose |
| --- | --- |
| [measurements/](measurements/) | Timing CSVs |
| [flops/](flops/) | Decoder FLOP grid |
| [figures/](figures/) | Plots |
| [complexity/](complexity/README.md) | SE width × depth |
| [submit/](submit/) | Embedding / training / FLOP jobs |

**Inputs (repo paths):** `data/luca/runtime/`, `results/luca-runtime-fm/`, `results/luca-runtime-complexity/`.
**Timing:** wall time, including loading/checkpoints.
**FLOPs:** processed cells/epoch (~395,000 train, 109,824 validation on full LuCA).

**Refresh (repository root):**

```bash
# Logs → CSVs + cell-count plot
python runtime/02_foundation_model/codes/summarize_runtime.py
# CSVs → decoder FLOP plot
python runtime/02_foundation_model/codes/plot_decoder_flops.py --include-se-runtime
```

**Slurm image:** `RECONEVAL_IMAGE`. **Estimates:** [notebook and tables](../estimates/README.md).
