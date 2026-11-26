from __future__ import annotations

import os
import pickle
import sys
import tempfile
import warnings
from pathlib import Path

import anndata as ad
import lightning as L
import numpy as np
from anndata import AnnData

# UCE's code reads ./model_files/new_species_protein_embeddings.csv from its repository.
UCE_DIR = Path(os.environ.get("UCE_DIR", "/opt/foundation_models/UCE"))
UCE_CKPT_NAME = "33l_8ep_1024t_1280.torch"
UCE_NLAYERS = 33
UCE_TOKEN_DIM, UCE_D_MODEL, UCE_D_HID, UCE_NHEAD, UCE_DROPOUT, UCE_OUT = (
    5120,
    1280,
    5120,
    20,
    0.05,
    1280,
)
UCE_N_TOKENS = 145469


def _device(device: str | None) -> str:
    if device is not None:
        return device
    import torch

    return "cuda" if torch.cuda.is_available() else "cpu"


def load_uce(checkpoint_path: str | os.PathLike[str], device: str | None = None):
    """Load the 33-layer UCE model from a directory of UCE model files."""
    import torch
    from torch import nn

    model_files = Path(checkpoint_path).resolve()
    ckpt = model_files / UCE_CKPT_NAME
    token_file = model_files / "all_tokens.torch"
    if str(UCE_DIR) not in sys.path:
        sys.path.append(str(UCE_DIR))
    cwd = os.getcwd()
    os.chdir(UCE_DIR)
    try:
        from model import TransformerModel

        if not ckpt.exists():
            raise FileNotFoundError(
                f"{ckpt} missing — run download_checkpoints.py --model UCE"
            )
        model = TransformerModel(
            token_dim=UCE_TOKEN_DIM,
            d_model=UCE_D_MODEL,
            nhead=UCE_NHEAD,
            d_hid=UCE_D_HID,
            nlayers=UCE_NLAYERS,
            dropout=UCE_DROPOUT,
            output_dim=UCE_OUT,
        )
        empty_pe = torch.zeros(UCE_N_TOKENS, UCE_TOKEN_DIM)
        model.pe_embedding = nn.Embedding.from_pretrained(empty_pe)
        model.load_state_dict(torch.load(ckpt, map_location="cpu"), strict=True)
        all_pe = torch.load(token_file, map_location="cpu")
        if all_pe.shape[0] == 143574:
            torch.manual_seed(23)
            all_pe = torch.vstack(
                (all_pe, torch.normal(0, 1, size=(1895, UCE_TOKEN_DIM)))
            )
        if all_pe.shape[0] != UCE_N_TOKENS:
            model.pe_embedding = nn.Embedding.from_pretrained(all_pe)
    finally:
        os.chdir(cwd)
    model.eval().to(_device(device))
    n_params = sum(p.numel() for p in model.parameters() if p.requires_grad) / 1e6
    print(
        f"[UCE] loaded {ckpt.name}: "
        f"{UCE_NLAYERS} layers, {n_params:.0f}M trainable params"
    )
    return model


