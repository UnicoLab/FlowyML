"""Materializer for PyMC / Bayesian artifacts (ArviZ ``InferenceData``).

Serializes posterior traces to NetCDF (ArviZ's native, portable format) so they
round-trip faithfully across environments.  Registered only when ``arviz`` is
installed; otherwise PyMC objects fall back to the cloudpickle materializer.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from flowyml.storage.materializers.base import BaseMaterializer, register_materializer

try:
    import arviz as az

    ARVIZ_AVAILABLE = True
except ImportError:
    ARVIZ_AVAILABLE = False


if ARVIZ_AVAILABLE:

    class PyMCMaterializer(BaseMaterializer):
        """Materializer for ArviZ ``InferenceData`` (PyMC/Bayesian traces)."""

        def save(self, obj: Any, path: Path) -> None:
            path.mkdir(parents=True, exist_ok=True)
            az.to_netcdf(obj, str(path / "inference.nc"))

        def load(self, path: Path) -> Any:
            nc = path / "inference.nc" if path.is_dir() else path
            return az.from_netcdf(str(nc))

        @classmethod
        def supported_types(cls) -> list[type]:
            return [az.InferenceData]

    register_materializer(PyMCMaterializer)

else:

    class PyMCMaterializer(BaseMaterializer):
        """Placeholder when ArviZ is not installed."""

        def save(self, obj: Any, path: Path) -> None:
            raise ImportError("arviz is required for PyMCMaterializer. Install with: pip install arviz pymc")

        def load(self, path: Path) -> Any:
            raise ImportError("arviz is required for PyMCMaterializer. Install with: pip install arviz pymc")

        @classmethod
        def supported_types(cls) -> list[type]:
            return []
