"""Tests for AppSettings — pure key/value store with YAML persistence.

No QApplication required; AppSettings only touches the filesystem.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from unityaml_gui.settings import AppSettings


class TestAppSettingsGetSet:
    def test_get_missing_key_returns_default(self, tmp_path):
        s = AppSettings()
        assert s.get("nonexistent") is None

    def test_get_missing_key_custom_default(self, tmp_path):
        s = AppSettings()
        assert s.get("nonexistent", 42) == 42

    def test_set_and_get_string(self, tmp_path):
        s = AppSettings()
        s.set("theme", "dark")
        assert s.get("theme") == "dark"

    def test_set_and_get_int(self, tmp_path):
        s = AppSettings()
        s.set("tab", 1)
        assert s.get("tab") == 1

    def test_set_and_get_list(self, tmp_path):
        s = AppSettings()
        s.set("sizes", [200, 600])
        assert s.get("sizes") == [200, 600]

    def test_set_and_get_bool(self, tmp_path):
        s = AppSettings()
        s.set("active", True)
        assert s.get("active") is True

    def test_overwrite_existing_key(self, tmp_path):
        s = AppSettings()
        s.set("key", "old")
        s.set("key", "new")
        assert s.get("key") == "new"


class TestAppSettingsPersistence:
    def test_save_and_reload(self, tmp_path):
        s1 = AppSettings()
        s1.set("window_geometry", "ABCDEF")
        s1.save()

        s2 = AppSettings()
        assert s2.get("window_geometry") == "ABCDEF"

    def test_save_multiple_keys(self, tmp_path):
        s1 = AppSettings()
        s1.set("active_tab", 1)
        s1.set("assets_splitter", [300, 500])
        s1.save()

        s2 = AppSettings()
        assert s2.get("active_tab") == 1
        assert s2.get("assets_splitter") == [300, 500]

    def test_save_creates_file(self, tmp_path):
        s = AppSettings()
        s.set("x", 1)
        s.save()
        from unityaml_gui.settings import _settings_path
        assert _settings_path().exists()

    def test_fresh_settings_empty(self, tmp_path):
        s = AppSettings()
        assert s.get("anything") is None

    def test_settings_file_is_yaml(self, tmp_path):
        """The saved file should be readable as YAML."""
        import yaml
        s = AppSettings()
        s.set("hello", "world")
        s.save()
        from unityaml_gui.settings import _settings_path
        data = yaml.safe_load(_settings_path().read_text())
        assert data["hello"] == "world"
