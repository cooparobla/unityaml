"""Tests for unityaml.yaml_file — YamlProperties and YamlFileHandler."""

from __future__ import annotations

from pathlib import Path

import pytest

from unityaml.base import AssetType
from unityaml.yaml_file import YamlFileHandler, YamlProperties


# ──────────────────────────────────────────────────────────────────────────────
# YamlFileHandler.load
# ──────────────────────────────────────────────────────────────────────────────


class TestYamlFileHandlerLoad:
    def test_simple_config(self, tmp_path):
        p = tmp_path / "config.yaml"
        p.write_text("name: test\nvalue: 42\n")
        props = YamlFileHandler().load(p)
        assert "name" in props.top_level_keys
        assert "value" in props.top_level_keys

    def test_yml_extension(self, tmp_path):
        """Files with .yml extension should load normally."""
        p = tmp_path / "config.yml"
        p.write_text("key: hello\n")
        props = YamlFileHandler().load(p)
        assert "key" in props.top_level_keys

    def test_is_config_true_for_arbitrary_yaml(self, tmp_path):
        p = tmp_path / "settings.yaml"
        p.write_text("debug: true\nport: 8080\n")
        props = YamlFileHandler().load(p)
        assert props.is_config is True
        assert props.is_scene_export is False

    def test_scene_export_detection_full_set(self, tmp_path):
        """format + mesh + scene keys → scene export."""
        p = tmp_path / "export.yaml"
        p.write_text("format: v1\nmesh:\n  cube: {}\nscene:\n  objects: {}\n")
        props = YamlFileHandler().load(p)
        assert props.is_scene_export is True
        assert props.is_config is False

    def test_scene_export_any_magic_key_triggers_detection(self, tmp_path):
        """Any single key from {format, mesh, scene, animations} triggers scene-export detection.

        This documents the current behaviour of the detection heuristic.
        'format' alone is sufficient to mark the file as a scene export.
        """
        for key in ("format", "mesh", "scene", "animations"):
            p = tmp_path / f"partial_{key}.yaml"
            p.write_text(f"{key}: value\n")
            props = YamlFileHandler().load(p)
            assert props.is_scene_export is True, (
                f"Expected '{key}' alone to trigger is_scene_export"
            )

    def test_unrelated_keys_not_detected_as_scene_export(self, tmp_path):
        """Keys that share no members with the magic set → not a scene export."""
        p = tmp_path / "settings.yaml"
        p.write_text("debug: true\nport: 8080\nlog_level: INFO\n")
        props = YamlFileHandler().load(p)
        assert props.is_scene_export is False

    def test_line_count(self, tmp_path):
        content = "a: 1\nb: 2\nc: 3\n"
        p = tmp_path / "data.yaml"
        p.write_text(content)
        props = YamlFileHandler().load(p)
        assert props.line_count == content.count("\n")

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.yaml"
        p.write_text("")
        props = YamlFileHandler().load(p)
        assert props.top_level_keys == []
        assert props.line_count == 0
        assert props.is_config is False
        assert props.is_scene_export is False

    def test_invalid_yaml_gracefully_handled(self, tmp_path):
        p = tmp_path / "bad.yaml"
        p.write_text(":::: not valid yaml ::::\n")
        props = YamlFileHandler().load(p)
        # Should not raise; keys will be empty
        assert props.top_level_keys == []

    def test_yaml_list_at_root_not_crashing(self, tmp_path):
        """A YAML root that is a list (not a dict) should produce empty keys."""
        p = tmp_path / "list.yaml"
        p.write_text("- item1\n- item2\n")
        props = YamlFileHandler().load(p)
        assert props.top_level_keys == []

    def test_asset_type_is_yaml(self, tmp_path):
        p = tmp_path / "cfg.yaml"
        p.write_text("x: 1\n")
        props = YamlFileHandler().load(p)
        assert props.asset_type == AssetType.YAML

    def test_path_resolved(self, tmp_path):
        p = tmp_path / "cfg.yaml"
        p.write_text("x: 1\n")
        props = YamlFileHandler().load(p)
        assert props.path == p.resolve()

    def test_versioned_file(self, tmp_path):
        (tmp_path / "config.v1.0.yaml").write_text("a: 1\n")
        (tmp_path / "config.v2.0.yaml").write_text("a: 2\n")
        props = YamlFileHandler().load(tmp_path / "config.v2.0.yaml")
        assert len(props.versions) == 2

    def test_projects_default_empty(self, tmp_path):
        p = tmp_path / "cfg.yaml"
        p.write_text("x: 1\n")
        props = YamlFileHandler().load(p)
        assert props.projects == []

    def test_many_top_level_keys(self, tmp_path):
        keys = {f"key{i}": i for i in range(20)}
        import yaml as _yaml
        p = tmp_path / "big.yaml"
        p.write_text(_yaml.dump(keys))
        props = YamlFileHandler().load(p)
        assert len(props.top_level_keys) == 20

    def test_nested_yaml_only_top_level_keys_returned(self, tmp_path):
        p = tmp_path / "nested.yaml"
        p.write_text("outer:\n  inner: value\n")
        props = YamlFileHandler().load(p)
        assert props.top_level_keys == ["outer"]
        assert "inner" not in props.top_level_keys


# ──────────────────────────────────────────────────────────────────────────────
# YamlFileHandler.read_content
# ──────────────────────────────────────────────────────────────────────────────


class TestYamlFileHandlerReadContent:
    def test_returns_file_contents(self, tmp_path):
        p = tmp_path / "cfg.yaml"
        p.write_text("key: value\n")
        handler = YamlFileHandler()
        props = handler.load(p)
        assert handler.read_content(props) == "key: value\n"

    def test_non_utf8_bytes_handled(self, tmp_path):
        p = tmp_path / "latin.yaml"
        p.write_bytes(b"key: caf\xe9\n")  # latin-1 byte in UTF-8 stream
        handler = YamlFileHandler()
        props = handler.load(p)
        content = handler.read_content(props)
        assert "key:" in content  # at minimum the key is there

    def test_missing_file_returns_empty(self, tmp_path):
        p = tmp_path / "ghost.yaml"
        p.write_text("x: 1\n")
        props = YamlFileHandler().load(p)
        p.unlink()  # delete after loading props
        content = YamlFileHandler().read_content(props)
        assert content == ""
