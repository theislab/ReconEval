from __future__ import annotations

from typing import Dict, Any, Callable, Tuple, List
import zarr
import pandas as pd
import numpy as np
import os
import multiprocessing as mp
from functools import partial
from tqdm import tqdm
import warnings
from numcodecs import Blosc
import gc


class MetricsBatchEvaluator:
    """
    Base class to evaluate metrics on batches of data from a Zarr store.
    Statistical metrics specified in metric_funcs are computed for each batch.

    Attributes:
        model: Any - A model with a predict method that takes in data and returns predictions.
        zarr_path: str - Path to the Zarr store containing the data.
        comb_list: List[str] - List of combinations to evaluate, formatted as 'cell_line-drug-dosage'.
        metric_funcs: Dict | None - Dictionary of metric functions to apply, where keys are metric names and values are functions.
        max_cells: int - Maximum number of cells to process in a single batch.
        split_key: list[str] - List of keys to split the combination string into components.
        batch_size: int - Number of combinations to process in each batch.
        max_workers: int - Maximum number of worker processes to use for parallel processing.

    Returns:
        None
        When the evaluation is complete, results are saved as CSV to the specified output path.
    """

    def __init__(self,
                 model: Any,
                 zarr_path: str,
                 comb_list: List[str],
                 reference_batch: str = None,
                 proj_out_path: str | None = None,
                 dataset: str = None,
                 input_key: str = 'X',
                 output_key: str = 'X',
                 mode: str = "reconstruction",  # reconstruction, conditional, decode
                 ref_transform: str = None,
                 metric_funcs: Dict | None = None,
                 max_cells: int = 1e5,
                 split_key: list[str] = ['cell_line', 'drug', 'dosage'],
                 batch_size: int = 1000,
                 minibatch_size: int = 10_000,
                 max_workers: int = 2,
                 emb_zarr_path: str = None,
                 var_names: List[str] = None,
                 target_var_names: List[str] = None):

        assert mode in {"reconstruction", "conditional", "decode"}, \
            f"Unknown mode: {mode}"
        self.mode = mode
        self.model = model
        self.zarr_path = zarr_path
        self.emb_zarr_path = emb_zarr_path
        self.metric_funcs = metric_funcs or {}
        self.batch_size = batch_size
        self.max_cells = max_cells
        self.root_zarr = zarr.open(zarr_path, mode='r')
        if self.emb_zarr_path is not None and len(self.emb_zarr_path) > 0:
            self.emb_root_zarr = zarr.open(self.emb_zarr_path, mode='r')
        else:
            self.emb_root_zarr = None

        self.all_combs = comb_list
        self.split_key = split_key
        self.minibatch_size = minibatch_size

        if max_workers > 1:
            self.max_workers = mp.cpu_count()
        else:
            self.max_workers = 1
        self.pool = mp.get_context('spawn').Pool(self.max_workers)

        self.reference_batch = reference_batch
        self.dataset = dataset
        self.input_key = input_key
        self.output_key = output_key
        self.ref_transform = ref_transform

        # gene filtering
        self.var_names = var_names
        self.target_var_names = target_var_names
        if (self.var_names is not None) and (self.target_var_names is not None):
            idx = pd.Index(self.var_names).get_indexer(self.target_var_names)
            if (idx < 0).any():
                missing = [self.target_var_names[i] for i, v in enumerate(idx) if v < 0]
                raise ValueError(f"The following target_var_names are not in var_names: {missing}")
            self.filtered_var_indices = idx
        else:
            self.filtered_var_indices = None

        # optional projection output
        # only for conditional mode
        self.proj_out_path = proj_out_path
        self.proj_out_store = zarr.open(proj_out_path, mode='a') if proj_out_path else None
        if self.proj_out_store is not None:
            self.proj_out_store.attrs['reference_batch'] = reference_batch
            self.proj_out_store.attrs['output_key'] = output_key

        # reference batch onehot
        self.reference_batch_onehot = self._get_ref_batch_onehot(self.root_zarr, reference_batch) \
            if reference_batch is not None else None
        if self.mode == "conditional" and self.reference_batch is None:
            raise ValueError("conditional mode requires reference_batch to be set.")


    def _dynamic_batch_generator(self):
        current_batch = []
        current_cells = 0

        for comb in self.all_combs:
            cell_count = self.root_zarr[comb][self.output_key].shape[0]
            if len(current_batch) < self.batch_size and (current_cells + cell_count) <= self.max_cells:
                current_batch.append(comb)
                current_cells += cell_count
            else:
                if cell_count > self.max_cells and current_batch:
                    yield current_batch
                    current_batch = [comb]
                    current_cells = cell_count
                elif len(current_batch) >= self.batch_size:
                    yield current_batch
                    current_batch = [comb]
                    current_cells = cell_count
                elif (current_cells + cell_count) > self.max_cells:
                    yield current_batch
                    current_batch = [comb]
                    current_cells = cell_count

        if current_batch:
            yield current_batch


    def _write_pred_to_zarr(self, ref_batch_name: str, comb: str, arr: np.ndarray):
        if self.proj_out_store is None:
            return
        grp_ref = self.proj_out_store.require_group(ref_batch_name)
        grp = grp_ref.require_group(comb)

        arr = np.asarray(arr, dtype=np.float32)
        chunks = (min(10_000, arr.shape[0]), arr.shape[1])
        compressor = Blosc(cname='zstd', clevel=5, shuffle=Blosc.BITSHUFFLE)
        dset = grp.create_dataset(
            self.output_key,
            shape=arr.shape,
            dtype=arr.dtype,
            chunks=chunks,
            compressor=compressor,
        )
        dset[:] = arr

    @staticmethod
    def _get_ref_batch_onehot(root_zarr: Any, ref_batch) -> np.ndarray:
        ref_batch_onehot = np.array(root_zarr.attrs['batch_to_onehot'][ref_batch]).astype(np.int64)
        return ref_batch_onehot

    @staticmethod
    def _get_reference_batch(root_zarr: Any,
                             reference_batch: str,
                             comb: str,
                             dataset: str,
                             output_key: str) -> Tuple[np.ndarray, str | None, bool]:
        split_key = comb.split('-')
        if dataset == 'hlca':
            reference_batch_key = split_key[0] + '-' + reference_batch
        else:
            print('Unknown dataset for reference batch handling.')
            raise ValueError('Unknown dataset for reference batch handling.')

        if reference_batch in comb:
            x_ref = root_zarr[comb][output_key][:]
            return x_ref, comb, True
        elif reference_batch_key in root_zarr:
            x_ref = root_zarr[reference_batch_key][output_key][:]
            return x_ref, reference_batch_key, True
        else:
            warnings.warn(
                f"Reference batch {reference_batch_key} not found in data. "
                f"Using {comb} itself as reference."
            )
            return root_zarr[comb][output_key][:], None, False

    def _load_batch_data(self, batch: List[str]) -> Tuple[np.ndarray, List[Tuple[str, int, int]]]:
        all_x = []
        comb_indices: List[Tuple[str, int, int]] = []

        start_idx = 0
        for comb in batch:
            x = self.root_zarr[comb][self.input_key][:]
            n_cells = x.shape[0]
            all_x.append(x)
            comb_indices.append((comb, start_idx, start_idx + n_cells))
            start_idx += n_cells

        x_combined = np.concatenate(all_x, axis=0)
        return x_combined, comb_indices

    def _load_decode_data(self, batch: List[str]) -> Tuple[np.ndarray, np.ndarray, List[Tuple[str, int, int]]]:
        if self.emb_root_zarr is None:
            raise ValueError("emb_zarr_path is required for decode mode.")

        all_z, all_x = [], []
        comb_indices: List[Tuple[str, int, int]] = []

        start_idx = 0
        for comb in batch:
            z = self.emb_root_zarr[comb][self.input_key][:]
            x = self.root_zarr[comb][self.output_key][:]
            n_cells = x.shape[0]
            all_z.append(z)
            all_x.append(x)
            comb_indices.append((comb, start_idx, start_idx + n_cells))
            start_idx += n_cells

        z_combined = np.concatenate(all_z, axis=0)
        x_combined = np.concatenate(all_x, axis=0)
        return z_combined, x_combined, comb_indices

    def _load_ref_data(self, batch: List[str]) -> Tuple[np.ndarray, List[Tuple[str, int, int]], List[bool]]:
        """
        Load reference data for each combination in the batch.
        Returns all_ref (concatenated), ref_indices, if_ref_labels.
        """
        all_ref = []
        ref_indices: List[Tuple[str | None, int, int]] = []
        if_ref_labels: List[bool] = []

        start_idx = 0
        for comb in batch:
            x_ref, ref_comb, if_ref = self._get_reference_batch(
                self.root_zarr, self.reference_batch, comb, self.dataset, self.output_key
            )
            n_cells = x_ref.shape[0]
            ref_indices.append((ref_comb, start_idx, start_idx + n_cells))
            start_idx += n_cells

            all_ref.append(x_ref)
            if_ref_labels.append(if_ref)

        all_ref = np.concatenate(all_ref, axis=0)

        if self.ref_transform == 'proportional':
            all_ref = all_ref / np.sum(all_ref, axis=1, keepdims=True)

        return all_ref, ref_indices, if_ref_labels

    def preprocessing_batch(self, x: np.ndarray) -> np.ndarray:
        """Low-level preprocessing: default只做 gene filtering."""
        if self.filtered_var_indices is not None:
            x = x[:, self.filtered_var_indices]
        return x

    def _preprocess_for_metrics(self,
                                x: np.ndarray,
                                recon: np.ndarray) -> Tuple[np.ndarray, np.ndarray]:
        x = self.preprocessing_batch(x)
        recon = self.preprocessing_batch(recon)
        return x, recon


    def _run_predict(self, x_combined: np.ndarray) -> np.ndarray:
        if x_combined.shape[0] > self.minibatch_size:
            warnings.warn(
                f"Large batch size {x_combined.shape[0]} may lead to high memory usage."
            )
            parts = []
            for start in range(0, x_combined.shape[0], self.minibatch_size):
                end = min(start + self.minibatch_size, x_combined.shape[0])
                parts.append(self.model.predict(x_combined[start:end]))
            recon_combined = np.vstack(parts)
        else:
            recon_combined = self.model.predict(x_combined)
        return recon_combined

    def _run_decode(self, z_combined: np.ndarray) -> np.ndarray:
        if z_combined.shape[0] > self.minibatch_size:
            warnings.warn(
                f"Large batch size {z_combined.shape[0]} may lead to high memory usage."
            )
            parts = []
            for start in range(0, z_combined.shape[0], self.minibatch_size):
                end = min(start + self.minibatch_size, z_combined.shape[0])
                parts.append(self.model.decode(z_combined[start:end]))
            recon_combined = np.vstack(parts)
        else:
            recon_combined = self.model.decode(z_combined)
        return recon_combined

    def _run_conditional_decode(self,
                                x_combined: np.ndarray,
                                ref_batch_onehot: np.ndarray) -> np.ndarray:
        if x_combined.shape[0] > self.minibatch_size:
            warnings.warn(
                f"Large batch size {x_combined.shape[0]} may lead to high memory usage."
            )
            parts = []
            for start in range(0, x_combined.shape[0], self.minibatch_size):
                end = min(start + self.minibatch_size, x_combined.shape[0])
                parts.append(
                    self.model.decode(x_combined[start:end], ref_batch_onehot[start:end])
                )
            recon_combined = np.vstack(parts)
        else:
            # TODO: loglib size - bugging here
            recon_combined = self.model.decode(x_combined, ref_batch_onehot)
        return recon_combined


    def _compute_metrics_batch(self, results: List[tuple]) -> List[Dict]:
        """
        results: List[(comb, comb_ref, x, recon)]
        """
        worker = partial(compute_func_metrics, self.metric_funcs, self.split_key)
        batch_results = list(self.pool.imap(worker, results, chunksize=20))
        return batch_results


    def _process_batch_decode(self, batch: List[str]) -> List[Dict]:
        z_combined, x_combined, comb_indices = self._load_decode_data(batch)
        recon_combined = self._run_decode(z_combined)

        x_combined, recon_combined = self._preprocess_for_metrics(
            x_combined, recon_combined
        )

        results = []
        for comb, start, end in comb_indices:
            x_comb = x_combined[start:end]
            recon_comb = recon_combined[start:end]
            results.append((comb, None, x_comb, recon_comb))

        batch_results = self._compute_metrics_batch(results)
        del z_combined, x_combined, recon_combined, results
        return batch_results

    def _process_batch_reconstruction(self, batch: List[str]) -> List[Dict]:
        x_combined, comb_indices = self._load_batch_data(batch)
        recon_combined = self._run_predict(x_combined)

        x_combined, recon_combined = self._preprocess_for_metrics(
            x_combined, recon_combined
        )

        results = []
        for comb, start, end in comb_indices:
            x_comb = x_combined[start:end]
            recon_comb = recon_combined[start:end]
            results.append((comb, None, x_comb, recon_comb))

        batch_results = self._compute_metrics_batch(results)
        del x_combined, recon_combined, results
        return batch_results

    def _process_batch_conditional(self, batch: List[str]) -> List[Dict]:
        """
        process batch for batch cross-projection performance
        """
        x_combined, comb_indices = self._load_batch_data(batch)
        all_ref, ref_indices, if_ref_labels = self._load_ref_data(batch)

        ref_batch_onehot = np.tile(self.reference_batch_onehot,
                                   (x_combined.shape[0], 1))

        recon_combined = self._run_conditional_decode(x_combined, ref_batch_onehot)

        results = []
        for (comb, start, end), (ref_comb, ref_start, ref_end), is_true_ref in zip(
            comb_indices, ref_indices, if_ref_labels
        ):
            if not is_true_ref:
                warnings.warn(
                    f"Reference batch {self.reference_batch} not found for combination "
                    f"{comb}. Skipping this combination."
                )
                continue

            x_ref_comb = all_ref[ref_start:ref_end]
            recon_comb = recon_combined[start:end]

            # preprocess reference & prediction for metrics
            x_ref_comb, recon_comb = self._preprocess_for_metrics(
                x_ref_comb, recon_comb
            )

            if self.proj_out_store is not None:
                self._write_pred_to_zarr(self.reference_batch, comb, recon_comb)

            results.append((comb, ref_comb, x_ref_comb, recon_comb))

        batch_results = self._compute_metrics_batch(results)
        del x_combined, all_ref, recon_combined, results
        return batch_results

    def _process_batch(self, batch: List[str]) -> List[Dict]:
        if self.mode == "reconstruction":
            return self._process_batch_reconstruction(batch)
        elif self.mode == "decode":
            return self._process_batch_decode(batch)
        elif self.mode == "conditional":
            return self._process_batch_conditional(batch)
        else:
            raise ValueError(f"Unknown mode: {self.mode}")


    def run(self, output_path: str):
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        if os.path.exists(output_path):
            os.remove(output_path)
            print(f"Existing output file {output_path} removed.")

        columns = [
            "combination",
            "combination_ref",
            *self.split_key,
            "n_cells",
            "n_cells_recon",
            *list(self.metric_funcs.keys()),
        ]
        pd.DataFrame(columns=columns).to_csv(output_path, index=False)

        batch_gen = self._dynamic_batch_generator()
        with tqdm(total=len(self.all_combs), desc="Total progress") as pbar:
            for batch in batch_gen:
                batch_results = self._process_batch(batch)
                pd.DataFrame(batch_results, columns=columns).to_csv(
                    output_path, mode='a', header=False, index=False
                )
                pbar.update(len(batch))
                del batch_results
                gc.collect()

        self.pool.close()
        self.pool.join()
        print(f"Processing completed. Results saved to {output_path}")


def compute_func_metrics(metric_funcs: Dict,
                         split_key: list[str],
                         args: tuple) -> Dict:
    """
    Keep the original signature for backward compatibility.
    args: (comb, comb_ref, x, recon)
    """
    comb, comb_ref, x, recon = args
    comb_keys = comb.split('-')
    metrics = {
        "combination": comb,
        "combination_ref": comb_ref,  # None if self reference
        split_key[0]: comb_keys[0],
        split_key[1]: comb_keys[1] if len(comb_keys) > 1 else 'None',
        split_key[2]: comb_keys[2] if len(comb_keys) > 2 else 'None',
        "n_cells": x.shape[0],
        "n_cells_recon": recon.shape[0],
    }
    for name, func in metric_funcs.items():
        metrics[name] = func(x, recon)
    return metrics
