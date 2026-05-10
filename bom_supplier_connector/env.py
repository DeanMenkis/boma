"""
Load `.env` so DigiKey, CLōD, AllScale, and other keys are available on `os.environ`.

Search order (first existing file wins; existing shell vars are not overwritten):
1. `BOM_ENV_FILE` or `DOTENV_PATH` if set
2. `<repo>/.claude/worktrees/lucid-archimedes-e6fe3f/.env` (team worktree)
3. `<repo>/.env`

Set `BOM_SKIP_DOTENV=1` to skip loading.
"""
from __future__ import annotations

import os
from pathlib import Path

_PACKAGE_DIR = Path(__file__).resolve().parent
_REPO_ROOT = _PACKAGE_DIR.parent


def _candidate_env_files() -> list[Path]:
    explicit = os.getenv("BOM_ENV_FILE") or os.getenv("DOTENV_PATH")
    paths: list[Path] = []
    if explicit:
        paths.append(Path(explicit).expanduser())
    paths.append(
        _REPO_ROOT
        / ".claude"
        / "worktrees"
        / "lucid-archimedes-e6fe3f"
        / ".env"
    )
    paths.append(_REPO_ROOT / ".env")
    return paths


def load_connector_env() -> Path | None:
    """
    Load the first existing env file from candidates.
    Returns the path loaded, or None if skipped / python-dotenv missing.
    """
    if os.getenv("BOM_SKIP_DOTENV"):
        return None
    try:
        from dotenv import load_dotenv
    except ImportError:
        return None

    for path in _candidate_env_files():
        if path.is_file():
            load_dotenv(path, override=False)
            return path
    return None
