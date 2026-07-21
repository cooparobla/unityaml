"""Tests for unityaml.json_file — JsonProperties and JsonFileHandler."""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from unityaml.base import AssetType
from unityaml.json_file import JsonFileHandler, JsonProperties


# ──────────────────────────────────────────────────────────────────────────────
# JsonFileHandler.load
# ──────────────────────────────────────────────────────────────────────────────


class TestJsonFileHandlerLoad:
    def test_simple_flat_object(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text(json.dumps({"key": "value", "count": 5}))
        props = JsonFileHandler().load(p)
        assert "key" in props.top_level_keys
        assert "count" in props.top_level_keys

    def test_nested_only_top_level_keys(self, tmp_path):
        p = tmp_path / "nested.json"
        p.write_text(json.dumps({"outer": {"inner": 42}, "other": 1}))
        props = JsonFileHandler().load(p)
        assert props.top_level_keys == ["outer", "other"]
        assert "inner" not in props.top_level_keys

    def test_asset_type_is_json(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text("{}")
        props = JsonFileHandler().load(p)
        assert props.asset_type == AssetType.JSON

    def test_file_size_bytes(self, tmp_path):
        p = tmp_path / "data.json"
        content = json.dumps({"a": 1, "b": 2})
        p.write_text(content)
        props = JsonFileHandler().load(p)
        assert props.file_size_bytes == p.stat().st_size

    def test_path_resolved(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text("{}")
        props = JsonFileHandler().load(p)
        assert props.path == p.resolve()

    def test_invalid_json_gracefully_handled(self, tmp_path):
        p = tmp_path / "bad.json"
        p.write_text("{ not valid json ]")
        props = JsonFileHandler().load(p)
        assert props.top_level_keys == []

    def test_json_array_at_root(self, tmp_path):
        """A JSON root that is an array (not an object) → empty top_level_keys."""
        p = tmp_path / "list.json"
        p.write_text(json.dumps([1, 2, 3]))
        props = JsonFileHandler().load(p)
        assert props.top_level_keys == []

    def test_empty_object(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("{}")
        props = JsonFileHandler().load(p)
        assert props.top_level_keys == []

    def test_empty_file(self, tmp_path):
        p = tmp_path / "empty.json"
        p.write_text("")
        props = JsonFileHandler().load(p)
        assert props.top_level_keys == []

    def test_versions_populated(self, tmp_path):
        (tmp_path / "schema.v1.0.json").write_text('{"a":1}')
        (tmp_path / "schema.v2.0.json").write_text('{"a":2}')
        props = JsonFileHandler().load(tmp_path / "schema.v2.0.json")
        assert len(props.versions) == 2

    def test_projects_default_empty(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"x": 1}')
        props = JsonFileHandler().load(p)
        assert props.projects == []

    def test_many_keys(self, tmp_path):
        data = {f"key_{i}": i for i in range(50)}
        p = tmp_path / "big.json"
        p.write_text(json.dumps(data))
        props = JsonFileHandler().load(p)
        assert len(props.top_level_keys) == 50

    def test_unicode_keys(self, tmp_path):
        p = tmp_path / "unicode.json"
        p.write_text(json.dumps({"名前": "Alice", "年齢": 30}), encoding="utf-8")
        props = JsonFileHandler().load(p)
        assert "名前" in props.top_level_keys


# ──────────────────────────────────────────────────────────────────────────────
# JsonFileHandler.read_content
# ──────────────────────────────────────────────────────────────────────────────


class TestJsonFileHandlerReadContent:
    def test_returns_pretty_printed_json(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"a":1,"b":2}')
        handler = JsonFileHandler()
        props = handler.load(p)
        content = handler.read_content(props)
        assert '"a"' in content
        assert "\n" in content  # pretty-printed with newlines

    def test_indentation_is_two_spaces(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"nested":{"x":1}}')
        handler = JsonFileHandler()
        props = handler.load(p)
        content = handler.read_content(props)
        # json.dumps with indent=2 uses 2-space indent
        assert "  " in content

    def test_invalid_json_returns_raw_text(self, tmp_path):
        p = tmp_path / "bad.json"
        raw = "{ broken json"
        p.write_text(raw)
        handler = JsonFileHandler()
        props = handler.load(p)
        content = handler.read_content(props)
        assert content == raw

    def test_missing_file_returns_empty(self, tmp_path):
        p = tmp_path / "data.json"
        p.write_text('{"x":1}')
        props = JsonFileHandler().load(p)
        p.unlink()
        content = JsonFileHandler().read_content(props)
        assert content == ""

    def test_large_object_preserves_all_keys(self, tmp_path):
        data = {f"k{i}": i for i in range(100)}
        p = tmp_path / "large.json"
        p.write_text(json.dumps(data))
        props = JsonFileHandler().load(p)
        content = JsonFileHandler().read_content(props)
        parsed = json.loads(content)
        assert len(parsed) == 100

    def test_unicode_preserved_in_content(self, tmp_path):
        data = {"greeting": "こんにちは"}
        p = tmp_path / "unicode.json"
        p.write_text(json.dumps(data, ensure_ascii=False), encoding="utf-8")
        props = JsonFileHandler().load(p)
        content = JsonFileHandler().read_content(props)
        assert "こんにちは" in content
