"""Write LuCA gene symbols and Ensembl IDs in expression-column order.

scConcept and Geneformer need Ensembl IDs. The output can be the expression
store itself, as in custom_datasets_demo; existing arrays are preserved.
"""

import argparse

import h5py
import zarr
from anndata.io import read_elem


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--expression-zarr", required=True)
    parser.add_argument("--source-h5ad", default="data/luca/core_250130.h5ad")
    parser.add_argument("--out", required=True)
    args = parser.parse_args()

    with h5py.File(args.source_h5ad, "r") as source:
        var = read_elem(source["var"])
    gene_ids = dict(zip(var["feature_name"], var.index))
    genes = list(zarr.open(args.expression_zarr, mode="r").attrs["var_names"])

    out = zarr.open_group(args.out, mode="a")
    out.attrs["var_names"] = genes
    out.attrs["var_ensembl_ids_38"] = [gene_ids[gene].split(".")[0] for gene in genes]
    print(f"Wrote {len(genes)} gene IDs to {args.out}")


if __name__ == "__main__":
    main()