def embed_uce(
    adata,
    model,
    checkpoint_path: str | os.PathLike[str],
    species: str = "human",
    batch_size: int = 25,
    workdir: str | None = None,
    name: str = "query",
    device: str | None = None,
) -> np.ndarray:
    from argparse import Namespace

    import torch
    from accelerate import Accelerator
    from torch import nn
    from torch.utils.data import DataLoader

    model_files = Path(checkpoint_path).resolve()
    if workdir is not None:
        workdir = os.path.abspath(workdir)
    if str(UCE_DIR) not in sys.path:
        sys.path.append(str(UCE_DIR))
    cwd = os.getcwd()
    os.chdir(UCE_DIR)
    try:
        from data_proc.data_utils import (
            adata_path_to_prot_chrom_starts,
            get_spec_chrom_csv,
            get_species_to_pe,
        )
        from data_proc import gene_embeddings
        from eval_data import MultiDatasetSentenceCollator, MultiDatasetSentences
        from evaluate import AnndataProcessor

        # gene_embeddings hardcodes model_files/protein_embeddings/ for the built-in species.
        species_paths = gene_embeddings.MODEL_TO_SPECIES_TO_GENE_EMBEDDING_PATH["ESM2"]
        for key, path in species_paths.items():
            if Path(path).parent == gene_embeddings.EMBEDDING_DIR:
                species_paths[key] = model_files / "protein_embeddings" / Path(path).name

        with tempfile.TemporaryDirectory(prefix="uce_", dir=workdir) as tmp:
            work_path = Path(tmp)
            adata_path = work_path / f"{name}.h5ad"
            adata.write_h5ad(adata_path)
            args = Namespace(
                adata_path=str(adata_path),
                dir=str(work_path) + "/",
                species=species,
                filter=False, # True originally, but them combinations with 10 or less cells cannot be processed 
                skip=True,
                model_loc=str(model_files / UCE_CKPT_NAME),
                nlayers=UCE_NLAYERS,
                batch_size=batch_size,
                pad_length=1536,
                pad_token_idx=0,
                chrom_token_left_idx=1,
                chrom_token_right_idx=2,
                cls_token_idx=3,
                CHROM_TOKEN_OFFSET=143574,
                sample_size=1024,
                CXG=True,
                output_dim=UCE_OUT,
                d_hid=UCE_D_HID,
                token_dim=UCE_TOKEN_DIM,
                multi_gpu=False,
                spec_chrom_csv_path=str(model_files / "species_chrom.csv"),
                token_file=str(model_files / "all_tokens.torch"),
                protein_embeddings_dir=str(model_files / "protein_embeddings") + "/",
                offset_pkl_path=str(model_files / "species_offsets.pkl"),
            )
            accelerator = Accelerator(project_dir=args.dir)
            processor = AnndataProcessor(args, accelerator)
            processor.preprocess_anndata()
            processor.generate_idxs()
            with open(processor.shapes_dict_path, "rb") as shapes_file:
                shapes_dict = pickle.load(shapes_file)
            dataset = MultiDatasetSentences(
                sorted_dataset_names=[processor.name],
                shapes_dict=shapes_dict,
                args=args,
                npzs_dir=args.dir,
                dataset_to_protein_embeddings_path=processor.pe_idx_path,
                datasets_to_chroms_path=processor.chroms_path,
                datasets_to_starts_path=processor.starts_path,
            )
            collator = MultiDatasetSentenceCollator(args)
            dataloader = DataLoader(
                dataset, batch_size=batch_size, shuffle=False, collate_fn=collator
            )
            model, dataloader = accelerator.prepare(model, dataloader)
            outputs = []
            with torch.no_grad():
                for batch in dataloader:
                    sentences, mask, _ = batch[0], batch[1], batch[2]
                    sentences = sentences.permute(1, 0)
                    token_embeddings = model.pe_embedding(sentences.long())
                    token_embeddings = nn.functional.normalize(token_embeddings, dim=2)
                    _, embedding = model(src=token_embeddings, mask=mask)
                    outputs.append(embedding.detach().cpu().numpy())
            result = np.vstack(outputs).astype(np.float32)
            # processor.adata.obsm["X_uce"] = result
            # processor.adata.write(work_path / f"{name}_uce_adata.h5ad")
        return result
    finally:
        os.chdir(cwd)


class ReconPretrainedUCE:
    def __init__(self, checkpoint_path: str, emb_key: str = "X_UCE", **kwargs):
        self.model_params = {
            "checkpoint_path": checkpoint_path,
            "emb_key": emb_key,
            "species": kwargs.get("species", "human"),
            "batch_size": kwargs.get("batch_size", 25),
            "workdir": kwargs.get("workdir"),
            "device": kwargs.get("device"),
        }
        self.inferer = self._load_pretrained_model(checkpoint_path)
        self.emb_key = emb_key
        self.genes = None
        self.overlap_genes = None

    def _load_pretrained_model(self, checkpoint_path):
        return load_uce(checkpoint_path, self.model_params.get("device"))

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
            adata = ad.AnnData(X=X)
            adata.var_names = self.genes
        return embed_uce(
            adata,
            model=self.inferer,
            checkpoint_path=self.model_params["checkpoint_path"],
            species=self.model_params["species"],
            batch_size=self.model_params["batch_size"],
            workdir=self.model_params["workdir"],
            device=self.model_params["device"],
        )

    def train(self, datamodule: L.LightningDataModule = None, **train_kwargs):
        if datamodule is not None:
            raise NotImplementedError("Fine-tuning is not supported.")

    def set_genes(self, genes: list[str]):
        self.genes = genes

    def get_overlap_genes(self, genes) -> list[str]:
        warnings.warn("Gene overlap is not implemented for UCE.")
        return []

    def load(self, path: str, map_location=None) -> None:
        self.inferer = self._load_pretrained_model(path)
