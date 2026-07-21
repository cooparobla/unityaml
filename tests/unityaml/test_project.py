"""Tests for unityaml.project — AssetRef and ProjectConfig mutation methods."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest

from unityaml.base import AssetType, FileVersion
from unityaml.project import AssetRef, ProjectConfig


# ──────────────────────────────────────────────────────────────────────────────
# Fixtures
# ──────────────────────────────────────────────────────────────────────────────


@pytest.fixture
def project_in_tmp(tmp_path, monkeypatch):
    """Return a ProjectConfig whose save() writes into tmp_path."""
    from unityaml import persistence

    monkeypatch.setattr(persistence, "unityaml_root", lambda: tmp_path)
    monkeypatch.setattr(persistence, "projects_root", lambda: tmp_path / "projects")

    def patched_project_dir(self):
        return tmp_path / "projects" / self.name.lower().replace(" ", "_")

    monkeypatch.setattr(ProjectConfig, "project_dir", property(patched_project_dir))
    monkeypatch.setattr(
        ProjectConfig,
        "project_yaml_path",
        property(lambda self: patched_project_dir(self) / "project.yaml"),
    )

    proj = ProjectConfig(name="TestProject", created=datetime(2026, 1, 1))
    proj.project_dir.mkdir(parents=True, exist_ok=True)
    return proj


# ──────────────────────────────────────────────────────────────────────────────
# AssetRef
# ──────────────────────────────────────────────────────────────────────────────


class TestAssetRef:
    def test_display_name_unversioned(self, tmp_path):
        p = tmp_path / "char.blend"
        ref = AssetRef(path=p, asset_type=AssetType.BLEND)
        assert ref.display_name == "char.blend"

    def test_display_name_with_pinned_version(self, tmp_path):
        p = tmp_path / "char.v2.3.blend"
        v = FileVersion(path=p, major=2, minor=3)
        ref = AssetRef(path=p, asset_type=AssetType.BLEND, pinned_version=v)
        assert ref.display_name == "char.v2.3.blend (v2.3)"

    def test_display_name_pinned_v0_0_no_label(self, tmp_path):
        """A pinned version with major=minor=0 (unversioned) shows no label."""
        p = tmp_path / "char.blend"
        v = FileVersion(path=p, major=0, minor=0)
        ref = AssetRef(path=p, asset_type=AssetType.BLEND, pinned_version=v)
        # label="" → display_name should just be the filename
        assert ref.display_name == "char.blend"

    def test_pinned_version_default_none(self, tmp_path):
        ref = AssetRef(path=tmp_path / "x.blend", asset_type=AssetType.BLEND)
        assert ref.pinned_version is None

    def test_asset_types(self, tmp_path):
        for atype in [AssetType.BLEND, AssetType.IMAGE, AssetType.YAML, AssetType.JSON]:
            ref = AssetRef(path=tmp_path / "f.blend", asset_type=atype)
            assert ref.asset_type == atype


# ──────────────────────────────────────────────────────────────────────────────
# ProjectConfig.add_asset_ref
# ──────────────────────────────────────────────────────────────────────────────


class TestProjectConfigAddAssetRef:
    def test_adds_new_ref(self, tmp_path, project_in_tmp):
        p = tmp_path / "char.blend"
        p.touch()
        project_in_tmp.add_asset_ref(p, AssetType.BLEND)
        assert len(project_in_tmp.asset_refs) == 1
        assert project_in_tmp.asset_refs[0].path.resolve() == p.resolve()

    def test_no_duplicate_refs(self, tmp_path, project_in_tmp):
        p = tmp_path / "char.blend"
        p.touch()
        project_in_tmp.add_asset_ref(p, AssetType.BLEND)
        project_in_tmp.add_asset_ref(p, AssetType.BLEND)  # second time
        assert len(project_in_tmp.asset_refs) == 1

    def test_different_files_both_added(self, tmp_path, project_in_tmp):
        p1 = tmp_path / "char.blend"
        p2 = tmp_path / "weapon.blend"
        p1.touch()
        p2.touch()
        project_in_tmp.add_asset_ref(p1, AssetType.BLEND)
        project_in_tmp.add_asset_ref(p2, AssetType.BLEND)
        assert len(project_in_tmp.asset_refs) == 2

    def test_saves_after_add(self, tmp_path, project_in_tmp):
        p = tmp_path / "mesh.blend"
        p.touch()
        project_in_tmp.add_asset_ref(p, AssetType.BLEND)
        assert project_in_tmp.project_yaml_path.exists()

    def test_dedup_uses_resolved_path(self, tmp_path, project_in_tmp):
        """Relative and absolute paths to the same file should dedup."""
        p = tmp_path / "asset.blend"
        p.touch()
        project_in_tmp.add_asset_ref(p, AssetType.BLEND)
        project_in_tmp.add_asset_ref(p.resolve(), AssetType.BLEND)
        assert len(project_in_tmp.asset_refs) == 1


# ──────────────────────────────────────────────────────────────────────────────
# ProjectConfig.remove_asset_ref
# ──────────────────────────────────────────────────────────────────────────────


class TestProjectConfigRemoveAssetRef:
    def test_removes_existing_ref(self, tmp_path, project_in_tmp):
        p = tmp_path / "char.blend"
        p.touch()
        project_in_tmp.add_asset_ref(p, AssetType.BLEND)
        project_in_tmp.remove_asset_ref(p)
        assert len(project_in_tmp.asset_refs) == 0

    def test_remove_nonexistent_does_nothing(self, tmp_path, project_in_tmp):
        p = tmp_path / "ghost.blend"
        p.touch()
        project_in_tmp.remove_asset_ref(p)  # should not raise
        assert len(project_in_tmp.asset_refs) == 0

    def test_only_matching_ref_removed(self, tmp_path, project_in_tmp):
        p1 = tmp_path / "a.blend"
        p2 = tmp_path / "b.blend"
        p1.touch()
        p2.touch()
        project_in_tmp.add_asset_ref(p1, AssetType.BLEND)
        project_in_tmp.add_asset_ref(p2, AssetType.BLEND)
        project_in_tmp.remove_asset_ref(p1)
        assert len(project_in_tmp.asset_refs) == 1
        assert project_in_tmp.asset_refs[0].path.resolve() == p2.resolve()

    def test_saves_after_remove(self, tmp_path, project_in_tmp):
        p = tmp_path / "mesh.blend"
        p.touch()
        project_in_tmp.add_asset_ref(p, AssetType.BLEND)
        project_in_tmp.remove_asset_ref(p)
        # YAML should exist and have zero asset_refs
        from unityaml import persistence

        loaded = persistence.load_project(project_in_tmp.project_yaml_path)
        assert len(loaded.asset_refs) == 0


# ──────────────────────────────────────────────────────────────────────────────
# ProjectConfig.add_config_file
# ──────────────────────────────────────────────────────────────────────────────


class TestProjectConfigAddConfigFile:
    def test_adds_new_config(self, tmp_path, project_in_tmp):
        p = tmp_path / "scene.yaml"
        p.touch()
        project_in_tmp.add_config_file(p)
        assert len(project_in_tmp.config_files) == 1

    def test_no_duplicate_config(self, tmp_path, project_in_tmp):
        p = tmp_path / "scene.yaml"
        p.touch()
        project_in_tmp.add_config_file(p)
        project_in_tmp.add_config_file(p)
        assert len(project_in_tmp.config_files) == 1

    def test_saves_after_add_config(self, tmp_path, project_in_tmp):
        p = tmp_path / "cfg.yaml"
        p.touch()
        project_in_tmp.add_config_file(p)
        assert project_in_tmp.project_yaml_path.exists()


# ──────────────────────────────────────────────────────────────────────────────
# ProjectConfig.remove_config_file
# ──────────────────────────────────────────────────────────────────────────────


class TestProjectConfigRemoveConfigFile:
    def test_removes_config(self, tmp_path, project_in_tmp):
        p = tmp_path / "scene.yaml"
        p.touch()
        project_in_tmp.add_config_file(p)
        project_in_tmp.remove_config_file(p)
        assert len(project_in_tmp.config_files) == 0

    def test_remove_nonexistent_config_does_nothing(self, tmp_path, project_in_tmp):
        p = tmp_path / "ghost.yaml"
        p.touch()
        project_in_tmp.remove_config_file(p)
        assert len(project_in_tmp.config_files) == 0

    def test_only_matching_config_removed(self, tmp_path, project_in_tmp):
        p1 = tmp_path / "a.yaml"
        p2 = tmp_path / "b.yaml"
        p1.touch()
        p2.touch()
        project_in_tmp.add_config_file(p1)
        project_in_tmp.add_config_file(p2)
        project_in_tmp.remove_config_file(p1)
        assert len(project_in_tmp.config_files) == 1
        assert project_in_tmp.config_files[0].resolve() == p2.resolve()
