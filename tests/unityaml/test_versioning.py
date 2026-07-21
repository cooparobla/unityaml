"""Tests for unityaml.versioning — version parsing, grouping, and resolution."""

from __future__ import annotations

from pathlib import Path

import pytest

from unityaml.versioning import (
    canonical_stem,
    group_versioned_files,
    highest_version,
    parse_version,
    resolve_versions,
)


# ──────────────────────────────────────────────────────────────────────────────
# parse_version
# ──────────────────────────────────────────────────────────────────────────────


class TestParseVersion:
    # --- Versioned files ---

    def test_blend_versioned(self, tmp_path):
        p = tmp_path / "character.v2.3.blend"
        p.touch()
        name, ver = parse_version(p)
        assert name == "character"
        assert ver is not None
        assert ver.major == 2
        assert ver.minor == 3
        assert ver.path == p

    def test_png_versioned(self, tmp_path):
        p = tmp_path / "skin.v1.0.png"
        p.touch()
        name, ver = parse_version(p)
        assert name == "skin"
        assert ver.major == 1
        assert ver.minor == 0

    def test_large_version_numbers(self, tmp_path):
        p = tmp_path / "scene.v10.20.yaml"
        p.touch()
        name, ver = parse_version(p)
        assert ver.major == 10
        assert ver.minor == 20

    def test_version_zero_zero(self, tmp_path):
        p = tmp_path / "data.v0.0.json"
        p.touch()
        name, ver = parse_version(p)
        assert ver.major == 0
        assert ver.minor == 0
        assert ver.label == ""  # v0.0 has no label

    def test_multipart_name_preserved(self, tmp_path):
        p = tmp_path / "my_cool_asset.v3.1.blend"
        p.touch()
        name, ver = parse_version(p)
        assert name == "my_cool_asset"

    def test_name_with_dots_preserved(self, tmp_path):
        # Only the .v<N>.<M> suffix should be stripped
        p = tmp_path / "asset.extra.v1.2.blend"
        p.touch()
        name, ver = parse_version(p)
        assert name == "asset.extra"
        assert ver.major == 1
        assert ver.minor == 2

    # --- Unversioned files ---

    def test_yaml_unversioned(self, tmp_path):
        p = tmp_path / "scene.yaml"
        p.touch()
        name, ver = parse_version(p)
        assert name == "scene"
        assert ver is None

    def test_json_unversioned(self, tmp_path):
        p = tmp_path / "config.json"
        p.touch()
        name, ver = parse_version(p)
        assert name == "config"
        assert ver is None

    def test_no_extension(self, tmp_path):
        p = tmp_path / "README"
        p.touch()
        name, ver = parse_version(p)
        assert name == "README"
        assert ver is None

    def test_version_suffix_must_have_both_parts(self, tmp_path):
        # ".v3" without minor part is NOT a version suffix
        p = tmp_path / "file.v3.blend"
        p.touch()
        name, ver = parse_version(p)
        # stem = "file.v3", no match → unversioned
        assert ver is None


# ──────────────────────────────────────────────────────────────────────────────
# canonical_stem
# ──────────────────────────────────────────────────────────────────────────────


class TestCanonicalStem:
    def test_strips_version(self):
        assert canonical_stem(Path("char.v2.3.blend")) == "char"

    def test_leaves_unversioned(self):
        assert canonical_stem(Path("scene.yaml")) == "scene"

    def test_multipart(self):
        assert canonical_stem(Path("my_mesh.v1.0.blend")) == "my_mesh"


# ──────────────────────────────────────────────────────────────────────────────
# resolve_versions
# ──────────────────────────────────────────────────────────────────────────────


