"""Application data path resolution."""

from __future__ import annotations

import os
import sys
from pathlib import Path

APP_NAME = "fathom-play"
DATA_ROOT_ENV = "FATHOM_PLAY_DATA_DIR"


def default_data_root(app_name: str = APP_NAME) -> Path:
    """Return the platform-appropriate user data directory."""
    override = os.getenv(DATA_ROOT_ENV)
    if override:
        return Path(override).expanduser()

    if sys.platform == "darwin":
        return Path.home() / "Library" / "Application Support" / app_name

    if sys.platform.startswith("win"):
        base = os.getenv("LOCALAPPDATA") or os.getenv("APPDATA")
        if base:
            return Path(base) / app_name
        return Path.home() / "AppData" / "Local" / app_name

    xdg_data_home = os.getenv("XDG_DATA_HOME")
    if xdg_data_home:
        return Path(xdg_data_home).expanduser() / app_name
    return Path.home() / ".local" / "share" / app_name
