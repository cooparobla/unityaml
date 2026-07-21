"""Tests for VersionSelector widget."""

from __future__ import annotations

from pathlib import Path

import pytest
from unityaml.base import FileVersion
from unityaml_gui.views.detail.version_selector import VersionSelector


class TestVersionSelector:
    def test_init(self, qtbot):
        selector = VersionSelector()
        qtbot.addWidget(selector)
        assert selector.current_version() is None

    def test_set_versions(self, qtbot, tmp_path):
        selector = VersionSelector()
        qtbot.addWidget(selector)

        v1 = FileVersion(path=tmp_path / "char.v1.0.blend", major=1, minor=0)
        v2 = FileVersion(path=tmp_path / "char.v2.0.blend", major=2, minor=0)

        selector.set_versions([v1, v2], active=v2)
        # Should be sorted in reverse order (v2, then v1)
        assert selector.current_version() == v2

    def test_version_changed_signal(self, qtbot, tmp_path):
        selector = VersionSelector()
        qtbot.addWidget(selector)

        v1 = FileVersion(path=tmp_path / "char.v1.0.blend", major=1, minor=0)
        v2 = FileVersion(path=tmp_path / "char.v2.0.blend", major=2, minor=0)

        emitted = []
        selector.version_changed.connect(lambda v: emitted.append(v))

        selector.set_versions([v1, v2], active=v1)
        assert selector.current_version() == v1

        # Change combo index programmatically
        selector._combo.setCurrentIndex(0)  # should select v2 since reverse sorted
        assert len(emitted) > 0
        assert selector.current_version() == v2
