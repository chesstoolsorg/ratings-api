"""Vendored ChessTools shell: nav/footer fragments and static assets for HTML pages."""

import os
from pathlib import Path


def _ratings_api_root() -> Path:
    return Path(__file__).resolve().parent.parent


_ROOT = Path(os.environ.get("RATINGS_API_ROOT", _ratings_api_root()))
_STATIC_CHESSTOOLS = Path(os.environ.get("CHESSTOOLS_UI_STATIC", _ROOT / "static" / "chesstools"))
_TEMPLATES_CHESSTOOLS = Path(os.environ.get("CHESSTOOLS_UI_TEMPLATES", _ROOT / "templates" / "chesstools"))


def _read_fragment(name: str) -> str:
    path = _TEMPLATES_CHESSTOOLS / name
    return path.read_text(encoding="utf-8")


def static_dir() -> Path:
    return _STATIC_CHESSTOOLS


def nav_html() -> str:
    return _read_fragment("nav.html")


def footer_html() -> str:
    return _read_fragment("footer.html")
