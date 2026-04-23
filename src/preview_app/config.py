import os
from pathlib import Path


APP_NAME = "preview_app"


def _xdg(env_var: str, fallback: Path) -> Path:
    value = os.environ.get(env_var)
    return Path(value) if value else fallback


def data_dir() -> Path:
    base = _xdg("XDG_DATA_HOME", Path.home() / ".local" / "share")
    return base / APP_NAME


def cache_dir() -> Path:
    base = _xdg("XDG_CACHE_HOME", Path.home() / ".cache")
    return base / APP_NAME


def signatures_dir() -> Path:
    return data_dir() / "signatures"


def ocr_cache_dir() -> Path:
    return cache_dir() / "ocr"


def project_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resources_dir() -> Path:
    return project_root() / "resources"


def fonts_dir() -> Path:
    return resources_dir() / "fonts"


def ensure_dirs() -> None:
    for d in (data_dir(), signatures_dir(), cache_dir(), ocr_cache_dir()):
        d.mkdir(parents=True, exist_ok=True)
