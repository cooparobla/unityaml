"""Tests for the unityaml data layer."""

from __future__ import annotations

import json
from datetime import datetime
from pathlib import Path

import pytest

# ──────────────────────────────────────────────────────────────────────────────
# versioning
# ──────────────────────────────────────────────────────────────────────────────

class TestVersioning:
    def test_parse_versioned(self, tmp_path):
        from unityaml.versioning import parse_version

        p = tmp_path / "character.v2.3.blend"
        p.touch()
        name, ver = parse_version(p)
        assert name == "character"
        assert ver is not None
        assert ver.major == 2
        assert ver.minor == 3
        assert ver.label == "v2.3"

    def test_parse_unversioned(self, tmp_path):
        from unityaml.versioning import parse_version

        p = tmp_path / "scene.yaml"
        p.touch()
        name, ver = parse_version(p)
        assert name == "scene"
        assert ver is None

    def test_group_versioned_files(self, tmp_path):
        from unityaml.versioning import group_versioned_files

        paths = []
        for name in ["char.v1.0.blend", "char.v2.3.blend", "scene.yaml"]:
            p = tmp_path / name
            p.touch()
            paths.append(p)

        groups = group_versioned_files(paths)
        assert "char.blend" in groups
        assert "scene.yaml" in groups
        assert len(groups["char.blend"]) == 2
        assert groups["char.blend"][0].major == 1
        assert groups["char.blend"][1].major == 2

    def test_resolve_versions(self, tmp_path):
        from unityaml.versioning import resolve_versions

        for name in ["char.v1.0.blend", "char.v2.3.blend"]:
            (tmp_path / name).touch()

        versions = resolve_versions(tmp_path / "char.v2.3.blend")
        assert len(versions) == 2
        majors = {v.major for v in versions}
        assert majors == {1, 2}

    def test_highest_version(self, tmp_path):
        from unityaml.versioning import highest_version, resolve_versions

        for name in ["char.v1.0.blend", "char.v2.3.blend", "char.v0.9.blend"]:
            (tmp_path / name).touch()

        versions = resolve_versions(tmp_path / "char.v2.3.blend")
        best = highest_version(versions)
        assert best.major == 2
        assert best.minor == 3

    def test_canonical_stem(self):
        from unityaml.versioning import canonical_stem
        from pathlib import Path

        assert canonical_stem(Path("char.v2.3.blend")) == "char"
        assert canonical_stem(Path("scene.yaml")) == "scene"
        assert canonical_stem(Path("skin.v1.0.png")) == "skin"


# ──────────────────────────────────────────────────────────────────────────────
# base
# ──────────────────────────────────────────────────────────────────────────────

class TestBaseProperties:
    def test_is_versioned(self, tmp_path):
        from unityaml.base import AssetType, BaseProperties, FileVersion

        p = tmp_path / "char.v2.3.blend"
        p.touch()
        v1 = FileVersion(path=tmp_path / "char.v1.0.blend", major=1, minor=0)
        v2 = FileVersion(path=p, major=2, minor=3)
        props = BaseProperties(
            path=p,
            asset_type=AssetType.BLEND,
            versions=[v1, v2],
        )
        assert props.is_versioned is True

    def test_not_versioned(self, tmp_path):
        from unityaml.base import AssetType, BaseProperties, FileVersion

        p = tmp_path / "scene.yaml"
        p.touch()
        v = FileVersion(path=p, major=0, minor=0)
        props = BaseProperties(
            path=p,
            asset_type=AssetType.YAML,
            versions=[v],
        )
        assert props.is_versioned is False

    def test_active_version_defaults_to_highest(self, tmp_path):
        from unityaml.base import AssetType, BaseProperties, FileVersion

        p1 = tmp_path / "char.v1.0.blend"
        p2 = tmp_path / "char.v2.3.blend"
        p1.touch(); p2.touch()
        v1 = FileVersion(path=p1, major=1, minor=0)
        v2 = FileVersion(path=p2, major=2, minor=3)
        props = BaseProperties(
            path=p2,
            asset_type=AssetType.BLEND,
            versions=[v1, v2],
        )
        assert props.active_version == v2


# ──────────────────────────────────────────────────────────────────────────────
# handlers — image (pure header parsing)
# ──────────────────────────────────────────────────────────────────────────────

class TestImageHandler:
    def _write_minimal_png(self, path: Path) -> None:
        """Write a valid 1×1 PNG."""
        import zlib
        import struct

        def chunk(name: bytes, data: bytes) -> bytes:
            c = name + data
            return struct.pack(">I", len(data)) + c + struct.pack(">I", zlib.crc32(c) & 0xFFFFFFFF)

        signature = b"\x89PNG\r\n\x1a\n"
        ihdr_data = struct.pack(">IIBBBBB", 1, 1, 8, 2, 0, 0, 0)  # 1x1 RGB
        idat_data = zlib.compress(b"\x00\xff\x00\x00")  # filter + 1 RGB pixel
        iend_data = b""

        path.write_bytes(
            signature
            + chunk(b"IHDR", ihdr_data)
            + chunk(b"IDAT", idat_data)
            + chunk(b"IEND", iend_data)
        )

    def test_load_png(self, tmp_path):
        from unityaml.image import ImageFileHandler

        p = tmp_path / "test.png"
        self._write_minimal_png(p)

        handler = ImageFileHandler()
        props = handler.load(p)
        assert props.format == "PNG"
        assert props.width == 1
        assert props.height == 1
        assert props.file_size_bytes > 0

    def test_load_unknown_image(self, tmp_path):
        from unityaml.image import ImageFileHandler

        p = tmp_path / "test.bmp"
        p.write_bytes(b"\x00" * 64)  # invalid but loadable

        handler = ImageFileHandler()
        props = handler.load(p)
        assert props.path == p


