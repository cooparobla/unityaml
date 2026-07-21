"""Shared fixtures for unityaml_gui tests.

A single QApplication must exist for the entire test session — pytest-qt
provides the `qapp` fixture for this, but we layer some project-specific
helpers on top of it.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from unityaml.app_state import AppState
from unityaml.project import ProjectConfig


# ──────────────────────────────────────────────────────────────────────────────
# Persistence redirection (keep tests isolated from ~/.unityaml)
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _isolate_persistence(tmp_path, monkeypatch):
    """Redirect all persistence paths into tmp_path for every GUI test."""
    from unityaml import persistence

    monkeypatch.setattr(persistence, "unityaml_root", lambda: tmp_path / "unityaml")
    monkeypatch.setattr(
        persistence, "projects_root", lambda: tmp_path / "unityaml" / "projects"
    )

    def patched_project_dir(self):
        return tmp_path / "unityaml" / "projects" / self.name.lower().replace(" ", "_")

    monkeypatch.setattr(ProjectConfig, "project_dir", property(patched_project_dir))
    monkeypatch.setattr(
        ProjectConfig,
        "project_yaml_path",
        property(lambda self: patched_project_dir(self) / "project.yaml"),
    )

    # Also redirect AppSettings to tmp
    from unityaml_gui import settings as _settings_mod
    monkeypatch.setattr(
        _settings_mod,
        "_settings_path",
        lambda: tmp_path / "unityaml" / "settings.yaml",
    )


# ──────────────────────────────────────────────────────────────────────────────
# Convenience factories
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def asset_root(tmp_path) -> Path:
    """An empty directory to use as the asset root."""
    root = tmp_path / "assets"
    root.mkdir()
    return root


@pytest.fixture
def app_state(asset_root) -> AppState:
    """A fresh AppState backed by the isolated tmp asset_root."""
    return AppState(asset_root=asset_root)


@pytest.fixture
def project_factory(app_state, tmp_path):
    """Return a callable that creates and registers a ProjectConfig."""

    def _make(name: str) -> ProjectConfig:
        proj = ProjectConfig(name=name, created=datetime(2026, 1, 1))
        proj.project_dir.mkdir(parents=True, exist_ok=True)
        app_state.add_project(proj)
        return proj

    return _make
