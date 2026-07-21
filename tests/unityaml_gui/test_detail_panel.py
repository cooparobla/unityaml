"""Tests for DetailPanel dispatcher and detail sub-panels."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from unityaml_gui.views.detail_panel import DetailPanel


class TestDetailPanel:
    def test_init(self, qtbot):
        panel = DetailPanel()
        qtbot.addWidget(panel)
        assert panel._stack.currentIndex() == 0

    def test_show_file_blend(self, qtbot, tmp_path):
        panel = DetailPanel()
        qtbot.addWidget(panel)

        blend = tmp_path / "model.blend"
        blend.touch()

        panel.show_file(blend, [blend])
        assert panel._stack.currentIndex() == 1

    def test_show_file_image(self, qtbot, tmp_path):
        panel = DetailPanel()
        qtbot.addWidget(panel)

        img = tmp_path / "texture.png"
        img.touch()

        panel.show_file(img, [img])
        assert panel._stack.currentIndex() == 2

    def test_show_file_yaml(self, qtbot, tmp_path):
        panel = DetailPanel()
        qtbot.addWidget(panel)

        cfg = tmp_path / "config.yaml"
        cfg.write_text("key: value\n")

        panel.show_file(cfg, [cfg])
        assert panel._stack.currentIndex() == 3

    def test_show_file_json(self, qtbot, tmp_path):
        panel = DetailPanel()
        qtbot.addWidget(panel)

        data = tmp_path / "data.json"
        data.write_text(json.dumps({"key": "value"}))

        panel.show_file(data, [data])
        assert panel._stack.currentIndex() == 4

    def test_show_file_unknown_returns_to_empty(self, qtbot, tmp_path):
        panel = DetailPanel()
        qtbot.addWidget(panel)

        unknown = tmp_path / "data.unknown"
        unknown.touch()

        panel.show_file(unknown, [unknown])
        assert panel._stack.currentIndex() == 0

    def test_clear(self, qtbot, tmp_path):
        panel = DetailPanel()
        qtbot.addWidget(panel)

        cfg = tmp_path / "config.yaml"
        cfg.write_text("key: value\n")
        panel.show_file(cfg, [cfg])
        assert panel._stack.currentIndex() == 3

        panel.clear()
        assert panel._stack.currentIndex() == 0
