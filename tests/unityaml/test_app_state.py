"""Tests for unityaml.app_state — AppState and create_app_state."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from unityaml.app_state import DEFAULT_FILTER, AppState, create_app_state
from unityaml.project import ProjectConfig


# ──────────────────────────────────────────────────────────────────────────────
# Fixture — redirect persistence
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _redirect(tmp_path, monkeypatch):
    from unityaml import persistence

    monkeypatch.setattr(persistence, "unityaml_root", lambda: tmp_path / "unityaml")
    monkeypatch.setattr(
        persistence, "projects_root", lambda: tmp_path / "unityaml" / "projects"
    )

    def patched_dir(self):
        return tmp_path / "unityaml" / "projects" / self.name.lower().replace(" ", "_")

    monkeypatch.setattr(ProjectConfig, "project_dir", property(patched_dir))
    monkeypatch.setattr(
        ProjectConfig,
        "project_yaml_path",
        property(lambda self: patched_dir(self) / "project.yaml"),
    )


# ──────────────────────────────────────────────────────────────────────────────
# DEFAULT_FILTER
# ──────────────────────────────────────────────────────────────────────────────


class TestDefaultFilter:
    def test_contains_blend(self):
        assert ".blend" in DEFAULT_FILTER

    def test_contains_yaml(self):
        assert ".yaml" in DEFAULT_FILTER

    def test_contains_json(self):
        assert ".json" in DEFAULT_FILTER

    def test_contains_png(self):
        assert ".png" in DEFAULT_FILTER


# ──────────────────────────────────────────────────────────────────────────────
# AppState construction
# ──────────────────────────────────────────────────────────────────────────────


class TestAppState:
    def test_asset_root_stored(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        assert state.asset_root == tmp_path

    def test_default_file_filter(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        assert state.file_filter == DEFAULT_FILTER

    def test_custom_file_filter(self, tmp_path):
        state = AppState(asset_root=tmp_path, file_filter=[".blend"])
        assert state.file_filter == [".blend"]

    def test_default_projects_empty(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        assert state.projects == []

    def test_default_active_project_none(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        assert state.active_project is None


# ──────────────────────────────────────────────────────────────────────────────
# AppState.get_project
# ──────────────────────────────────────────────────────────────────────────────


class TestGetProject:
    def _state_with(self, *names, root=Path("/tmp")):
        state = AppState(asset_root=root)
        for name in names:
            state.projects.append(ProjectConfig(name=name, created=datetime.now()))
        return state

    def test_get_existing_project(self, tmp_path):
        state = self._state_with("Alpha", "Beta", root=tmp_path)
        result = state.get_project("Alpha")
        assert result is not None
        assert result.name == "Alpha"

    def test_get_missing_project_returns_none(self, tmp_path):
        state = self._state_with("Alpha", root=tmp_path)
        assert state.get_project("Nonexistent") is None

    def test_get_is_case_sensitive(self, tmp_path):
        state = self._state_with("Alpha", root=tmp_path)
        assert state.get_project("alpha") is None

    def test_get_from_empty_projects(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        assert state.get_project("Anything") is None


# ──────────────────────────────────────────────────────────────────────────────
# AppState.add_project
# ──────────────────────────────────────────────────────────────────────────────


class TestAddProject:
    def test_adds_to_list(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        proj = ProjectConfig(name="NewGame", created=datetime.now())
        proj.project_dir.mkdir(parents=True, exist_ok=True)
        state.add_project(proj)
        assert len(state.projects) == 1

    def test_saves_to_disk(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        proj = ProjectConfig(name="Saved", created=datetime.now())
        proj.project_dir.mkdir(parents=True, exist_ok=True)
        state.add_project(proj)
        assert proj.project_yaml_path.exists()

    def test_project_retrievable_after_add(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        proj = ProjectConfig(name="Retrieve", created=datetime.now())
        proj.project_dir.mkdir(parents=True, exist_ok=True)
        state.add_project(proj)
        assert state.get_project("Retrieve") is not None


# ──────────────────────────────────────────────────────────────────────────────
# AppState.remove_project
# ──────────────────────────────────────────────────────────────────────────────


class TestRemoveProject:
    def _add(self, state: AppState, name: str) -> ProjectConfig:
        proj = ProjectConfig(name=name, created=datetime.now())
        proj.project_dir.mkdir(parents=True, exist_ok=True)
        state.add_project(proj)
        return proj

    def test_removes_from_list(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        self._add(state, "ToDelete")
        state.remove_project("ToDelete")
        assert state.get_project("ToDelete") is None

    def test_removes_directory(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        proj = self._add(state, "DirGone")
        proj_dir = proj.project_dir
        state.remove_project("DirGone")
        assert not proj_dir.exists()

    def test_clears_active_project(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        self._add(state, "Active")
        state.active_project = "Active"
        state.remove_project("Active")
        assert state.active_project is None

    def test_active_project_not_cleared_for_other_removal(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        self._add(state, "KeepActive")
        self._add(state, "RemoveThis")
        state.active_project = "KeepActive"
        state.remove_project("RemoveThis")
        assert state.active_project == "KeepActive"

    def test_remove_nonexistent_does_nothing(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        self._add(state, "Existing")
        state.remove_project("Ghost")  # should not raise
        assert len(state.projects) == 1

    def test_other_projects_unaffected(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        self._add(state, "A")
        self._add(state, "B")
        self._add(state, "C")
        state.remove_project("B")
        assert state.get_project("A") is not None
        assert state.get_project("C") is not None
        assert len(state.projects) == 2


# ──────────────────────────────────────────────────────────────────────────────
# AppState.reload_projects
# ──────────────────────────────────────────────────────────────────────────────


class TestReloadProjects:
    def test_reload_empty(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        state.reload_projects()
        assert state.projects == []

    def test_reload_picks_up_new_projects(self, tmp_path):
        state = AppState(asset_root=tmp_path)
        proj = ProjectConfig(name="Dynamic", created=datetime.now())
        proj.project_dir.mkdir(parents=True, exist_ok=True)
        from unityaml.persistence import save_project
        save_project(proj)
        state.reload_projects()
        assert state.get_project("Dynamic") is not None


# ──────────────────────────────────────────────────────────────────────────────
# create_app_state
# ──────────────────────────────────────────────────────────────────────────────


class TestCreateAppState:
    def test_uses_provided_root(self, tmp_path):
        state = create_app_state(tmp_path)
        assert state.asset_root == tmp_path

    def test_defaults_to_cwd_when_none(self, tmp_path, monkeypatch):
        monkeypatch.chdir(tmp_path)
        state = create_app_state(None)
        assert state.asset_root == Path.cwd()

    def test_loads_projects_on_creation(self, tmp_path):
        proj = ProjectConfig(name="Preloaded", created=datetime.now())
        proj.project_dir.mkdir(parents=True, exist_ok=True)
        from unityaml.persistence import save_project
        save_project(proj)
        state = create_app_state(tmp_path)
        assert state.get_project("Preloaded") is not None

    def test_has_default_filter(self, tmp_path):
        state = create_app_state(tmp_path)
        assert ".blend" in state.file_filter