# ──────────────────────────────────────────────────────────────────────────────
# handlers — yaml
# ──────────────────────────────────────────────────────────────────────────────

class TestYamlHandler:
    def test_load_simple_yaml(self, tmp_path):
        from unityaml.yaml_file import YamlFileHandler

        p = tmp_path / "config.yaml"
        p.write_text("name: test\nvalue: 42\n")

        handler = YamlFileHandler()
        props = handler.load(p)
        assert "name" in props.top_level_keys
        assert "value" in props.top_level_keys
        assert props.is_config is True
        assert props.is_scene_export is False
        assert props.line_count >= 2

    def test_scene_export_detection(self, tmp_path):
        from unityaml.yaml_file import YamlFileHandler

        p = tmp_path / "scene_export.yaml"
        p.write_text("format: v1\nmesh:\n  cube: {}\nscene:\n  objects: {}\n")

        handler = YamlFileHandler()
        props = handler.load(p)
        assert props.is_scene_export is True

    def test_read_content(self, tmp_path):
        from unityaml.yaml_file import YamlFileHandler

        p = tmp_path / "cfg.yaml"
        p.write_text("key: value\n")
        handler = YamlFileHandler()
        props = handler.load(p)
        content = handler.read_content(props)
        assert "key: value" in content


# ──────────────────────────────────────────────────────────────────────────────
# handlers — json
# ──────────────────────────────────────────────────────────────────────────────

class TestJsonHandler:
    def test_load_json(self, tmp_path):
        from unityaml.json_file import JsonFileHandler

        p = tmp_path / "data.json"
        p.write_text(json.dumps({"key": "value", "count": 5}))

        handler = JsonFileHandler()
        props = handler.load(p)
        assert "key" in props.top_level_keys
        assert "count" in props.top_level_keys
        assert props.file_size_bytes > 0

    def test_read_content_pretty(self, tmp_path):
        from unityaml.json_file import JsonFileHandler

        p = tmp_path / "data.json"
        p.write_text('{"a":1}')
        handler = JsonFileHandler()
        props = handler.load(p)
        content = handler.read_content(props)
        assert '"a"' in content
        assert "\n" in content  # pretty-printed


# ──────────────────────────────────────────────────────────────────────────────
# project + persistence
# ──────────────────────────────────────────────────────────────────────────────

class TestProjectPersistence:
    def test_save_and_load_project(self, tmp_path, monkeypatch):
        from unityaml import persistence
        from unityaml.base import AssetType
        from unityaml.project import AssetRef, ProjectConfig

        # Redirect ~/.unityaml to tmp_path
        monkeypatch.setattr(persistence, "unityaml_root", lambda: tmp_path)
        monkeypatch.setattr(persistence, "projects_root", lambda: tmp_path / "projects")

        proj = ProjectConfig(
            name="TestProject",
            created=datetime(2026, 1, 15, 10, 30),
            config_files=[tmp_path / "scene.yaml"],
            asset_refs=[
                AssetRef(
                    path=tmp_path / "char.blend",
                    asset_type=AssetType.BLEND,
                )
            ],
        )

        # Patch project_dir so it uses our tmp dir
        proj_dir = tmp_path / "projects" / "testproject"
        proj_dir.mkdir(parents=True)

        import unittest.mock as mock

        with mock.patch.object(type(proj), "project_dir", new_callable=lambda: property(lambda self: proj_dir)):
            with mock.patch.object(type(proj), "project_yaml_path", new_callable=lambda: property(lambda self: proj_dir / "project.yaml")):
                persistence.save_project(proj)
                yaml_path = proj_dir / "project.yaml"
                assert yaml_path.exists()

                loaded = persistence.load_project(yaml_path)
                assert loaded.name == "TestProject"
                assert len(loaded.config_files) == 1
                assert len(loaded.asset_refs) == 1
                assert loaded.asset_refs[0].asset_type == AssetType.BLEND

    def test_app_state_reload(self, tmp_path, monkeypatch):
        from unityaml import persistence
        from unityaml.app_state import create_app_state

        monkeypatch.setattr(persistence, "unityaml_root", lambda: tmp_path)
        monkeypatch.setattr(persistence, "projects_root", lambda: tmp_path / "projects")

        state = create_app_state(tmp_path)
        assert state.asset_root == tmp_path
        assert state.projects == []

    def test_add_remove_project(self, tmp_path, monkeypatch):
        from unityaml import persistence
        from unityaml.app_state import create_app_state
        from unityaml.project import ProjectConfig

        monkeypatch.setattr(persistence, "unityaml_root", lambda: tmp_path)
        monkeypatch.setattr(persistence, "projects_root", lambda: tmp_path / "projects")

        # Also patch ProjectConfig.project_dir so it puts files in tmp
        original_pd = ProjectConfig.project_dir.fget  # type: ignore

        def patched_pd(self):
            return tmp_path / "projects" / self.name.lower()

        with monkeypatch.context() as m:
            m.setattr(ProjectConfig, "project_dir", property(patched_pd))
            m.setattr(ProjectConfig, "project_yaml_path", property(lambda self: patched_pd(self) / "project.yaml"))

            state = create_app_state(tmp_path)
            proj = ProjectConfig(name="Gamma", created=datetime.now())
            state.add_project(proj)
            assert state.get_project("Gamma") is not None
            state.remove_project("Gamma")
            assert state.get_project("Gamma") is None
