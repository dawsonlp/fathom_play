"""Fathom.ai API exploration and tooling."""

from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("fathom-play")
except PackageNotFoundError:
    __version__ = "dev"

