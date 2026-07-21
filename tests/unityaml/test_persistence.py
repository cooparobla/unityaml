"""Tests for unityaml.persistence — YAML I/O, project serialization round-trips."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from unityaml.base import AssetType, FileVersion
from unityaml.project import AssetRef, ProjectConfig


# ──────────────────────────────────────────────────────────────────────────────
# Fixture — redirect all persistence paths to tmp_path
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture(autouse=True)
def _redirect_persistence(tmp_path, monkeypatch):
    from unityaml import persistence

    monkeypatch.setattr(persistence, "unityaml_root", lambda: tmp_path / "unityaml")
    monkeypatch.setattr(
        persistence, "projects_root", lambda: tmp_path / "unityaml" / "projects"
    )
    # Also redirect ProjectConfig.project_dir / project_yaml_path
    def patched_project_dir(self):
        return tmp_path / "unityaml" / "projects" / self.name.lower().replace(" ", "_")

    monkeypatch.setattr(ProjectConfig, "project_dir", property(patched_project_dir))
    monkeypatch.setattr(
        ProjectConfig,
        "project_yaml_path",
        property(lambda self: patched_project_dir(self) / "project.yaml"),
    )


# ──────────────────────────────────────────────────────────────────────────────
# load_yaml / dump_yaml
# ──────────────────────────────────────────────────────────────────────────────


class TestLoadDumpYaml:
    def test_load_missing_file_returns_empty(self, tmp_path):
        from unityaml.persistence import load_yaml

        result = load_yaml(tmp_path / "nonexistent.yaml")
        assert result == {}

    def test_load_invalid_yaml_returns_empty(self, tmp_path):
        from unityaml.persistence import load_yaml

        p = tmp_path / "bad.yaml"
        p.write_text(":::: garbage ::::")
        assert load_yaml(p) == {}

    def test_load_yaml_list_returns_empty(self, tmp_path):
        """A YAML document that is a list (not a dict) should return {}."""
        from unityaml.persistence import load_yaml

        p = tmp_path / "list.yaml"
        p.write_text("- item1\n- item2\n")
        assert load_yaml(p) == {}

    def test_dump_and_load_roundtrip(self, tmp_path):
        from unityaml.persistence import dump_yaml, load_yaml

        data = {"name": "Alice", "value": 42, "active": True}
        p = tmp_path / "out.yaml"
        dump_yaml(data, p)
        assert p.exists()
        loaded = load_yaml(p)
        assert loaded["name"] == "Alice"
        assert loaded["value"] == 42

    def test_dump_creates_parent_dirs(self, tmp_path):
        from unityaml.persistence import dump_yaml

        p = tmp_path / "a" / "b" / "c" / "out.yaml"
        dump_yaml({"x": 1}, p)
        assert p.exists()

    def test_load_empty_file_returns_empty(self, tmp_path):
        from unityaml.persistence import load_yaml

        p = tmp_path / "empty.yaml"
        p.write_text("")
        assert load_yaml(p) == {}


# ──────────────────────────────────────────────────────────────────────────────
# save_project / load_project
# ──────────────────────────────────────────────────────────────────────────────


class TestSaveLoadProject:
    def _make_project(self, tmp_path, name="Alpha") -> ProjectConfig:
        proj = ProjectConfig(name=name, created=datetime(2026, 6, 1, 12, 0))
        proj.project_dir.mkdir(parents=True, exist_ok=True)
        return proj

    def test_save_creates_yaml(self, tmp_path):
        from unityaml.persistence import save_project

        proj = self._make_project(tmp_path)
        save_project(proj)
        assert proj.project_yaml_path.exists()

    def test_roundtrip_name_and_created(self, tmp_path):
        from unityaml.persistence import load_project, save_project

        proj = self._make_project(tmp_path)
        save_project(proj)
        loaded = load_project(proj.project_yaml_path)
        assert loaded.name == "Alpha"
        assert loaded.created.year == 2026

    def test_roundtrip_config_files(self, tmp_path):
        from unityaml.persistence import load_project, save_project

        proj = self._make_project(tmp_path)
        cfg = tmp_path / "scene.yaml"
        cfg.touch()
        proj.config_files = [cfg]
        save_project(proj)
        loaded = load_project(proj.project_yaml_path)
        assert len(loaded.config_files) == 1
        assert Path(loaded.config_files[0]).name == "scene.yaml"

    def test_roundtrip_asset_ref_no_pinned_version(self, tmp_path):
        from unityaml.persistence import load_project, save_project

        proj = self._make_project(tmp_path)
        proj.asset_refs = [AssetRef(path=tmp_path / "char.blend", asset_type=AssetType.BLEND)]
        save_project(proj)
        loaded = load_project(proj.project_yaml_path)
        assert len(loaded.asset_refs) == 1
        assert loaded.asset_refs[0].asset_type == AssetType.BLEND
        assert loaded.asset_refs[0].pinned_version is None

    def test_roundtrip_asset_ref_with_pinned_version(self, tmp_path):
        from unityaml.persistence import load_project, save_project

        proj = self._make_project(tmp_path)
        p = tmp_path / "char.v2.3.blend"
        v = FileVersion(path=p, major=2, minor=3)
        proj.asset_refs = [AssetRef(path=p, asset_type=AssetType.BLEND, pinned_version=v)]
        save_project(proj)
        loaded = load_project(proj.project_yaml_path)
        pv = loaded.asset_refs[0].pinned_version
        assert pv is not None
        assert pv.major == 2
        assert pv.minor == 3

    def test_roundtrip_export_dir(self, tmp_path):
        from unityaml.persistence import load_project, save_project

        proj = self._make_project(tmp_path)
        proj.export_dir = tmp_path / "output"
        save_project(proj)
        loaded = load_project(proj.project_yaml_path)
        assert loaded.export_dir == tmp_path / "output"

    def test_roundtrip_no_export_dir(self, tmp_path):
        from unityaml.persistence import load_project, save_project

        proj = self._make_project(tmp_path)
        proj.export_dir = None
        save_project(proj)
        loaded = load_project(proj.project_yaml_path)
        # None export_dir is serialised as empty string and reads back as None
        assert loaded.export_dir is None

    def test_load_project_bad_created_falls_back(self, tmp_path):
        """A missing/malformed 'created' field should not crash."""
        from unityaml.persistence import dump_yaml, load_project

        p = tmp_path / "proj.yaml"
        dump_yaml({"name": "Broken", "created": "not-a-date"}, p)
        proj = load_project(p)
        assert proj.name == "Broken"
        assert isinstance(proj.created, datetime)

    def test_load_project_unknown_asset_type(self, tmp_path):
        """Unknown asset_type values should deserialize to AssetType.UNKNOWN."""
        from unityaml.persistence import dump_yaml, load_project

        p = tmp_path / "proj.yaml"
        dump_yaml(
            {
                "name": "Edge",
                "created": datetime.now().isoformat(),
                "asset_refs": [{"path": str(tmp_path / "x.blend"), "asset_type": "NOTREAL"}],
            },
            p,
        )
        proj = load_project(p)
        assert proj.asset_refs[0].asset_type == AssetType.UNKNOWN


# ──────────────────────────────────────────────────────────────────────────────
# load_all_projects
# ──────────────────────────────────────────────────────────────────────────────


class TestLoadAllProjects:
    def _make_and_save(self, name: str) -> ProjectConfig:
        proj = ProjectConfig(name=name, created=datetime.now())
        proj.project_dir.mkdir(parents=True, exist_ok=True)
        from unityaml.persistence import save_project
        save_project(proj)
        return proj

    def test_empty_projects_dir_returns_empty(self, tmp_path):
        from unityaml.persistence import load_all_projects

        result = load_all_projects()
        assert result == []

    def test_nonexistent_projects_dir_returns_empty(self, tmp_path, monkeypatch):
        from unityaml import persistence

        monkeypatch.setattr(persistence, "projects_root", lambda: tmp_path / "nowhere")
        result = persistence.load_all_projects()
        assert result == []

    def test_loads_single_project(self, tmp_path):
        from unityaml.persistence import load_all_projects

        self._make_and_save("Gamma")
        projects = load_all_projects()
        assert len(projects) == 1
        assert projects[0].name == "Gamma"

    def test_loads_multiple_projects_sorted(self, tmp_path):
        from unityaml.persistence import load_all_projects

        self._make_and_save("Zeta")
        self._make_and_save("Alpha")
        self._make_and_save("Beta")
        projects = load_all_projects()
        assert len(projects) == 3
        # They should be sorted by directory name (alphabetically)
        names = [p.name for p in projects]
        assert names == sorted(names)

    def test_ignores_dirs_without_project_yaml(self, tmp_path):
        from unityaml import persistence as _p
        from unityaml.persistence import load_all_projects

        # Create a subdir without a project.yaml
        empty_dir = _p.projects_root() / "orphan"
        empty_dir.mkdir(parents=True, exist_ok=True)
        projects = load_all_projects()
        assert len(projects) == 0

    def test_ignores_corrupt_project_yaml(self, tmp_path):
        from unityaml import persistence as _p
        from unityaml.persistence import load_all_projects

        corrupt_dir = _p.projects_root() / "corrupt"
        corrupt_dir.mkdir(parents=True, exist_ok=True)
        # load_yaml returns {} on invalid YAML, and load_project is tolerant of
        # a {} dict (uses parent dir name as fallback). It does NOT raise.
        # So invalid YAML produces a minimal project, not zero projects.
        (corrupt_dir / "project.yaml").write_text(":::: not yaml ::::")
        projects = load_all_projects()
        # Expect exactly 1 fallback project (name = dir name)
        assert len(projects) == 1
        assert projects[0].name == "corrupt"


# ──────────────────────────────────────────────────────────────────────────────
# delete_project
# ──────────────────────────────────────────────────────────────────────────────


class TestDeleteProject:
    def test_deletes_project_dir(self, tmp_path):
        from unityaml.persistence import delete_project, save_project

        proj = ProjectConfig(name="Delete_Me", created=datetime.now())
        proj.project_dir.mkdir(parents=True, exist_ok=True)
        save_project(proj)
        assert proj.project_dir.exists()
        delete_project(proj)
        assert not proj.project_dir.exists()

    def test_delete_nonexistent_dir_does_not_crash(self, tmp_path):
        from unityaml.persistence import delete_project

        proj = ProjectConfig(name="Ghost", created=datetime.now())
        # Don't create the dir; delete should be a no-op
        delete_project(proj)  # should not raise
