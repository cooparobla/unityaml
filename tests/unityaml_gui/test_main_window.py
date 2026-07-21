"""Tests for AssetsTab and MainWindow / UnityYamlApp."""

from __future__ import annotations

import pytest
from unityaml_gui.app import UnityYamlApp
from unityaml_gui.main_window import MainWindow
from unityaml_gui.views.assets_tab import AssetsTab


class TestAssetsTab:
    def test_init(self, qtbot, app_state):
        tab = AssetsTab(app_state)
        qtbot.addWidget(tab)
        assert tab._filter_edit.text() == " ".join(app_state.file_filter)

    def test_apply_filter(self, qtbot, app_state):
        tab = AssetsTab(app_state)
        qtbot.addWidget(tab)

        tab._filter_edit.setText(".blend .png")
        tab._apply_filter()

        assert app_state.file_filter == [".blend", ".png"]


class TestMainWindow:
    def test_init(self, qtbot, app_state):
        window = MainWindow(app_state)
        qtbot.addWidget(window)

        assert window.tabs.count() == 2
        assert window.windowTitle() == "UnityYAML — Asset Manager"

    def test_unityaml_app_stylesheet(self, qtbot, app_state):
        app_win = UnityYamlApp(app_state)
        qtbot.addWidget(app_win)

        assert app_win.tabs.count() == 2
