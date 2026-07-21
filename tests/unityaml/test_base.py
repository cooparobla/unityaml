"""Tests for unityaml.base — FileVersion, BaseProperties, BaseFileHandler."""

from __future__ import annotations

from pathlib import Path

import pytest

from unityaml.base import AssetType, BaseFileHandler, BaseProperties, FileVersion


# ──────────────────────────────────────────────────────────────────────────────
# FileVersion
# ──────────────────────────────────────────────────────────────────────────────


class TestFileVersion:
    def test_label_with_version(self, tmp_path):
        v = FileVersion(path=tmp_path / "a.v2.3.blend", major=2, minor=3)
        assert v.label == "v2.3"

    def test_label_v0_0_is_empty(self, tmp_path):
        v = FileVersion(path=tmp_path / "a.blend", major=0, minor=0)
        assert v.label == ""

    def test_label_major_zero_minor_nonzero(self, tmp_path):
        v = FileVersion(path=tmp_path / "a.v0.5.blend", major=0, minor=5)
        assert v.label == "v0.5"

    # --- Ordering ---

    def test_lt_by_major(self, tmp_path):
        v1 = FileVersion(path=tmp_path / "a.v1.0.blend", major=1, minor=0)
        v2 = FileVersion(path=tmp_path / "a.v2.0.blend", major=2, minor=0)
        assert v1 < v2
        assert not v2 < v1

    def test_lt_by_minor_when_major_equal(self, tmp_path):
        v1 = FileVersion(path=tmp_path / "a.v2.1.blend", major=2, minor=1)
        v2 = FileVersion(path=tmp_path / "a.v2.9.blend", major=2, minor=9)
        assert v1 < v2

    def test_le_equal(self, tmp_path):
        v1 = FileVersion(path=tmp_path / "a.v2.3.blend", major=2, minor=3)
        v2 = FileVersion(path=tmp_path / "a.v2.3.blend", major=2, minor=3)
        assert v1 <= v2

    def test_eq_same_version(self, tmp_path):
        v1 = FileVersion(path=tmp_path / "a.v2.3.blend", major=2, minor=3)
        v2 = FileVersion(path=tmp_path / "b.v2.3.blend", major=2, minor=3)
        assert v1 == v2  # equality is on (major, minor) only

    def test_eq_different_version(self, tmp_path):
        v1 = FileVersion(path=tmp_path / "a.v1.0.blend", major=1, minor=0)
        v2 = FileVersion(path=tmp_path / "a.v2.0.blend", major=2, minor=0)
        assert v1 != v2

    def test_sortable(self, tmp_path):
        versions = [
            FileVersion(path=tmp_path / "a.v3.0.blend", major=3, minor=0),
            FileVersion(path=tmp_path / "a.v1.0.blend", major=1, minor=0),
            FileVersion(path=tmp_path / "a.v2.0.blend", major=2, minor=0),
        ]
        sorted_versions = sorted(versions)
        assert [v.major for v in sorted_versions] == [1, 2, 3]

    def test_hashable(self, tmp_path):
        v = FileVersion(path=tmp_path / "a.v1.0.blend", major=1, minor=0)
        s = {v}
        assert v in s

    def test_eq_non_fileversion_returns_notimplemented(self, tmp_path):
        v = FileVersion(path=tmp_path / "a.v1.0.blend", major=1, minor=0)
        assert v.__eq__("not a version") is NotImplemented


# ──────────────────────────────────────────────────────────────────────────────
# BaseProperties
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseProperties:
    def _make_props(self, tmp_path, versions=None, active=None):
        p = tmp_path / "file.blend"
        p.touch()
        return BaseProperties(
            path=p,
            asset_type=AssetType.BLEND,
            versions=versions or [],
            active_version=active,
        )

    # --- is_versioned ---

    def test_is_versioned_true(self, tmp_path):
        v1 = FileVersion(path=tmp_path / "a.v1.0.blend", major=1, minor=0)
        v2 = FileVersion(path=tmp_path / "a.v2.0.blend", major=2, minor=0)
        props = self._make_props(tmp_path, versions=[v1, v2])
        assert props.is_versioned is True

    def test_is_versioned_false_single(self, tmp_path):
        v = FileVersion(path=tmp_path / "a.blend", major=0, minor=0)
        props = self._make_props(tmp_path, versions=[v])
        assert props.is_versioned is False

    def test_is_versioned_false_empty(self, tmp_path):
        props = self._make_props(tmp_path, versions=[])
        assert props.is_versioned is False

    # --- active_version auto-selection ---

    def test_active_version_defaults_to_highest(self, tmp_path):
        v1 = FileVersion(path=tmp_path / "a.v1.0.blend", major=1, minor=0)
        v2 = FileVersion(path=tmp_path / "a.v2.3.blend", major=2, minor=3)
        props = self._make_props(tmp_path, versions=[v1, v2])
        assert props.active_version == v2

    def test_active_version_none_when_no_versions(self, tmp_path):
        props = self._make_props(tmp_path, versions=[])
        assert props.active_version is None

    def test_active_version_explicit_override(self, tmp_path):
        v1 = FileVersion(path=tmp_path / "a.v1.0.blend", major=1, minor=0)
        v2 = FileVersion(path=tmp_path / "a.v2.0.blend", major=2, minor=0)
        props = self._make_props(tmp_path, versions=[v1, v2], active=v1)
        # explicit value passed in init, post_init should not override it
        # (actually post_init only sets if None, so explicit v1 stays)
        assert props.active_version == v1

    # --- display_name ---

    def test_display_name_versioned(self, tmp_path):
        p = tmp_path / "char.v2.3.blend"
        p.touch()
        v = FileVersion(path=p, major=2, minor=3)
        props = BaseProperties(
            path=p,
            asset_type=AssetType.BLEND,
            versions=[v],
            active_version=v,
        )
        assert props.display_name == "char.blend (v2.3)"

    def test_display_name_unversioned(self, tmp_path):
        p = tmp_path / "scene.yaml"
        p.touch()
        v = FileVersion(path=p, major=0, minor=0)
        props = BaseProperties(
            path=p,
            asset_type=AssetType.YAML,
            versions=[v],
            active_version=v,
        )
        assert props.display_name == "scene.yaml"

    def test_display_name_no_active_version(self, tmp_path):
        p = tmp_path / "data.json"
        p.touch()
        props = BaseProperties(
            path=p,
            asset_type=AssetType.JSON,
            versions=[],
        )
        assert props.display_name == "data.json"

    # --- projects default ---

    def test_projects_default_empty(self, tmp_path):
        props = self._make_props(tmp_path)
        assert props.projects == []

    # --- last_modified default ---

    def test_last_modified_has_default(self, tmp_path):
        from datetime import datetime

        props = self._make_props(tmp_path)
        assert isinstance(props.last_modified, datetime)


