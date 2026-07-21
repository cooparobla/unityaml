"""Projects tab — project list (left) + project detail panel (right)."""

from __future__ import annotations

from datetime import datetime

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QHBoxLayout,
    QInputDialog,
    QListWidget,
    QListWidgetItem,
    QMessageBox,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from unityaml.app_state import AppState
from unityaml.project import ProjectConfig
from unityaml_gui.settings import AppSettings
from unityaml_gui.views.project_detail import ProjectDetailPanel


class ProjectsTab(QWidget):
    """Projects tab widget."""

    projects_changed = Signal()
    status_message = Signal(str)

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self._settings = AppSettings()
        self._build_ui()
        self._populate_list()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Toolbar ───────────────────────────────────────────────────
        toolbar = self._build_toolbar()
        root.addWidget(toolbar)

        # ── Splitter ──────────────────────────────────────────────────
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: project list
        self._list = QListWidget()
        self._list.setMinimumWidth(180)
        self._list.setMaximumWidth(280)
        self._list.currentItemChanged.connect(self._on_project_selected)
        self._splitter.addWidget(self._list)

        # Right: detail
        self._detail = ProjectDetailPanel()
        self._detail.status_message.connect(self.status_message)
        self._detail.project_changed.connect(self._on_project_changed)
        self._splitter.addWidget(self._detail)

        saved = self._settings.get("projects_splitter", None)
        if saved and isinstance(saved, list):
            self._splitter.setSizes([int(s) for s in saved])
        else:
            self._splitter.setSizes([220, 580])

        self._splitter.splitterMoved.connect(self._on_splitter_moved)
        root.addWidget(self._splitter)

    def _build_toolbar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet("background: #1C1D26; border-bottom: 1px solid #2A2B38;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        new_btn = QPushButton("+ New Project")
        new_btn.setProperty("accent", True)
        new_btn.clicked.connect(self._on_new_project)
        layout.addWidget(new_btn)

        del_btn = QPushButton("Delete")
        del_btn.setProperty("danger", True)
        del_btn.clicked.connect(self._on_delete_project)
        layout.addWidget(del_btn)

        layout.addStretch()
        return bar

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def _populate_list(self) -> None:
        self._list.clear()
        for proj in self.state.projects:
            item = QListWidgetItem(f"▸  {proj.name}")
            item.setData(Qt.ItemDataRole.UserRole, proj.name)
            self._list.addItem(item)
        if self._list.count() == 0:
            self._detail.clear()

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_project_selected(self, current: QListWidgetItem | None, _prev) -> None:
        if current is None:
            self._detail.clear()
            self.state.active_project = None
            return
        name: str = current.data(Qt.ItemDataRole.UserRole)
        self.state.active_project = name
        project = self.state.get_project(name)
        if project:
            self._detail.load(project)
            self.status_message.emit(f"Active project: {name}")

    def _on_new_project(self) -> None:
        name, ok = QInputDialog.getText(
            self, "New Project", "Project name:", text="MyProject"
        )
        if not ok or not name.strip():
            return
        name = name.strip()
        if self.state.get_project(name):
            QMessageBox.warning(self, "Duplicate", f"A project named '{name}' already exists.")
            return
        project = ProjectConfig(name=name, created=datetime.now())
        self.state.add_project(project)
        self._populate_list()
        # Select the new project
        for i in range(self._list.count()):
            if self._list.item(i).data(Qt.ItemDataRole.UserRole) == name:
                self._list.setCurrentRow(i)
                break
        self.projects_changed.emit()
        self.status_message.emit(f"Created project '{name}'")

    def _on_delete_project(self) -> None:
        item = self._list.currentItem()
        if not item:
            return
        name: str = item.data(Qt.ItemDataRole.UserRole)
        reply = QMessageBox.question(
            self,
            "Delete Project",
            f"Delete project '{name}'? This cannot be undone.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply != QMessageBox.StandardButton.Yes:
            return
        self.state.remove_project(name)
        self._populate_list()
        self._detail.clear()
        self.projects_changed.emit()
        self.status_message.emit(f"Deleted project '{name}'")

    def _on_project_changed(self) -> None:
        self.projects_changed.emit()

    def _on_splitter_moved(self, pos: int, _idx: int) -> None:
        self._settings.set("projects_splitter", self._splitter.sizes())
        self._settings.save()
