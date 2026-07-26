# 02_foundation_model — FM-based reconstruction

Two-step pipeline:

1. **Embed** a dataset with a pre-trained FM (SE / scGPT / scConcept /
   SCimilarity) → one zarr / h5ad of cell embeddings.
2. **Decode** those embeddings back to gene expression with a downstream
   MLP, Transformer or KNN decoder.

The FM weights are frozen — no fine-tuning. Matches the
`tutorials/fm.ipynb` recipe.

## Layout

```
02_foundation_model/
├── configs/
│   ├── base_pretrained_emb.yaml      # root for embed-side scripts
│   ├── base_pretrained_dec_hvg.yaml  # root for decoder-side scripts
│   ├── pretrained/
│   │   ├── SE.yaml
│   │   ├── scGPT.yaml
│   │   ├── scConcept.yaml
│   │   └── scimilarity.yaml
│   ├── decoder/
│   │   ├── MLP.yaml
│   │   ├── Transformer.yaml
│   │   └── KNN.yaml
│   ├── model/eval/
│   │   └── AE.yaml                   # eval-side AE reference
│   └── data/
│       ├── pbmc.yaml
│       ├── tahoe.yaml
│       └── luca.yaml
├── codes/
│   ├── SE_emb.py                     # FM-specific embed (zarr loop)
│   ├── SE_emb_adata.py               # FM-specific embed (in-memory h5ad)
│   ├── scGPT_emb.py
│   ├── scConcept_emb.py
│   ├── scimilarity_emb.py
│   ├── decoderonly_hvg.py            # decoder w/ Hydra
│   ├── decoderonly_hvg_tsfm.py       # transformer decoder variant
│   ├── eval_decoder_statistical.py   # statistical scoring of decoder outputs
│   └── eval_decoder_biological.py    # biological scoring of decoder outputs
└── submit/
    └── decoderonly_grid.sbatch       # Hydra --multirun decoder sweep
```

## Eval drivers

Once you have a trained decoder checkpoint from `decoderonly_hvg.py` /
`decoderonly_hvg_tsfm.py`, score it with:

```bash
python experiments/02_foundation_model/codes/eval_decoder_statistical.py \
  pretrained=SE decoder=MLP data=pbmc +metric=decode_statistical
```

Both eval drivers use Hydra root `base_eval_decode` and rely on the
metric subgroups under `configs/metric/`.

## Step 1: embed

Each FM has its own driver + Hydra config, and each ships in its OWN conda
env because their torch/CUDA/flash-attn pins clash pairwise.

```bash
# SE (uses the STATE package)
STATE_SRC=/path/to/state/src conda activate reconeval-state
python experiments/02_foundation_model/codes/SE_emb.py \
  total_parts=1 parts=1 \
  data_args.output_dir=/path/to/SE_emb.zarr

# scGPT
conda activate scgpt
python experiments/02_foundation_model/codes/scGPT_emb.py \
  total_parts=1 parts=1

# scConcept
conda activate scconcept_env
python experiments/02_foundation_model/codes/scConcept_emb.py \
  total_parts=1 parts=1

# SCimilarity
conda activate scimilarity_env
python experiments/02_foundation_model/codes/scimilarity_emb.py \
  total_parts=1 parts=1
```

`total_parts` × `parts` shards the combination grid so multiple workers
can split the corpus.

## Step 2: decode

The decoder reads embeddings from disk and trains an MLP / Transformer /
KNN head to predict gene expression. Hydra-driven with subgroup defaults:

```bash
python experiments/02_foundation_model/codes/decoderonly_hvg.py \
  pretrained=<SE|scGPT|scConcept|scimilarity> \
  decoder=<MLP|Transformer|KNN> \
  data=<pbmc|tahoe|luca>
```

For the transformer-specific driver:

```bash
python experiments/02_foundation_model/codes/decoderonly_hvg_tsfm.py \
  pretrained=SE decoder=Transformer data=pbmc
```

## Sweep

`submit/decoderonly_grid.sbatch` is a Hydra `--multirun` sweep over
decoder hidden sizes and number of layers. Edit the override list at the
top of the file before submitting.

## Quick smoke test

```bash
conda activate cstm_scvi_env
RECONEVAL_OUT=/tmp/reconeval_smoke \
python experiments/02_foundation_model/codes/decoderonly_hvg.py \
  pretrained=SE decoder=MLP data=pbmc \
  decoder.max_epochs=1 decoder.min_epochs=1
```

Expected output: an MLP decoder checkpoint under
`${RECONEVAL_OUT}/weights/pbmc/SE_MLP/.../<filename>.ckpt`.

## Reproduce a paper decoder from a released FM embedding

`codes/train_decoder_from_embedding.py` is a self-contained argparse
driver (no Hydra) intended for reproducibility on top of released FM
embeddings — one command, one env (`cstm_scvi_env`), one checkpoint out.

```bash
conda activate cstm_scvi_env
python experiments/02_foundation_model/codes/train_decoder_from_embedding.py \
  --emb-train-zarr /path/to/pbmc_SE/ag/split02/train.zarr \
  --emb-val-zarr   /path/to/pbmc_SE/ag/split02/val.zarr \
  --all-genes-zarr /path/to/pbmc_w_ag/comb_w_obs.zarr \
  --target-genes-zarr /path/to/pbmc/comb_w_obs.zarr \
  --embedding-key SE \
  --latent-dim 128 \
  --out $RECONEVAL_OUT/decoder/pbmc/SE/split02/MLP \
  --epochs 500
```

See `train_decoder_from_embedding.py --help` for all flags.

## Conda envs

| Env | Drivers |
|---|---|
| `cstm_scvi_env` | `decoderonly_hvg.py`, `train_decoder_from_embedding.py` (decoder-only training; no FM package needed at train time) |
| `reconeval-state` | `SE_emb.py`, `SE_emb_adata.py` (STATE FM embedder) |
| `reconeval-scgpt` | `scGPT_emb.py` |
| `reconeval-scconcept` | `scConcept_emb.py`, `decoderonly_hvg_tsfm.py` |
| `reconeval-scimilarity` | `scimilarity_emb.py` |
