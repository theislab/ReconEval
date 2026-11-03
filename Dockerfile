# syntax=docker/dockerfile:1
# Base image
ARG BASE_IMAGE=quay.io/condaforge/miniforge3@sha256:be01a3e63d4af20d8a9937d1e12fa299d1c572edf601b961180a59c78bd7250d
FROM ${BASE_IMAGE} AS base

ENV PYTHONUNBUFFERED=1 \
    PYTHONNOUSERSITE=1 \
    PIP_NO_CACHE_DIR=1 \
    MPLBACKEND=Agg \
    HNSWLIB_NO_NATIVE=1

# Rootless builds may map only one UID.
RUN apt-get -o APT::Sandbox::User=root update \
    && apt-get -o APT::Sandbox::User=root install -y --no-install-recommends \
       ca-certificates git build-essential pkg-config libgomp1 libglib2.0-0 libgl1 \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /opt/ReconEval

# Repository
COPY pyproject.toml README.rst LICENSE ./
COPY src/ ./src/
COPY experiments/ ./experiments/
COPY tutorials/ ./tutorials/
COPY docker/setup.sh ./docker/setup.sh

ENTRYPOINT ["/opt/conda/bin/conda", "run", "--no-capture-output"]
CMD ["-n", "reconeval", "python", "--version"]

# Environments
FROM base AS metrics
COPY envs/requirements-min.txt ./envs/
RUN bash docker/setup.sh envs/requirements-min.txt reconeval-metrics
CMD ["-n", "reconeval-metrics", "python", "--version"]

FROM base AS core
COPY envs/cstm_scvi_env.yaml ./envs/
RUN bash docker/setup.sh envs/cstm_scvi_env.yaml reconeval

FROM base AS scgpt
COPY envs/scgpt.yaml ./envs/
COPY docker/scgpt_overrides.yaml docker/scgpt_requirements.txt ./docker/
RUN bash docker/setup.sh envs/scgpt.yaml reconeval-scgpt docker/scgpt_overrides.yaml
CMD ["-n", "reconeval-scgpt", "python", "--version"]

FROM base AS state
COPY envs/state_env.yaml ./envs/
COPY docker/state_overrides.yaml ./docker/
# Supply the CUDA capability to Conda when building on a CPU node.
RUN CONDA_OVERRIDE_CUDA=12.6 bash docker/setup.sh \
    envs/state_env.yaml reconeval-state docker/state_overrides.yaml
CMD ["-n", "reconeval-state", "python", "--version"]

FROM base AS scconcept
COPY envs/scconcept_env.yaml ./envs/
COPY docker/scconcept_overrides.yaml ./docker/
RUN CONDA_OVERRIDE_CUDA=12.6 bash docker/setup.sh \
    envs/scconcept_env.yaml reconeval-scconcept docker/scconcept_overrides.yaml
CMD ["-n", "reconeval-scconcept", "python", "--version"]

FROM base AS scimilarity
COPY envs/scimilarity_env.yaml ./envs/
RUN bash docker/setup.sh envs/scimilarity_env.yaml reconeval-scimilarity
CMD ["-n", "reconeval-scimilarity", "python", "--version"]

FROM base AS cellflow
COPY envs/pancellflow.yaml ./envs/
COPY docker/cellflow_overrides.yaml ./docker/
RUN bash docker/setup.sh envs/pancellflow.yaml reconeval-pancellflow docker/cellflow_overrides.yaml
CMD ["-n", "reconeval-pancellflow", "python", "--version"]

# Combined image
FROM base AS all
COPY --from=metrics /opt/conda/envs/reconeval-metrics /opt/conda/envs/reconeval-metrics
COPY --from=core /opt/conda/envs/reconeval /opt/conda/envs/reconeval
COPY --from=scgpt /opt/conda/envs/reconeval-scgpt /opt/conda/envs/reconeval-scgpt
COPY --from=state /opt/conda/envs/reconeval-state /opt/conda/envs/reconeval-state
COPY --from=scconcept /opt/conda/envs/reconeval-scconcept /opt/conda/envs/reconeval-scconcept
COPY --from=scimilarity /opt/conda/envs/reconeval-scimilarity /opt/conda/envs/reconeval-scimilarity
COPY --from=cellflow /opt/conda/envs/reconeval-pancellflow /opt/conda/envs/reconeval-pancellflow
