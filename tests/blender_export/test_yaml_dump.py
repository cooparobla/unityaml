"""Tests for blender_export.yaml_dump — the pure-Python YAML serialiser.

No Qt or Blender needed; tests run in plain Python.
"""

from __future__ import annotations

import pytest

from blender_export.yaml_dump import (
    dump_simple_dict,
    dump_simple_list,
    is_simple_dict,
    is_simple_list,
    manual_yaml_dump,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helper predicates
# ──────────────────────────────────────────────────────────────────────────────


class TestIsSimpleDict:
    def test_empty_dict_is_simple(self):
        assert is_simple_dict({}) is True

    def test_scalar_values_are_simple(self):
        assert is_simple_dict({"a": 1, "b": "x"}) is True

    def test_nested_dict_is_not_simple(self):
        assert is_simple_dict({"a": {"b": 1}}) is False

    def test_nested_list_is_not_simple(self):
        assert is_simple_dict({"a": [1, 2]}) is False

    def test_too_many_keys_is_not_simple(self):
        assert is_simple_dict({str(i): i for i in range(5)}) is False

    def test_tag_key_is_not_simple(self):
        assert is_simple_dict({"_tag": "Vector3", "x": 0}) is False

    def test_non_dict_is_not_simple(self):
        assert is_simple_dict([1, 2]) is False
        assert is_simple_dict("hello") is False
        assert is_simple_dict(42) is False


class TestIsSimpleList:
    def test_empty_list_is_simple(self):
        assert is_simple_list([]) is True

    def test_scalar_items_are_simple(self):
        assert is_simple_list([1, 2, "a"]) is True

    def test_nested_list_is_not_simple(self):
        assert is_simple_list([[1, 2]]) is False

    def test_nested_dict_is_not_simple(self):
        assert is_simple_list([{"a": 1}]) is False

    def test_too_many_items_is_not_simple(self):
        assert is_simple_list(list(range(11))) is False

    def test_exactly_ten_items_is_simple(self):
        assert is_simple_list(list(range(10))) is True

    def test_non_list_is_not_simple(self):
        assert is_simple_list({"a": 1}) is False


# ──────────────────────────────────────────────────────────────────────────────
# Formatters
# ──────────────────────────────────────────────────────────────────────────────


class TestDumpSimpleDict:
    def test_string_values(self):
        result = dump_simple_dict({"key": "value"})
        assert result == "{ key: value }"

    def test_int_values(self):
        result = dump_simple_dict({"x": 1, "y": 2})
        assert "x: 1" in result
        assert "y: 2" in result

    def test_bool_values_lowercased(self):
        result = dump_simple_dict({"flag": True, "off": False})
        assert "flag: true" in result
        assert "off: false" in result

    def test_empty_dict(self):
        result = dump_simple_dict({})
        assert result == "{  }"


class TestDumpSimpleList:
    def test_int_list(self):
        result = dump_simple_list([1, 2, 3])
        assert result == "[1, 2, 3]"

    def test_bool_list_lowercased(self):
        result = dump_simple_list([True, False])
        assert result == "[true, false]"

    def test_empty_list(self):
        result = dump_simple_list([])
        assert result == "[]"

    def test_string_list(self):
        result = dump_simple_list(["a", "b"])
        assert result == "[a, b]"


# ──────────────────────────────────────────────────────────────────────────────
# manual_yaml_dump — scalar output
# ──────────────────────────────────────────────────────────────────────────────


class TestManualYamlDumpScalars:
    def test_string(self):
        lines = manual_yaml_dump("hello")
        assert lines == ["hello"]

    def test_int(self):
        lines = manual_yaml_dump(42)
        assert lines == ["42"]

    def test_float(self):
        lines = manual_yaml_dump(3.14)
        assert lines == ["3.14"]

    def test_bool_true(self):
        lines = manual_yaml_dump(True)
        assert lines == ["true"]

    def test_bool_false(self):
        lines = manual_yaml_dump(False)
        assert lines == ["false"]

    def test_none(self):
        lines = manual_yaml_dump(None)
        assert lines == ["None"]


# ──────────────────────────────────────────────────────────────────────────────
# manual_yaml_dump — flat dicts
# ──────────────────────────────────────────────────────────────────────────────


class TestManualYamlDumpFlatDict:
    def test_flat_simple_values(self):
        lines = manual_yaml_dump({"name": "Alice", "age": 30})
        text = "\n".join(lines)
        assert "name: Alice" in text
        assert "age: 30" in text

    def test_simple_dict_inlined(self):
        """A nested simple dict should be dumped inline."""
        lines = manual_yaml_dump({"pos": {"x": 0, "y": 1}})
        assert any("pos:" in l and "{" in l for l in lines)

    def test_nested_dict_block(self):
        """A nested complex dict should be dumped as a block."""
        lines = manual_yaml_dump({"outer": {"a": {"b": "c"}}})
        text = "\n".join(lines)
        assert "outer:" in text
        assert "a:" in text

    def test_bool_values_lowercased(self):
        lines = manual_yaml_dump({"active": True, "hidden": False})
        text = "\n".join(lines)
        assert "active: true" in text
        assert "hidden: false" in text

    def test_mesh_sorts_before_scene(self):
        """The dumper guarantees 'mesh' appears before 'scene'."""
        lines = manual_yaml_dump({"scene": {"objects": {}}, "mesh": {"cube": {}}})
        mesh_idx = next(i for i, l in enumerate(lines) if l.startswith("mesh"))
        scene_idx = next(i for i, l in enumerate(lines) if l.startswith("scene"))
        assert mesh_idx < scene_idx


# ──────────────────────────────────────────────────────────────────────────────
# manual_yaml_dump — lists
# ──────────────────────────────────────────────────────────────────────────────


class TestManualYamlDumpLists:
    def test_simple_list_inlined(self):
        lines = manual_yaml_dump({"tags": [1, 2, 3]})
        assert any("tags:" in l and "[" in l for l in lines)

    def test_complex_list_block(self):
        """List items that are complex dicts should expand to blocks."""
        lines = manual_yaml_dump([{"a": {"b": "c"}}, {"d": "e"}])
        assert any("- " in l for l in lines)

    def test_list_of_simple_dicts_inlined(self):
        lines = manual_yaml_dump([{"x": 1, "y": 2}])
        # simple dicts in a list use '- {x: 1, y: 2}' form
        assert any(l.strip().startswith("- {") for l in lines)

    def test_list_of_scalars(self):
        lines = manual_yaml_dump([10, 20, 30])
        assert "- 10" in lines
        assert "- 20" in lines
        assert "- 30" in lines

    def test_empty_list(self):
        lines = manual_yaml_dump({"items": []})
        assert any("items:" in l and "[]" in l for l in lines)


# ──────────────────────────────────────────────────────────────────────────────
# manual_yaml_dump — tagged dicts
# ──────────────────────────────────────────────────────────────────────────────


class TestManualYamlDumpTagged:
    def test_tag_emitted(self):
        lines = manual_yaml_dump({"_tag": "Vector3", "x": 0, "y": 1, "z": 2})
        assert any(l.strip().startswith("!Vector3") for l in lines)

    def test_tag_keys_rendered(self):
        lines = manual_yaml_dump({"_tag": "Quaternion", "x": 0.0, "y": 0.0, "z": 0.0, "w": 1.0})
        text = "\n".join(lines)
        assert "x: 0.0" in text
        assert "w: 1.0" in text

    def test_tag_key_excluded_from_output(self):
        lines = manual_yaml_dump({"_tag": "Color", "r": 1, "g": 0, "b": 0})
        assert not any("_tag" in l for l in lines)


# ──────────────────────────────────────────────────────────────────────────────
# manual_yaml_dump — indentation
# ──────────────────────────────────────────────────────────────────────────────


class TestManualYamlDumpIndent:
    def test_indent_applied(self):
        lines = manual_yaml_dump({"key": "val"}, indent=2)
        assert all(l.startswith("    ") for l in lines if l)  # 4 spaces for indent=2

    def test_nested_indent_increases(self):
        lines = manual_yaml_dump({"a": {"b": {"c": 1}}})
        c_line = next((l for l in lines if "c:" in l), None)
        assert c_line is not None
        assert c_line.startswith("  ")  # at least 2 levels deep


# ──────────────────────────────────────────────────────────────────────────────
# Round-trip: dump → parse with PyYAML
# ──────────────────────────────────────────────────────────────────────────────


class TestRoundTrip:
    def _roundtrip(self, data: dict) -> dict:
        import yaml

        lines = manual_yaml_dump(data)
        return yaml.safe_load("\n".join(lines)) or {}

    def test_flat_dict_roundtrip(self):
        data = {"name": "test", "value": 42, "active": True}
        result = self._roundtrip(data)
        assert result["name"] == "test"
        assert result["value"] == 42
        assert result["active"] is True

    def test_nested_dict_roundtrip(self):
        data = {"outer": {"inner": "value"}}
        result = self._roundtrip(data)
        assert result["outer"]["inner"] == "value"

    def test_list_roundtrip(self):
        data = {"items": [1, 2, 3]}
        result = self._roundtrip(data)
        assert result["items"] == [1, 2, 3]
