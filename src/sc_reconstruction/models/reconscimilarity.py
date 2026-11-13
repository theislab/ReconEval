from __future__ import annotations

import inspect
import scanpy as sc
import numpy as np
import scipy.sparse as sp
import warnings
import anndata as ad
import lightning as L
from anndata import AnnData
from scimilarity import CellEmbedding
from scimilarity.utils import align_dataset, lognorm_counts
import pandas as pd

SCIMILARITY_GENE_OVERLAP = inspect.signature(align_dataset).parameters["gene_overlap_threshold"].default


def _is_raw_counts(X):
    """Heuristic: raw counts are non-negative integers."""
    vals = X.data if sp.issparse(X) else X.ravel()
    sample = vals[:min(100_000, len(vals))]
    if len(sample) == 0:
        return True
    return bool(np.all(sample >= 0) and np.allclose(sample, np.round(sample)))


def _normalize_total(X, target_sum=1e4):
    rs = np.asarray(X.sum(axis=1)).ravel()
    scale = np.zeros_like(rs, dtype=np.float64)
    nz = rs > 0
    scale[nz] = target_sum / rs[nz]
    return X * scale[:, None]


def preprocess_for_scimilarity(X):
    """Bring X into log1p(normalize_total(raw, 1e4)) space.

    Auto-detects whether X is raw counts or already log1p-normalised:
      - raw counts  → normalize_total(1e4) → log1p
      - log1p data  → expm1 → normalize_total(1e4) → log1p
    """
    if _is_raw_counts(X):
        X = _normalize_total(X, target_sum=1e4)
        return np.log1p(X)
    X = np.expm1(X)
    X = _normalize_total(X, target_sum=1e4)
    return np.log1p(X)

class ReconPretrainedscimilarity(): 
    def __init__(
        self,
        checkpoint_path: str, 
        emb_key: str = 'X_scimilarity',
        gene_overlap_threshold: int | None = None,
        **kwargs
    ):
        """Pre-trained SCimilarity foundation model wrapper.

        Wraps the SCimilarity encoder for ReconEval's foundation-model
        reconstruction task. Requires the ``scimilarity`` package and
        runs in the ``scimilarity_env`` conda env.

        Args:
            checkpoint_path: Path to the pre-trained model checkpoint
                (config, model weights, gene mapping).
            gene_overlap_threshold: Minimum number of genes shared with the model;
                ``None`` uses SCimilarity's default.
        """
        if gene_overlap_threshold is None:
            gene_overlap_threshold = SCIMILARITY_GENE_OVERLAP
        if gene_overlap_threshold < SCIMILARITY_GENE_OVERLAP:
            warnings.warn(
                f"gene_overlap_threshold={gene_overlap_threshold} is below SCimilarity's "
                f"default of {SCIMILARITY_GENE_OVERLAP} shared genes. SCimilarity is not intended for inputs "
                "with this few genes.",
                UserWarning,
            )
        self.model_params = {
            'checkpoint_path': checkpoint_path,
            'emb_key': emb_key,
            'gene_overlap_threshold': gene_overlap_threshold,
        }

        self.inferer = self._load_pretrained_model(checkpoint_path)
        self.emb_key = emb_key
        self.gene_overlap_threshold = gene_overlap_threshold
        self.genes = None
        self.overlap_genes = None

    def _load_pretrained_model(self, checkpoint_path):
        """Load the pre-trained SCimilarity CellEmbedding model."""
        
        ce = CellEmbedding(model_path=checkpoint_path)
        return ce

    def prepare(self, adata: AnnData | None = None, **kwargs):
        """Cache the adata reference and its gene list on the wrapper."""
        if adata is not None:
            self.adata = adata
            self.genes = adata.var_names.tolist()

    def get_latent_representation(
        self, 
        X: np.ndarray|ad.AnnData
        ) -> np.ndarray:

        device = next(self.inferer.model.parameters()).device
        if isinstance(X, ad.AnnData):
            temp_adata = X
        else:
            temp_adata = AnnData(X=X, var=pd.DataFrame(index=self.genes))

        temp_adata = align_dataset(
            temp_adata,
            self.inferer.gene_order,
            gene_overlap_threshold=self.gene_overlap_threshold,
        )
        X_dense = temp_adata.X.toarray() if sp.issparse(temp_adata.X) else np.asarray(temp_adata.X)
        temp_X = preprocess_for_scimilarity(X_dense)
        cell_embs = self.inferer.get_embeddings(temp_X)
        return cell_embs


    def train(self, datamodule: L.LightningDataModule = None, **train_kwargs):
        """No-op: SCimilarity is used frozen. Raises if a datamodule is passed."""
        if datamodule is not None:
            raise NotImplementedError(
                "Fine-tuning is not supported for the pretrained SCimilarity wrapper."
            )

    def set_genes(self, genes: list[str]):
        """Set the genes for reconstruction"""
        self.genes = genes

    def get_overlap_genes(self, genes) -> list[str]:
        """Not implemented for SCimilarity; reserved for parity with other FM wrappers."""
        raise NotImplementedError(
            "get_overlap_genes is not implemented for the SCimilarity wrapper."
        )


    def load(self, path: str, map_location=None) -> None:
        """Load model configuration"""
        self.inferer = self._load_pretrained_model(path)
