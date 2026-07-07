"""Shared path helpers for tests that reach outside ``src/``."""

from pathlib import Path


def repo_root() -> Path:
    """Return the repository root (directory containing ``pyproject.toml``)."""
    path = Path(__file__).resolve()
    for parent in path.parents:
        if (parent / "pyproject.toml").exists():
            return parent
    msg = "Repository root not found (no pyproject.toml in parent directories)."
    raise RuntimeError(msg)
