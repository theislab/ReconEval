from __future__ import annotations

import os
import sys
import warnings
from pathlib import Path

import anndata as ad
import lightning as L
import numpy as np
from anndata import AnnData

SCF_MODEL_DIR = Path(
    os.environ.get("SCFOUNDATION_DIR", "/opt/foundation_models/scFoundation/model")
)
SCF_GENE_LIST = SCF_MODEL_DIR / "OS_scRNA_gene_index.19264.tsv"


def _device(device: str | None):
    if device is not None:
        return device
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def _scfoundation_ckpt(checkpoint_path: str | os.PathLike[str]) -> Path:
    """Return ``checkpoint_path`` if it is a file, else the checkpoint in that directory."""
    path = Path(checkpoint_path)
    if path.is_file():
        return path
    preferred = path / "models.ckpt"
    if preferred.exists():
        return preferred
    ckpts = sorted(path.glob("*.ckpt"))
    if not ckpts:
        raise FileNotFoundError(f"No .ckpt in {path}")
    return ckpts[0]


def load_scfoundation(
    checkpoint_path: str | os.PathLike[str],
    key: str = "cell",
    device: str | None = None,
):
    """Load the scFoundation encoder and return it with its configuration."""
    if str(SCF_MODEL_DIR) not in sys.path:
        sys.path.append(str(SCF_MODEL_DIR))
    from load import load_model_frommmf

    ckpt = _scfoundation_ckpt(checkpoint_path)
    model, config = load_model_frommmf(str(ckpt), key)
    selected_device = _device(device)
    model.eval().to(selected_device)
    n_params = sum(parameter.numel() for parameter in model.parameters()) / 1e6
    print(
        f"[scFoundation] loaded {ckpt.name} "
        f"(key={key}): {n_params:.0f}M params"
    )
    return model, config


def scfoundation_gene_list() -> list[str]:
    import pandas as pd

    return list(pd.read_csv(SCF_GENE_LIST, sep="\t")["gene_name"])


class ReconPretrainedscFoundation:
    def __init__(self, checkpoint_path: str, emb_key: str = "X_scFoundation", **kwargs):
        self.model_params = {
            "checkpoint_path": checkpoint_path,
            "emb_key": emb_key,
            "device": kwargs.get("device"),
        }
        self.inferer, self.config = self._load_pretrained_model(
            checkpoint_path, device=kwargs.get("device")
        )
        self.emb_key = emb_key
        self.genes = None
        self.overlap_genes = None

    def _load_pretrained_model(self, checkpoint_path, device: str | None = None):
        return load_scfoundation(checkpoint_path, device=device)

    def prepare(self, adata: AnnData | None = None, **kwargs):
        if adata is not None:
            self.adata = adata
            self.genes = adata.var_names.tolist()

    def get_latent_representation(self, X: np.ndarray | ad.AnnData) -> np.ndarray:
        if isinstance(X, ad.AnnData):
            adata = X
        else:
            if self.genes is None:
                raise ValueError("Gene names are required when X is a NumPy array.")
            adata = ad.AnnData(X=X, var={"gene_name": self.genes})
            adata.var_names = self.genes
        return embed_scfoundation(
            adata,
            self.inferer,
            self.config,
            device=self.model_params["device"],
            checkpoint_path=self.model_params["checkpoint_path"],
        )

    def train(self, datamodule: L.LightningDataModule = None, **train_kwargs):
        if datamodule is not None:
            raise NotImplementedError("Fine-tuning is not supported.")

    def set_genes(self, genes: list[str]):
        self.genes = genes

    def get_overlap_genes(self, genes) -> list[str]:
        warnings.warn("Gene overlap is not implemented for scFoundation.")
        return []

    def load(self, path: str, map_location=None) -> None:
        self.inferer = self._load_pretrained_model(path)


