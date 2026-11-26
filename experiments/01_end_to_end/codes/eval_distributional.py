import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[3] / "src"))
import sys
sys.path.append('../')

import os
import torch
import hydra
from omegaconf import DictConfig, OmegaConf
from hydra.utils import instantiate
from functools import partial
import pandas as pd
import numpy as np
import zarr
from sc_reconstruction.metrics.utils import gene_r_squared, mean_squared_error, mmd_rbf, energy_distance
from sc_reconstruction.utils.model_loader import create_model_from_cfg
from sc_reconstruction.utils.run_tools import sample_list




@hydra.main(config_path="../configs", config_name="base_eval", version_base=None)
def main(cfg: DictConfig) -> None:
    
    running_device = None if torch.cuda.is_available() else "cpu"
    print(f"Running on device: {running_device}")
    # Load model - either using dynamic loading or direct instantiation
    if cfg.get('dynamic_model_loading', False):
        model, checkpoint_path = create_model_from_cfg(cfg, running_device)
        print(f"Loaded model from {checkpoint_path} using dynamic loading")
    else:
        model = instantiate(cfg.model.model_args)
        model.load(cfg.model.load.path, map_location=running_device)
        print(f"Loaded model from {cfg.model.load.path} using direct instantiation")

    # Older mlAE checkpoints used the library encoder output directly. Fresh
    # models use their own forward implementation, including its exponentiation.
    module = getattr(model, "module", None)
    if (
        cfg.get("legacy_mlae_forward", True)
        and cfg.model.meta.name == "mlAE"
        and getattr(module, "l_encoder", None) is not None
    ):
        import types

        def patched_forward_modeled(self, x):
            z = self.encoder(x)
            library_size = self.l_encoder(x)
            return self.decoder(z, library_size)

        module._forward_modeled = types.MethodType(patched_forward_modeled, module)
        module.forward_fn = module._forward_modeled
        print("Using legacy mlAE modeled-library forward implementation.")
    
    # Load projection model (e.g., PCA)
    print("Loading projection model...")
    projector = instantiate(cfg.metric.projector.model_args)
    projector.load(cfg.metric.projector.load.path)
    
    # Define metrics
    metric_functions = {
        "r2_score": gene_r_squared,
        "mse": mean_squared_error,
        "mmd_rbf": partial(mmd_rbf, gamma=0.5),
        "energy_distance": energy_distance,
    }
    


    save_path = cfg.output.save_path
    print('save path:', save_path)
    
    # Load zarr dataset and get all combinations
    zarr_path = cfg.eval_path
    # zarr_path = '/lustre/groups/ml01/workspace/xiaotong.fu/reconstruction/comb_w_obs/cl_drg_dos.zarr'
    print(f"Using zarr dataset: {zarr_path}")
    
    root_zarr = zarr.open(zarr_path, mode='r')

    split_zarr = zarr.open(cfg.data.split_comb, mode='r')
    test_combs = split_zarr.attrs['test_combinations']
    train_combs = split_zarr.attrs['train_combinations']
    train_length = len(train_combs)


    # Sample 10% of combinations 
    seed = cfg.get("seed", 42) 
    train_fraction = cfg.get("train_fraction", 0.10)  
    test_fraction  = cfg.get("test_fraction", 1.00)    

    rng = np.random.default_rng(seed)
    if train_fraction > 1e-4:
        train_comb_list = sample_list(train_combs, train_fraction, rng)
    else:
        train_comb_list = []
    test_comb_list = sample_list(test_combs, test_fraction, rng)
    comb_list = list(test_comb_list) + list(train_comb_list)

    
    print(f"Sampled {test_fraction} test and {train_fraction} train with seed {seed}")
    print(f"Total combinations: {len(comb_list)}, test combinations: {len(test_comb_list)}, train combinations: {len(train_comb_list)}")
    print(f"First 5 sampled combinations: {comb_list[:5]}")
    

    
    evaluator_factory = instantiate(cfg.metric.evaluator, _partial_=True)
    evaluator = evaluator_factory(
        model=model,
        projector=projector,
        comb_list=comb_list,
        metric_funcs=metric_functions
    )
    
    # Run evaluation
    evaluator.run(save_path)
    
    print("Successfully saved results to:", save_path)

if __name__ == "__main__":
    main()
