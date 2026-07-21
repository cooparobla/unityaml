"""Main application window — tab bar, status bar, and menu."""

from __future__ import annotations

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QLabel,
    QMainWindow,
    QStatusBar,
    QTabWidget,
    QWidget,
)

from unityaml.app_state import AppState
from unityaml_gui.settings import AppSettings


class MainWindow(QMainWindow):
    """QMainWindow containing the Assets and Projects tabs."""

    def __init__(self, state: AppState) -> None:
        super().__init__()
        self.state = state
        self.settings = AppSettings()

        self.setWindowTitle("UnityYAML — Asset Manager")
        self.setMinimumSize(1024, 650)

        self._build_ui()
        self._restore_geometry()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        from unityaml_gui.views.assets_tab import AssetsTab
        from unityaml_gui.views.projects_tab import ProjectsTab

        self.tabs = QTabWidget()
        self.tabs.setDocumentMode(True)

        self.assets_tab = AssetsTab(self.state)
        self.projects_tab = ProjectsTab(self.state)

        self.tabs.addTab(self.assets_tab, "  Assets  ")
        self.tabs.addTab(self.projects_tab, "  Projects  ")

        # Forward project-changed signals so the assets tab can refresh
        self.projects_tab.projects_changed.connect(self._on_projects_changed)
        self.assets_tab.status_message.connect(self._show_status)
        self.projects_tab.status_message.connect(self._show_status)

        self.setCentralWidget(self.tabs)

        # Status bar
        self._status_label = QLabel()
        self._status_label.setObjectName("statusLabel")
        status_bar = QStatusBar()
        status_bar.addWidget(self._status_label, 1)
        self.setStatusBar(status_bar)

        # Restore last active tab
        last_tab = self.settings.get("active_tab", 0)
        self.tabs.setCurrentIndex(int(last_tab))
        self.tabs.currentChanged.connect(self._on_tab_changed)

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_tab_changed(self, index: int) -> None:
        self.settings.set("active_tab", index)

    def _on_projects_changed(self) -> None:
        """Propagate project changes to the assets tab detail panel."""
        self.assets_tab.refresh_projects()

    def _show_status(self, message: str) -> None:
        self._status_label.setText(message)

    # ------------------------------------------------------------------
    # Window lifecycle
    # ------------------------------------------------------------------

    def _restore_geometry(self) -> None:
        geom = self.settings.get("window_geometry")
        if geom:
            try:
                from PySide6.QtCore import QByteArray

                self.restoreGeometry(QByteArray.fromHex(geom.encode()))
            except Exception:
                pass

    def closeEvent(self, event) -> None:  # type: ignore[override]
        self.settings.set("window_geometry", self.saveGeometry().toHex().data().decode())
        self.settings.save()
        super().closeEvent(event)
