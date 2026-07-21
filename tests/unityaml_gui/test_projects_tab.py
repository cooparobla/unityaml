"""Tests for ProjectsTab and ProjectDetailPanel."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

import pytest
from unityaml.project import ProjectConfig
from unityaml_gui.views.project_detail import ProjectDetailPanel
from unityaml_gui.views.projects_tab import ProjectsTab


class TestProjectDetailPanel:
    def test_init(self, qtbot):
        panel = ProjectDetailPanel()
        qtbot.addWidget(panel)
        assert panel._project is None

    def test_load_and_clear(self, qtbot, tmp_path):
        panel = ProjectDetailPanel()
        qtbot.addWidget(panel)

        proj = ProjectConfig(name="DemoProject", created=datetime.now())
        panel.load(proj)
        assert panel._project == proj
        assert panel._name_label.text() == "DemoProject"

        panel.clear()
        assert panel._project is None
        assert panel._name_label.text() == ""


class TestProjectsTab:
    def test_init_and_populate(self, qtbot, app_state, project_factory):
        proj1 = project_factory("ProjectOne")
        proj2 = project_factory("ProjectTwo")

        tab = ProjectsTab(app_state)
        qtbot.addWidget(tab)

        assert tab._list.count() == 2

    def test_select_project(self, qtbot, app_state, project_factory):
        proj1 = project_factory("ProjectOne")

        tab = ProjectsTab(app_state)
        qtbot.addWidget(tab)

        tab._list.setCurrentRow(0)
        assert app_state.active_project == "ProjectOne"
        assert tab._detail._name_label.text() == "ProjectOne"