def embed_scfoundation(
    adata,
    model,
    cfg,
    pre_normalized: bool = True,
    total_counts=None,
    tgthighres: str = "t4",
    pool_type: str = "all",
    batch_size: int = 1,
    device: str | None = None,
    checkpoint_path: str | os.PathLike[str] | None = None,
) -> np.ndarray:
    """
    Compute scFoundation embeddings for an AnnData object.

    ``pre_normalized=True`` expects log1p(10k)-normalized expression values.
    With ``pre_normalized=False``, raw counts are normalized inside this
    function. ``pool_type="all"`` returns the 3072-dimensional concatenated
    representation; ``pool_type="max"`` returns the 768-dimensional max pool.
    """
    import pandas as pd
    import scipy.sparse as sp
    import torch

    if str(SCF_MODEL_DIR) not in sys.path:
        sys.path.append(str(SCF_MODEL_DIR))
    from load import gatherData

    selected_device = _device(device)

    genes = scfoundation_gene_list()
    X = adata.X.toarray() if sp.issparse(adata.X) else np.asarray(adata.X)
    df = pd.DataFrame(X, columns=adata.var_names)
    df = df.loc[:, df.columns.intersection(genes)]
    X = df.reindex(columns=genes, fill_value=0.0).to_numpy(dtype=np.float32)
    n_missing = len(genes) - df.shape[1]
    print(f"[scFoundation] {df.shape[1]} genes matched, {n_missing} zero-filled")

    if pre_normalized:
        logx = X
        if total_counts is None:
            total = logx.sum(axis=1)
        else:
            total = np.asarray(total_counts, dtype=np.float64)
    else:
        total = X.sum(axis=1)
        logx = np.log1p(X / total[:, None] * 1e4)

    kind, value = tgthighres[0], float(tgthighres[1:])
    log_total = np.log10(total)
    if kind == "f":
        high_resolution = np.log10(total * value)
    elif kind == "a":
        high_resolution = log_total + value
    elif kind == "t":
        high_resolution = np.full_like(log_total, value)
    else:
        raise ValueError("tgthighres must start with 'f', 'a' or 't'")

    full = np.concatenate(
        [logx, high_resolution[:, None], log_total[:, None]], axis=1
    ).astype(np.float32)

    outputs = []
    with torch.no_grad():
        for start in range(0, full.shape[0], batch_size):
            x_in = torch.from_numpy(full[start : start + batch_size]).to(
                selected_device
            )
            gene_ids = torch.arange(19266, device=selected_device).repeat(
                x_in.shape[0], 1
            )
            mask = x_in > 0
            x, x_padding = gatherData(x_in, mask, cfg["pad_token_id"])
            position_ids, _ = gatherData(
                gene_ids, mask, cfg["pad_token_id"]
            )
            hidden = model.token_emb(
                torch.unsqueeze(x, 2).float(), output_weight=0
            )
            hidden = hidden + model.pos_emb(position_ids)
            hidden = model.encoder(hidden, x_padding)

            valid = ~x_padding
            token_count = valid.sum(1)
            batch_indices = torch.arange(hidden.shape[0], device=selected_device)
            if pool_type == "all":
                embedding_1 = hidden[batch_indices, token_count - 1]
                embedding_2 = hidden[batch_indices, token_count - 2]
                gene_mask = valid.clone()
                gene_mask[batch_indices, token_count - 1] = False
                gene_mask[batch_indices, token_count - 2] = False
                embedding_3 = hidden.masked_fill(
                    ~gene_mask[..., None], float("-inf")
                ).max(dim=1).values
                embedding_4 = (hidden * gene_mask[..., None]).sum(1) / (
                    gene_mask.sum(1, keepdim=True)
                )
                embedding = torch.cat(
                    [embedding_1, embedding_2, embedding_3, embedding_4], dim=1
                )
            elif pool_type == "max":
                embedding = hidden.masked_fill(
                    ~valid[..., None], float("-inf")
                ).max(dim=1).values
            else:
                raise ValueError("pool_type must be 'all' or 'max'")
            outputs.append(embedding.float().cpu().numpy())

    return np.concatenate(outputs, axis=0)
