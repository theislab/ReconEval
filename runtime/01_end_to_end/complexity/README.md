# AE/VAE complexity

- **Latent:** 2048.
- **Widths:** 1024, 2048, 4096. **Depths:** 1, 2, 4.
- **Runs:** 54; three repeats.
- [fixed_latent_2048/](fixed_latent_2048/): config, manifest, FLOPs.
- [run_manifest.csv](run_manifest.csv): earlier 36 runs; notebook inputs.
- [complexity_runtime.csv](../measurements/complexity_runtime.csv): combined timings.
- [train.sbatch](submit/train.sbatch): training job.

**Time/epoch:** wall time ÷ epochs; includes overhead.

[Plot commands and outputs](../README.md)