class TestResolveVersions:
    def test_two_versioned_siblings(self, tmp_path):
        for name in ["char.v1.0.blend", "char.v2.3.blend"]:
            (tmp_path / name).touch()
        versions = resolve_versions(tmp_path / "char.v2.3.blend")
        assert len(versions) == 2
        assert {v.major for v in versions} == {1, 2}

    def test_three_versioned_siblings(self, tmp_path):
        for name in ["char.v0.9.blend", "char.v1.0.blend", "char.v2.3.blend"]:
            (tmp_path / name).touch()
        versions = resolve_versions(tmp_path / "char.v1.0.blend")
        assert len(versions) == 3

    def test_result_is_sorted(self, tmp_path):
        for name in ["char.v3.0.blend", "char.v1.0.blend", "char.v2.0.blend"]:
            (tmp_path / name).touch()
        versions = resolve_versions(tmp_path / "char.v3.0.blend")
        majors = [v.major for v in versions]
        assert majors == sorted(majors)

    def test_unversioned_file_returns_single_entry(self, tmp_path):
        p = tmp_path / "scene.yaml"
        p.touch()
        versions = resolve_versions(p)
        assert len(versions) == 1
        assert versions[0].major == 0
        assert versions[0].minor == 0
        assert versions[0].path == p

    def test_mixed_extensions_not_grouped(self, tmp_path):
        """char.v1.0.blend and char.v1.0.yaml should NOT be grouped together."""
        (tmp_path / "char.v1.0.blend").touch()
        (tmp_path / "char.v1.0.yaml").touch()
        versions = resolve_versions(tmp_path / "char.v1.0.blend")
        # Only .blend files grouped
        exts = {v.path.suffix for v in versions}
        assert exts == {".blend"}

    def test_different_canonical_names_not_grouped(self, tmp_path):
        """weapon.v1.0.blend should not appear when resolving char.v1.0.blend."""
        (tmp_path / "char.v1.0.blend").touch()
        (tmp_path / "weapon.v1.0.blend").touch()
        versions = resolve_versions(tmp_path / "char.v1.0.blend")
        names = {canonical_stem(v.path) for v in versions}
        assert names == {"char"}

    def test_unversioned_sibling_included(self, tmp_path):
        """A bare 'char.blend' alongside 'char.v1.0.blend' should appear in both."""
        (tmp_path / "char.blend").touch()
        (tmp_path / "char.v1.0.blend").touch()
        versions = resolve_versions(tmp_path / "char.v1.0.blend")
        assert len(versions) == 2

    def test_fallback_for_nonexistent_parent_file(self, tmp_path):
        """resolve_versions on an isolated path returns a single v0.0 entry."""
        p = tmp_path / "lonely.blend"
        p.touch()
        versions = resolve_versions(p)
        assert len(versions) == 1
        assert versions[0].path == p


# ──────────────────────────────────────────────────────────────────────────────
# group_versioned_files
# ──────────────────────────────────────────────────────────────────────────────


class TestGroupVersionedFiles:
    def test_basic_grouping(self, tmp_path):
        paths = []
        for name in ["char.v1.0.blend", "char.v2.3.blend", "scene.yaml"]:
            p = tmp_path / name
            p.touch()
            paths.append(p)
        groups = group_versioned_files(paths)
        assert "char.blend" in groups
        assert "scene.yaml" in groups
        assert len(groups["char.blend"]) == 2

    def test_each_group_sorted(self, tmp_path):
        paths = []
        for name in ["a.v3.0.blend", "a.v1.0.blend", "a.v2.0.blend"]:
            p = tmp_path / name
            p.touch()
            paths.append(p)
        groups = group_versioned_files(paths)
        majors = [v.major for v in groups["a.blend"]]
        assert majors == sorted(majors)

    def test_same_name_different_extension_separate_groups(self, tmp_path):
        paths = []
        for name in ["asset.v1.0.blend", "asset.v1.0.yaml"]:
            p = tmp_path / name
            p.touch()
            paths.append(p)
        groups = group_versioned_files(paths)
        assert "asset.blend" in groups
        assert "asset.yaml" in groups

    def test_unversioned_gets_v0_0(self, tmp_path):
        p = tmp_path / "config.json"
        p.touch()
        groups = group_versioned_files([p])
        assert "config.json" in groups
        assert groups["config.json"][0].major == 0
        assert groups["config.json"][0].minor == 0

    def test_empty_input(self):
        groups = group_versioned_files([])
        assert groups == {}

    def test_multiple_canonical_names(self, tmp_path):
        paths = []
        for name in ["char.v1.0.blend", "weapon.v2.0.blend", "scene.yaml"]:
            p = tmp_path / name
            p.touch()
            paths.append(p)
        groups = group_versioned_files(paths)
        assert len(groups) == 3


# ──────────────────────────────────────────────────────────────────────────────
# highest_version
# ──────────────────────────────────────────────────────────────────────────────


class TestHighestVersion:
    def test_picks_highest_major(self, tmp_path):
        from unityaml.base import FileVersion

        versions = [
            FileVersion(path=tmp_path / "a.v1.0.blend", major=1, minor=0),
            FileVersion(path=tmp_path / "a.v3.0.blend", major=3, minor=0),
            FileVersion(path=tmp_path / "a.v2.0.blend", major=2, minor=0),
        ]
        assert highest_version(versions).major == 3

    def test_minor_breaks_tie(self, tmp_path):
        from unityaml.base import FileVersion

        versions = [
            FileVersion(path=tmp_path / "a.v2.1.blend", major=2, minor=1),
            FileVersion(path=tmp_path / "a.v2.9.blend", major=2, minor=9),
            FileVersion(path=tmp_path / "a.v2.3.blend", major=2, minor=3),
        ]
        best = highest_version(versions)
        assert best.major == 2
        assert best.minor == 9

    def test_single_version(self, tmp_path):
        from unityaml.base import FileVersion

        v = FileVersion(path=tmp_path / "a.v1.0.blend", major=1, minor=0)
        assert highest_version([v]) == v
