"""Tests for unityaml.blend — BlenderProperties, BlenderFileHandler, and sidecar I/O."""

from __future__ import annotations

from datetime import datetime, timedelta
from pathlib import Path

import pytest

from unityaml.blend import (
    BlenderFileHandler,
    BlenderProperties,
    _load_sidecar,
    _sidecar_path,
    _write_sidecar,
)
from unityaml.base import AssetType, FileVersion


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _make_blend_props(tmp_path: Path, **kwargs) -> BlenderProperties:
    """Return a minimal BlenderProperties for testing."""
    p = tmp_path / "scene.blend"
    p.touch()
    v = FileVersion(path=p, major=0, minor=0)
    defaults = dict(
        path=p,
        versions=[v],
        projects=[],
        last_modified=datetime.now(),
    )
    defaults.update(kwargs)
    return BlenderProperties(**defaults)


# ──────────────────────────────────────────────────────────────────────────────
# BlenderProperties
# ──────────────────────────────────────────────────────────────────────────────


class TestBlenderProperties:
    def test_asset_type_is_blend(self, tmp_path):
        props = _make_blend_props(tmp_path)
        assert props.asset_type == AssetType.BLEND

    def test_not_stale_without_export(self, tmp_path):
        props = _make_blend_props(tmp_path, last_exported=None, export_path=None)
        assert props.stale is False

    def test_stale_when_blend_newer_than_export(self, tmp_path):
        export_file = tmp_path / "scene.yaml"
        export_file.touch()
        old = datetime(2020, 1, 1)
        now = datetime.now()
        # Simulate: blend modified after export
        props = _make_blend_props(
            tmp_path,
            last_modified=now,
            last_exported=old,
            export_path=export_file,
        )
        # __post_init__ uses last_modified > last_exported
        assert props.stale is True

    def test_not_stale_when_export_newer(self, tmp_path):
        export_file = tmp_path / "scene.yaml"
        export_file.touch()
        old = datetime(2020, 1, 1)
        recent = datetime(2025, 1, 1)
        props = _make_blend_props(
            tmp_path,
            last_modified=old,
            last_exported=recent,
            export_path=export_file,
        )
        assert props.stale is False

    def test_defaults(self, tmp_path):
        props = _make_blend_props(tmp_path)
        assert props.object_names == []
        assert props.mesh_count == 0
        assert props.has_armature is False
        assert props.has_animations is False
        assert props.last_exported is None
        assert props.export_path is None


# ──────────────────────────────────────────────────────────────────────────────
# Sidecar helpers
# ──────────────────────────────────────────────────────────────────────────────


class TestSidecarHelpers:
    def test_sidecar_path(self, tmp_path):
        blend = tmp_path / "char.blend"
        expected = tmp_path / "char.blend.meta.yaml"
        assert _sidecar_path(blend) == expected

    def test_load_sidecar_missing_returns_empty(self, tmp_path):
        blend = tmp_path / "scene.blend"
        blend.touch()
        result = _load_sidecar(blend)
        assert result == {}

    def test_load_sidecar_reads_valid_yaml(self, tmp_path):
        blend = tmp_path / "scene.blend"
        blend.touch()
        sidecar = _sidecar_path(blend)
        sidecar.write_text("objects:\n- Body\nmesh_count: 3\n")
        result = _load_sidecar(blend)
        assert result["objects"] == ["Body"]
        assert result["mesh_count"] == 3

    def test_load_sidecar_returns_empty_on_invalid_yaml(self, tmp_path):
        blend = tmp_path / "scene.blend"
        blend.touch()
        _sidecar_path(blend).write_text(":: invalid :: yaml ::")
        result = _load_sidecar(blend)
        assert result == {}

    def test_write_sidecar_creates_file(self, tmp_path):
        props = _make_blend_props(
            tmp_path,
            object_names=["Body", "Armature"],
            mesh_count=2,
            has_armature=True,
            has_animations=False,
            last_exported=datetime(2026, 1, 15, 12, 0),
            export_path=tmp_path / "scene.yaml",
        )
        _write_sidecar(props)
        sidecar = _sidecar_path(props.path)
        assert sidecar.exists()

    def test_write_then_load_round_trip(self, tmp_path):
        props = _make_blend_props(
            tmp_path,
            object_names=["Hero", "Shield"],
            mesh_count=5,
            has_armature=True,
            has_animations=True,
            last_exported=datetime(2026, 3, 10, 9, 30),
            export_path=tmp_path / "hero.yaml",
        )
        _write_sidecar(props)
        loaded = _load_sidecar(props.path)
        assert loaded["objects"] == ["Hero", "Shield"]
        assert loaded["mesh_count"] == 5
        assert loaded["has_armature"] is True
        assert loaded["has_animations"] is True
        # PyYAML parses ISO datetime strings into datetime objects automatically
        assert isinstance(loaded["last_exported"], datetime)
        assert loaded["last_exported"].year == 2026
        assert loaded["last_exported"].month == 3
        assert loaded["export_path"] is not None

    def test_write_sidecar_null_export_path(self, tmp_path):
        props = _make_blend_props(tmp_path, last_exported=None, export_path=None)
        _write_sidecar(props)
        loaded = _load_sidecar(props.path)
        # export_path is serialised as empty string → falsy but present
        assert not loaded.get("export_path")


