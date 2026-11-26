import sys
from pathlib import Path

import hydra
import zarr
from hydra.utils import instantiate
from omegaconf import DictConfig

sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
from sc_reconstruction.utils.data_tools import (
    get_zarr_attr,
    split_zarr_dataloader,
)


@hydra.main(
    config_path="../configs/pretrained",
    config_name="scFoundation",
    version_base=None,
)
def emb(cfg: DictConfig) -> None:
    all_combinations = get_zarr_attr(
        cfg.data_args.split_meta_root,
        target_key=cfg.data_args.target_key,
    )
    print(f"All combinations for key {cfg.data_args.target_key}: len {len(all_combinations)}")

    total_combinations = len(all_combinations)
    part_size = total_combinations // cfg.total_parts
    start_idx = (cfg.parts - 1) * part_size
    end_idx = cfg.parts * part_size if cfg.parts < cfg.total_parts else total_combinations
    selected_combinations = all_combinations[start_idx:end_idx]
    print(f"Processing part {cfg.parts}/{cfg.total_parts}: combinations {start_idx} to {end_idx}.")

    test_dataloader = split_zarr_dataloader(
        cfg.data_args.comb_meta_root,
        selected_combinations,
        target_key=cfg.data_args.target_key,
    )
    gene_names = zarr.open(cfg.data_args.var_names_path, mode="r").attrs[
        cfg.data_args.var_names_key
    ]

    pretrained_fm = instantiate(cfg.model_args)
    pretrained_fm.set_genes(gene_names)

    output_dir = cfg.data_args.output_dir
    state_zarr = zarr.open(output_dir, mode="a")
    chunk_size = 10_000
    existing_combinations = list(state_zarr.group_keys())
    print(f"{len(existing_combinations)} existing combinations in output Zarr")

    for combination, X in test_dataloader:
        if combination in existing_combinations:
            print(f"Combination {combination} already processed. Skipping.")
            continue

        cell_emb = pretrained_fm.get_latent_representation(X=X)
        state_zarr.create_group(combination, overwrite=True)
        state_zarr[combination].create_dataset(
            "X",
            data=cell_emb,
            chunks=(chunk_size, cell_emb.shape[1]),
        )

    print(f"Embedding extraction for key {cfg.data_args.target_key} completed.")


if __name__ == "__main__":
    emb()
