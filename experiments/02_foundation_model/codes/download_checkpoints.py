"""Download pretrained foundation models using the reconeval environment."""

import argparse
from pathlib import Path
import socket
import tarfile
import time
from urllib.error import HTTPError, URLError
from urllib.request import urlretrieve

from huggingface_hub import snapshot_download


# repo_id, allow_patterns, optional subdirectory returned as checkpoint_dir
HF_MODELS = {
    "SE":        ("arcinstitute/SE-600M",  ["se600m_epoch16.ckpt", "protein_embeddings.pt"], None),
    "scGPT":     ("wanglab/scGPT-human",   ["best_model.pt", "args.json", "vocab.json"],      None),
    "scConcept": ("theislab/scConcept",    ["Corpus-30M/*"],                                  "Corpus-30M"),
}

SCIMILARITY_URL = "https://zenodo.org/records/10685499/files/model_v1.1.tar.gz?download=1"
SCIMILARITY_FILES = [
    "encoder.ckpt", "decoder.ckpt", "gene_order.tsv",
    "hyperparameters.json", "layer_sizes.json", "metadata.json", "label_ints.csv",
]


class URLDownloader:
    """Download with urlretrieve, retrying temporary failures.

    ``retries`` counts attempts after the first. ``timeout`` and
    ``retry_delay`` are in seconds; timeout applies to blocking socket
    operations, not the whole download. Use sequentially: urlretrieve
    requires temporarily changing the process-wide socket default.
    """

    def __init__(self, retries: int = 3, timeout: float = 60, retry_delay: float = 10):
        if retries < 0 or timeout <= 0 or retry_delay < 0:
            raise ValueError("retries and retry_delay must be non-negative; timeout must be positive")
        self.retries = retries
        self.timeout = timeout
        self.retry_delay = retry_delay

    def download(self, url: str, destination: Path) -> Path:
        destination = Path(destination)
        destination.parent.mkdir(parents=True, exist_ok=True)
        partial = destination.with_name(destination.name + ".part")
        previous_timeout = socket.getdefaulttimeout()
        try:
            socket.setdefaulttimeout(self.timeout)
            for attempt in range(self.retries + 1):
                try:
                    urlretrieve(url, partial)
                except (URLError, TimeoutError, ConnectionError) as error:
                    if isinstance(error, HTTPError) and error.code not in (408, 429, 500, 502, 503, 504):
                        raise
                    if attempt == self.retries:
                        raise
                    print(
                        f"Download failed: {error}. Retrying in {self.retry_delay}s "
                        f"({attempt + 1}/{self.retries})...",
                        flush=True,
                    )
                    time.sleep(self.retry_delay)
                else:
                    partial.replace(destination)
                    return destination
        finally:
            socket.setdefaulttimeout(previous_timeout)



def download_huggingface(model: str, directory: Path) -> Path:
    repo_id, files, subdir = HF_MODELS[model]
    snapshot_download(repo_id=repo_id, allow_patterns=files, local_dir=directory)
    return directory / subdir if subdir else directory


def download_scimilarity(directory: Path) -> Path:
    checkpoint_dir = directory / "model_v1.1"
    expected = [checkpoint_dir / name for name in SCIMILARITY_FILES]
    if all(f.is_file() and f.stat().st_size > 0 for f in expected):
        return checkpoint_dir

    archive = directory / "model_v1.1.tar.gz"
    if not archive.is_file():
        downloader = URLDownloader(retries=3, timeout=60, retry_delay=10)
        downloader.download(SCIMILARITY_URL, archive)

    # Extract only model files; the archive also contains a large cell-search index.
    print("Extracting SCimilarity checkpoint files...", flush=True)
    tar_members = {f"model_v1.1/{name}" for name in SCIMILARITY_FILES}
    with tarfile.open(archive, mode="r|gz") as tar:
        tar.extractall(
            path=directory,
            members=(m for m in tar if m.name.removeprefix("./") in tar_members),
            filter="data",
        )

    missing = [f for f in expected if not f.is_file() or f.stat().st_size == 0]
    if missing:
        raise FileNotFoundError(f"Extraction incomplete, missing files: {missing}")
    return checkpoint_dir


def main() -> None:
    all_models = ["SE", "scGPT", "scConcept", "scimilarity"]
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--model", required=True, choices=all_models + ["all"])
    parser.add_argument("--output-dir", type=Path, default=Path("checkpoints/pretrained"))
    args = parser.parse_args()

    output_dir = args.output_dir.expanduser().resolve()
    models = all_models if args.model == "all" else [args.model]
    for model in models:
        directory = output_dir / model
        directory.mkdir(parents=True, exist_ok=True)
        print(f"Preparing {model} in {directory}...", flush=True)

        if model == "scimilarity":
            checkpoint_dir = download_scimilarity(directory)
        else:
            checkpoint_dir = download_huggingface(model, directory)

        print(f"\n{model} embedding overrides:")
        if model == "SE":
            print(f"model_args.checkpoint_path={checkpoint_dir / 'se600m_epoch16.ckpt'}")
            print(f"model_args.protein_embeds_path={checkpoint_dir / 'protein_embeddings.pt'}")
        else:
            print(f"model_args.checkpoint_path={checkpoint_dir}")


if __name__ == "__main__":
    main()
