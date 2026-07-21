"""Assets tab — file tree (left) + detail panel (right) in a QSplitter.

Also hosts the filter bar and toolbar actions.
"""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Signal, Qt, QThread, QObject
from PySide6.QtWidgets import (
    QCheckBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMessageBox,
    QProgressDialog,
    QPushButton,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from unityaml.app_state import AppState
from unityaml.base import AssetType
from unityaml_gui.settings import AppSettings
from unityaml_gui.views.detail_panel import DetailPanel
from unityaml_gui.views.file_tree import FileTreeView


class AssetsTab(QWidget):
    """Assets tab widget."""

    status_message = Signal(str)

    def __init__(self, state: AppState, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self.state = state
        self._settings = AppSettings()
        self._current_path: Path | None = None
        self._current_all_paths: list[Path] = []
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # ── Filter bar ────────────────────────────────────────────────
        filter_bar = self._build_filter_bar()
        root.addWidget(filter_bar)

        # ── Splitter ──────────────────────────────────────────────────
        self._splitter = QSplitter(Qt.Orientation.Horizontal)

        # Left: tree
        self._tree = FileTreeView(self.state.asset_root, self.state.file_filter)
        self._tree.file_selected.connect(self._on_file_selected)
        self._tree.export_requested.connect(self._on_export_requested)
        self._tree.add_to_project_requested.connect(self._on_add_to_project)
        self._tree.open_external_requested.connect(self._on_open_external)
        self._tree.refresh_requested.connect(self._on_refresh)
        self._splitter.addWidget(self._tree)

        # Right: detail
        self._detail = DetailPanel()
        self._detail.export_requested.connect(self._on_export_requested)
        self._detail.status_message.connect(self.status_message)
        self._splitter.addWidget(self._detail)

        # Restore splitter sizes
        saved = self._settings.get("assets_splitter", None)
        if saved and isinstance(saved, list):
            self._splitter.setSizes([int(s) for s in saved])
        else:
            self._splitter.setSizes([320, 480])

        self._splitter.splitterMoved.connect(self._on_splitter_moved)
        root.addWidget(self._splitter)

    def _build_filter_bar(self) -> QWidget:
        bar = QWidget()
        bar.setFixedHeight(44)
        bar.setStyleSheet("background: #1C1D26; border-bottom: 1px solid #2A2B38;")
        layout = QHBoxLayout(bar)
        layout.setContentsMargins(12, 0, 12, 0)
        layout.setSpacing(8)

        lbl = QLabel("Filter:")
        lbl.setProperty("subheading", True)
        layout.addWidget(lbl)

        self._filter_edit = QLineEdit()
        self._filter_edit.setPlaceholderText(".blend .yaml .json .png")
        self._filter_edit.setText(" ".join(self.state.file_filter))
        self._filter_edit.setMaximumWidth(280)
        self._filter_edit.returnPressed.connect(self._apply_filter)
        layout.addWidget(self._filter_edit)

        apply_btn = QPushButton("Apply")
        apply_btn.setMaximumWidth(60)
        apply_btn.clicked.connect(self._apply_filter)
        layout.addWidget(apply_btn)

        layout.addStretch()

        refresh_btn = QPushButton("⟳ Refresh")
        refresh_btn.setMaximumWidth(90)
        refresh_btn.clicked.connect(self._on_refresh)
        layout.addWidget(refresh_btn)

        return bar

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_file_selected(self, path: Path, all_versions: list[Path]) -> None:
        self._current_path = path
        self._current_all_paths = all_versions
        self._detail.show_file(path, all_versions)
        self.status_message.emit(str(path))

    def _on_export_requested(self, path: Path) -> None:
        """Launch a Blender headless export in a background thread."""
        output = path.with_suffix(".yaml")

        dlg = QProgressDialog(
            f"Exporting {path.name} → {output.name}…", "Cancel", 0, 0, self
        )
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.setMinimumDuration(0)
        dlg.setValue(0)
        dlg.show()

        self._export_thread = _ExportThread(path, output)
        self._export_thread.finished_ok.connect(lambda: self._on_export_done(path, output, dlg, None))
        self._export_thread.finished_err.connect(lambda e: self._on_export_done(path, output, dlg, e))
        dlg.canceled.connect(self._export_thread.terminate)
        self._export_thread.start()

    def _on_export_done(
        self, src: Path, output: Path, dlg: QProgressDialog, error: str | None
    ) -> None:
        dlg.close()
        if error:
            QMessageBox.critical(self, "Export Failed", error)
            self.status_message.emit(f"Export failed: {src.name}")
        else:
            self.status_message.emit(f"Exported → {output}")
            if self._current_path == src:
                self._detail.show_file(src, self._current_all_paths)

    def _on_add_to_project(self, path: Path) -> None:
        if not self.state.active_project:
            self.status_message.emit("No active project — select one in the Projects tab first")
            return
        project = self.state.get_project(self.state.active_project)
        if project is None:
            return
        ext = path.suffix.lower()
        if ext == ".blend":
            asset_type = AssetType.BLEND
        elif ext in (".yaml", ".yml"):
            asset_type = AssetType.YAML
        elif ext == ".json":
            asset_type = AssetType.JSON
        else:
            asset_type = AssetType.IMAGE
        project.add_asset_ref(path, asset_type)
        self.status_message.emit(f"Added {path.name} to project '{project.name}'")

    def _on_open_external(self, path: Path) -> None:
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            self.status_message.emit(f"Could not open: {e}")

    def _on_refresh(self) -> None:
        self._tree.refresh()
        self.status_message.emit("Tree refreshed")

    def _apply_filter(self) -> None:
        raw = self._filter_edit.text()
        exts = [e.strip() for e in raw.split() if e.strip()]
        # Normalise: ensure leading dot
        exts = [e if e.startswith(".") else f".{e}" for e in exts]
        self.state.file_filter = exts
        self._tree.set_filter(exts)
        self.status_message.emit(f"Filter: {' '.join(exts)}")

    def _on_splitter_moved(self, pos: int, _idx: int) -> None:
        self._settings.set("assets_splitter", self._splitter.sizes())
        self._settings.save()

    def refresh_projects(self) -> None:
        """Called when projects change — refresh detail panel project list."""
        if self._current_path:
            self._detail.show_file(self._current_path, self._current_all_paths)


# ──────────────────────────────────────────────────────────────────────────────
# Background export thread
# ──────────────────────────────────────────────────────────────────────────────

class _ExportThread(QThread):
    finished_ok = Signal()
    finished_err = Signal(str)

    def __init__(self, blend_path: Path, output: Path) -> None:
        super().__init__()
        self._blend = blend_path
        self._output = output

    def run(self) -> None:
        try:
            from blender_export.api import export_blend

            export_blend(self._blend, self._output)
            self.finished_ok.emit()
        except Exception as e:
            self.finished_err.emit(str(e))
