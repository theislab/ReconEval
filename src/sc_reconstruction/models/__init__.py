"""Reconstruction model wrappers.

End-to-end models (PCA, AE, scVI, nlscVI, mlscVI, KNN) need only
``cstm_scvi_env``. Foundation-model wrappers (``ReconPretrained*``)
each require their own conda env because the underlying FM packages
ship mutually-incompatible torch / CUDA / flash-attn stacks. See
``envs/`` for the matching environment files.

Each class is imported with a ``try/except`` guard so the package
stays importable in any env even when a particular backend package
is not installed. Failures are logged to ``stderr`` rather than
silently swallowed — this is how a "missing class" symptom in
sphinx/RTD surfaces a root cause in the build log instead of being
invisible. Broad except catches both ``ImportError`` (backend not
installed) and ``Exception`` (backend installed but broken at load
time — e.g. torchtext / scgpt with mismatched torch versions,
flash-attn with the wrong CUDA).
"""

import sys as _sys

from ._base_model import BaseReconstructionModel

__all__ = ["BaseReconstructionModel"]


def _try_import(modname: str, attr: str) -> None:
    """Import ``attr`` from ``.{modname}`` into this namespace and append to ``__all__``.

    On failure, log to stderr with the exception type + message so the
    cause is visible in CI / sphinx-build / RTD logs. Never raises.
    """
    try:
        module = __import__(f"{__name__}.{modname}", fromlist=[attr])
        globals()[attr] = getattr(module, attr)
        __all__.append(attr)
    except Exception as e:  # noqa: BLE001 — intentional broad except, see docstring
        print(
            f"[sc_reconstruction.models] {attr} unavailable: {type(e).__name__}: {e}",
            file=_sys.stderr,
        )


# End-to-end models — guarded so the package stays importable in any env.
_try_import("reconpca", "ReconPCA")
_try_import("reconae", "ReconAE")
_try_import("reconscvi", "ReconSCVI")
_try_import("reconnlscvi", "ReconNLSCVI")
_try_import("reconmlscvi", "ReconMLSCVI")
_try_import("reconknn", "ReconKNN")

# Foundation-model wrappers — each requires its own env at runtime.
_try_import("reconse", "ReconPretrainedStateModel")
_try_import("reconscgpt", "ReconPretrainedscGPT")
_try_import("reconscconcept", "ReconPretrainedscConcept")
_try_import("reconscimilarity", "ReconPretrainedscimilarity")
_try_import("recongeneformer", "ReconPretrainedGeneformer")
_try_import("reconuce", "ReconPretrainedUCE")
_try_import("reconscfoundation", "ReconPretrainedscFoundation")