# ──────────────────────────────────────────────────────────────────────────────
# BlenderFileHandler.load
# ──────────────────────────────────────────────────────────────────────────────


class TestBlenderFileHandlerLoad:
    def test_load_without_sidecar(self, tmp_path):
        blend = tmp_path / "model.blend"
        blend.touch()
        handler = BlenderFileHandler()
        props = handler.load(blend)
        assert props.path == blend.resolve()
        assert props.object_names == []
        assert props.mesh_count == 0
        assert props.has_armature is False
        assert props.stale is False

    def test_load_with_sidecar(self, tmp_path):
        blend = tmp_path / "model.blend"
        blend.touch()
        sidecar = _sidecar_path(blend.resolve())
        sidecar.write_text(
            "objects:\n- Cube\nmesh_count: 1\nhas_armature: false\nhas_animations: false\n"
            "last_exported: '2026-01-01T00:00:00'\nexport_path: null\n"
        )
        handler = BlenderFileHandler()
        props = handler.load(blend)
        assert props.object_names == ["Cube"]
        assert props.mesh_count == 1

    def test_load_resolves_path(self, tmp_path):
        blend = tmp_path / "model.blend"
        blend.touch()
        handler = BlenderFileHandler()
        props = handler.load(blend)
        assert props.path == blend.resolve()

    def test_load_populates_versions(self, tmp_path):
        (tmp_path / "model.v1.0.blend").touch()
        (tmp_path / "model.v2.0.blend").touch()
        handler = BlenderFileHandler()
        props = handler.load(tmp_path / "model.v2.0.blend")
        assert len(props.versions) == 2

    def test_load_invalid_sidecar_datetime(self, tmp_path):
        """A malformed last_exported in the sidecar should not crash."""
        blend = tmp_path / "model.blend"
        blend.touch()
        _sidecar_path(blend.resolve()).write_text(
            "last_exported: 'not-a-date'\nexport_path: null\n"
        )
        handler = BlenderFileHandler()
        props = handler.load(blend)
        assert props.last_exported is None


# ──────────────────────────────────────────────────────────────────────────────
# BlenderFileHandler.check_stale
# ──────────────────────────────────────────────────────────────────────────────


class TestCheckStale:
    def test_no_export_path_not_stale(self, tmp_path):
        handler = BlenderFileHandler()
        props = _make_blend_props(tmp_path, last_exported=datetime.now(), export_path=None)
        assert handler.check_stale(props) is False

    def test_no_last_exported_not_stale(self, tmp_path):
        handler = BlenderFileHandler()
        export = tmp_path / "out.yaml"
        export.touch()
        props = _make_blend_props(tmp_path, last_exported=None, export_path=export)
        assert handler.check_stale(props) is False

    def test_missing_export_file_is_stale(self, tmp_path):
        handler = BlenderFileHandler()
        export = tmp_path / "nonexistent.yaml"
        # does NOT touch it
        props = _make_blend_props(
            tmp_path,
            last_exported=datetime.now(),
            export_path=export,
        )
        assert handler.check_stale(props) is True

    def test_blend_newer_than_export_is_stale(self, tmp_path):
        import os
        import time

        export = tmp_path / "out.yaml"
        export.touch()
        # Set export mtime to the past
        past = time.time() - 3600
        os.utime(export, (past, past))

        blend = tmp_path / "model.blend"
        blend.touch()
        # blend's mtime is now (after export's mtime)
        handler = BlenderFileHandler()
        props = BlenderFileHandler().load(blend)
        props.export_path = export
        props.last_exported = datetime.fromtimestamp(past)
        assert handler.check_stale(props) is True

    def test_export_newer_than_blend_not_stale(self, tmp_path):
        import os
        import time

        blend = tmp_path / "model.blend"
        blend.touch()
        # Set blend mtime to past
        past = time.time() - 3600
        os.utime(blend, (past, past))

        export = tmp_path / "out.yaml"
        export.touch()
        # export mtime is now (after blend)

        handler = BlenderFileHandler()
        props = BlenderFileHandler().load(blend)
        props.export_path = export
        props.last_exported = datetime.fromtimestamp(export.stat().st_mtime)
        assert handler.check_stale(props) is False
