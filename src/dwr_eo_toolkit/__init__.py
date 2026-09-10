"""DWR Earth Observation Toolkit.

Top-level names are resolved lazily (PEP 562). Importing this package, or any
subpackage, no longer drags in the dependency chain of every other subpackage:
`from dwr_eo_toolkit.filters import Query` used to require apscheduler because
this module imported DownloadManager eagerly.

    from dwr_eo_toolkit import EarthAccessProvider   # needs [base]
    from dwr_eo_toolkit import DownloadManager       # needs [scheduler]
"""

from typing import TYPE_CHECKING

__version__ = "0.4.0"

# name -> (module path, extra that provides its dependencies)
_LAZY: dict[str, tuple[str, str | None]] = {
    "EarthDataLoginAuth": ("dwr_eo_toolkit.core.auth", None),
    "EarthAccessProvider": ("dwr_eo_toolkit.providers", None),
    "DownloadManager": ("dwr_eo_toolkit.download_manager", "scheduler"),
}

__all__ = list(_LAZY)

if TYPE_CHECKING:  # keeps mypy and IDE completion working
    from dwr_eo_toolkit.core.auth import EarthDataLoginAuth
    from dwr_eo_toolkit.download_manager import DownloadManager
    from dwr_eo_toolkit.providers import EarthAccessProvider


def __getattr__(name: str):
    try:
        module_path, extra = _LAZY[name]
    except KeyError:
        raise AttributeError(f"module {__name__!r} has no attribute {name!r}") from None
    import importlib

    try:
        return getattr(importlib.import_module(module_path), name)
    except ModuleNotFoundError as exc:
        if extra and not str(exc).startswith("No module named 'dwr_eo_toolkit"):
            raise ModuleNotFoundError(
                f"{name} requires the '{extra}' extra. Install it with:\n"
                f"    pip install 'dwr-eo-toolkit[{extra}]'\n"
                f"(missing dependency: {exc.name})"
            ) from exc
        raise


def __dir__() -> list[str]:
    return sorted(__all__)