# ──────────────────────────────────────────────────────────────────────────────
# AssetType
# ──────────────────────────────────────────────────────────────────────────────


class TestAssetType:
    def test_values(self):
        assert AssetType.BLEND.value == "blend"
        assert AssetType.IMAGE.value == "image"
        assert AssetType.YAML.value == "yaml"
        assert AssetType.JSON.value == "json"
        assert AssetType.UNKNOWN.value == "unknown"

    def test_from_string(self):
        assert AssetType("blend") == AssetType.BLEND
        assert AssetType("image") == AssetType.IMAGE

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            AssetType("not_a_type")


# ──────────────────────────────────────────────────────────────────────────────
# BaseFileHandler.get_projects
# ──────────────────────────────────────────────────────────────────────────────


class TestBaseFileHandlerGetProjects:
    """get_projects is a concrete method on the ABC — test it directly via a stub."""

    class _StubHandler(BaseFileHandler):
        def load(self, path: Path) -> BaseProperties:
            raise NotImplementedError

    def test_no_projects_returns_empty(self, tmp_path):
        handler = self._StubHandler()
        p = tmp_path / "file.blend"
        p.touch()
        assert handler.get_projects(p, []) == []

    def test_matching_asset_ref_included(self, tmp_path):
        from datetime import datetime

        from unityaml.base import AssetType
        from unityaml.project import AssetRef, ProjectConfig

        handler = self._StubHandler()
        asset_path = tmp_path / "char.blend"
        asset_path.touch()

        proj = ProjectConfig(
            name="MyGame",
            created=datetime.now(),
            asset_refs=[AssetRef(path=asset_path, asset_type=AssetType.BLEND)],
        )
        result = handler.get_projects(asset_path, [proj])
        assert "MyGame" in result

    def test_non_matching_ref_excluded(self, tmp_path):
        from datetime import datetime

        from unityaml.base import AssetType
        from unityaml.project import AssetRef, ProjectConfig

        handler = self._StubHandler()
        asset_path = tmp_path / "char.blend"
        other_path = tmp_path / "other.blend"
        asset_path.touch()
        other_path.touch()

        proj = ProjectConfig(
            name="MyGame",
            created=datetime.now(),
            asset_refs=[AssetRef(path=other_path, asset_type=AssetType.BLEND)],
        )
        result = handler.get_projects(asset_path, [proj])
        assert result == []

    def test_config_file_match_included(self, tmp_path):
        from datetime import datetime

        from unityaml.project import ProjectConfig

        handler = self._StubHandler()
        cfg_path = tmp_path / "scene.yaml"
        cfg_path.touch()

        proj = ProjectConfig(
            name="Demo",
            created=datetime.now(),
            config_files=[cfg_path],
        )
        result = handler.get_projects(cfg_path, [proj])
        assert "Demo" in result

    def test_no_duplicates_when_matched_twice(self, tmp_path):
        """A file that matches both asset_refs and config_files should appear once."""
        from datetime import datetime

        from unityaml.base import AssetType
        from unityaml.project import AssetRef, ProjectConfig

        handler = self._StubHandler()
        p = tmp_path / "scene.yaml"
        p.touch()

        proj = ProjectConfig(
            name="Multi",
            created=datetime.now(),
            config_files=[p],
            asset_refs=[AssetRef(path=p, asset_type=AssetType.YAML)],
        )
        result = handler.get_projects(p, [proj])
        assert result.count("Multi") == 1
