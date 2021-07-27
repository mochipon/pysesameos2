"""Top-level package for pysesameos2."""
try:
    import importlib.metadata as importlib_metadata
except ModuleNotFoundError:  # pragma: no cover
    import importlib_metadata  # type: ignore

__author__ = """Masaki Tagawa"""
__version__ = importlib_metadata.version(__name__)
