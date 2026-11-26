from __future__ import annotations

import os
import tempfile
import warnings
from pathlib import Path

import anndata as ad
import lightning as L
import numpy as np
from anndata import AnnData
import scipy.sparse as sp

MODEL_VERSION = "V2"


def _device(device: str | None) -> str:
    if device is not None:
        return device
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def load_geneformer(checkpoint_path: str | os.PathLike[str], device: str | None = None):
    """Load a Geneformer model directory (e.g. ``Geneformer-V2-316M``) in evaluation mode."""
    from transformers import BertForMaskedLM

    model_dir = Path(checkpoint_path)
    model = BertForMaskedLM.from_pretrained(
        str(model_dir), output_hidden_states=True
    )
    cfg = model.config
    # if cfg.num_hidden_layers != 6 or cfg.max_position_embeddings != 2048:
    #     raise ValueError(
    #         "Expected the paper's 6-layer/2048-token model, got "
    #         f"{cfg.num_hidden_layers} layers / {cfg.max_position_embeddings}"
    #     )
    model.eval().to(_device(device))
    print(f"[Geneformer] loaded {model_dir.name}: {cfg.num_hidden_layers} layers, {cfg.max_position_embeddings} tokens")
    return model


def geneformer_tokenizer(custom_attr_name_dict: dict | None = None, nproc: int = 4):
    from geneformer import TranscriptomeTokenizer

    return TranscriptomeTokenizer(
        custom_attr_name_dict=custom_attr_name_dict,
        nproc=nproc,
        model_version=MODEL_VERSION,
    )


def tokenize_adata(adata, workdir: Path, nproc: int = 4):
    """Write AnnData and tokenize it with Geneformer's V1 tokenizer."""
    from datasets import load_from_disk

    if "ensembl_id" not in adata.var:
        raise AssertionError(
            "adata.var['ensembl_id'] is required (Ensembl gene IDs)"
        )
    if "n_counts" not in adata.obs:
        adata.obs["n_counts"] = np.asarray(adata.X.sum(axis=1)).ravel()
    adata.obs["cell_idx"] = np.arange(adata.n_obs)

    (workdir / "in").mkdir(parents=True, exist_ok=True)
    adata.write_h5ad(workdir / "in" / "data.h5ad")
    tokenizer = geneformer_tokenizer(
        custom_attr_name_dict={"cell_idx": "cell_idx"}, nproc=nproc
    )
    tokenizer.tokenize_data(
        str(workdir / "in"),
        str(workdir),
        "tok",
        file_format="h5ad",
    )
    return load_from_disk(str(workdir / "tok.dataset")), tokenizer


def embed_geneformer(
    adata,
    model,
    emb_layer: int = -1,
    batch_size: int = 32,
    nproc: int = 4,
    workdir: str | None = None,
) -> np.ndarray:
    """
    Extract cell embeddings using the supplied loaded Geneformer model.

    ``emb_layer=-1`` selects the second-to-last transformer layer and
    ``emb_layer=0`` selects the last layer, matching EmbExtractor semantics.
    """
    import torch

    device = next(model.parameters()).device
    n_layers = model.config.num_hidden_layers
    if emb_layer not in (-1, 0):
        raise AssertionError(
            "emb_layer must be -1 (second-to-last) or 0 (last), "
            "as in EmbExtractor"
        )
    hidden_state_index = n_layers + emb_layer

    with tempfile.TemporaryDirectory(prefix="geneformer_", dir=workdir) as tmp:
        work_path = Path(tmp)
        dataset, tokenizer = tokenize_adata(adata, work_path, nproc=nproc)
        pad_id = tokenizer.gene_token_dict["<pad>"]
        order = np.argsort(-np.asarray(dataset["length"]))
        input_ids = dataset["input_ids"]
        lengths = np.asarray(dataset["length"])
        cell_idx = np.asarray(dataset["cell_idx"])
        output = np.empty(
            (len(dataset), model.config.hidden_size), dtype=np.float32
        )

        with torch.no_grad():
            for start in range(0, len(order), batch_size):
                indices = order[start : start + batch_size]
                max_length = int(lengths[indices].max())
                ids = torch.full(
                    (len(indices), max_length), pad_id, dtype=torch.long
                )
                attention = torch.zeros(
                    (len(indices), max_length), dtype=torch.long
                )
                for row, index in enumerate(indices):
                    length = int(lengths[index])
                    ids[row, :length] = torch.tensor(
                        input_ids[int(index)], dtype=torch.long
                    )
                    attention[row, :length] = 1
                hidden_states = model(
                    input_ids=ids.to(device),
                    attention_mask=attention.to(device),
                ).hidden_states[hidden_state_index]

                if MODEL_VERSION == "V2":
                    cell_embeddings = hidden_states[:, 0, :]
                else:  # mean over genes only (skip <cls> at position 0 and <eos> at position length-1)
                    mask = attention.clone()
                    mask[:, 0] = 0
                    mask[torch.arange(mask.shape[0]), lengths_tensor - 1] = 0
                    mask = mask.unsqueeze(-1).to(hidden_states.dtype)
                    cell_embeddings = (hidden_states * mask).sum(1) / mask.sum(1)

                output[indices] = cell_embeddings.float().cpu().numpy()

        result = np.empty_like(output)
        result[cell_idx] = output
    return result


class ReconPretrainedGeneformer:
    def __init__(self, checkpoint_path: str, emb_key: str = "X_Geneformer", **kwargs):
        self.model_params = {
            "checkpoint_path": checkpoint_path,
            "emb_key": emb_key,
            "emb_layer": kwargs.get("emb_layer", -1),
            "device": kwargs.get("device"),
            "batch_size": kwargs.get("batch_size", 32),
            "nproc": kwargs.get("nproc", 4),
            "workdir": kwargs.get("workdir"),
        }
        self.inferer = self._load_pretrained_model(checkpoint_path)
        self.emb_key = emb_key
        self.genes = None
        self.overlap_genes = None

    def _load_pretrained_model(self, checkpoint_path):
        return load_geneformer(checkpoint_path, self.model_params["device"])

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
            adata = ad.AnnData(X=X, var={"ensembl_id": self.genes})

        if not sp.issparse(adata.X):
            adata.X = sp.csr_matrix(adata.X)
            
        return embed_geneformer(
            adata,
            model=self.inferer,
            emb_layer=self.model_params["emb_layer"],
            batch_size=self.model_params["batch_size"],
            nproc=self.model_params["nproc"],
            workdir=self.model_params["workdir"],
        )

    def train(self, datamodule: L.LightningDataModule = None, **train_kwargs):
        if datamodule is not None:
            raise NotImplementedError("Fine-tuning is not supported.")

    def set_genes(self, genes: list[str]):
        self.genes = genes

    def get_overlap_genes(self, genes) -> list[str]:
        warnings.warn("Gene overlap is not implemented for Geneformer.")
        return []

    def load(self, path: str, map_location=None) -> None:
        self.inferer = self._load_pretrained_model(path)
