"""Project detail panel — shows name, config files, asset references, actions."""

from __future__ import annotations

import os
import subprocess
import sys
from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QListWidget,
    QListWidgetItem,
    QProgressDialog,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from unityaml.project import ProjectConfig


class ProjectDetailPanel(QWidget):
    """Right-side panel showing full details for a selected project."""

    status_message = Signal(str)
    project_changed = Signal()  # emitted after mutation

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._project: ProjectConfig | None = None
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Header ────────────────────────────────────────────────────
        self._name_label = QLabel()
        self._name_label.setProperty("heading", True)
        root.addWidget(self._name_label)

        self._path_label = QLabel()
        self._path_label.setProperty("subheading", True)
        self._path_label.setWordWrap(True)
        root.addWidget(self._path_label)

        self._created_label = QLabel()
        root.addWidget(self._created_label)

        root.addWidget(_separator())

        # ── Config files ──────────────────────────────────────────────
        cfg_group = QGroupBox("Config Files")
        cfg_layout = QVBoxLayout(cfg_group)
        self._cfg_list = QListWidget()
        self._cfg_list.setMaximumHeight(120)
        self._cfg_list.setAlternatingRowColors(True)
        cfg_layout.addWidget(self._cfg_list)

        cfg_btn_row = QHBoxLayout()
        self._remove_cfg_btn = QPushButton("Remove Selected")
        self._remove_cfg_btn.setProperty("danger", True)
        self._remove_cfg_btn.clicked.connect(self._on_remove_config)
        cfg_btn_row.addWidget(self._remove_cfg_btn)
        cfg_btn_row.addStretch()
        cfg_layout.addLayout(cfg_btn_row)
        root.addWidget(cfg_group)

        # ── Asset references ──────────────────────────────────────────
        ref_group = QGroupBox("Asset References")
        ref_layout = QVBoxLayout(ref_group)
        self._ref_list = QListWidget()
        self._ref_list.setAlternatingRowColors(True)
        ref_layout.addWidget(self._ref_list)

        ref_btn_row = QHBoxLayout()
        self._remove_ref_btn = QPushButton("Remove Selected")
        self._remove_ref_btn.setProperty("danger", True)
        self._remove_ref_btn.clicked.connect(self._on_remove_ref)
        ref_btn_row.addWidget(self._remove_ref_btn)
        ref_btn_row.addStretch()
        ref_layout.addLayout(ref_btn_row)
        root.addWidget(ref_group)

        root.addWidget(_separator())

        # ── Action buttons ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._export_all_btn = QPushButton("⚡ Export All")
        self._export_all_btn.setProperty("accent", True)
        self._export_all_btn.clicked.connect(self._on_export_all)
        btn_row.addWidget(self._export_all_btn)

        self._open_folder_btn = QPushButton("📂 Open Folder")
        self._open_folder_btn.clicked.connect(self._on_open_folder)
        btn_row.addWidget(self._open_folder_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        root.addStretch()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, project: ProjectConfig) -> None:
        self._project = project
        self._refresh_ui()

    def clear(self) -> None:
        self._project = None
        self._name_label.setText("")
        self._path_label.setText("")
        self._created_label.setText("")
        self._cfg_list.clear()
        self._ref_list.clear()

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _refresh_ui(self) -> None:
        if not self._project:
            return
        p = self._project
        self._name_label.setText(p.name)
        self._path_label.setText(str(p.project_dir))
        self._created_label.setText(f"Created: {p.created.strftime('%Y-%m-%d')}")

        # Config files
        self._cfg_list.clear()
        for cfg in p.config_files:
            item = QListWidgetItem(f"📄 {cfg.name}")
            item.setData(Qt.ItemDataRole.UserRole, cfg)
            item.setToolTip(str(cfg))
            self._cfg_list.addItem(item)

        # Asset references
        self._ref_list.clear()
        _ICONS = {"blend": "📦", "image": "🖼", "yaml": "📄", "json": "📄", "unknown": "📄"}
        for ref in p.asset_refs:
            icon = _ICONS.get(ref.asset_type.value, "📄")
            label = f"{icon} {ref.display_name}"
            item = QListWidgetItem(label)
            item.setData(Qt.ItemDataRole.UserRole, ref)
            item.setToolTip(str(ref.path))
            self._ref_list.addItem(item)

    def _on_remove_config(self) -> None:
        if not self._project:
            return
        item = self._cfg_list.currentItem()
        if item:
            path: Path = item.data(Qt.ItemDataRole.UserRole)
            self._project.remove_config_file(path)
            self._refresh_ui()
            self.project_changed.emit()
            self.status_message.emit(f"Removed config: {path.name}")

    def _on_remove_ref(self) -> None:
        if not self._project:
            return
        item = self._ref_list.currentItem()
        if item:
            from unityaml.project import AssetRef

            ref: AssetRef = item.data(Qt.ItemDataRole.UserRole)
            self._project.remove_asset_ref(ref.path)
            self._refresh_ui()
            self.project_changed.emit()
            self.status_message.emit(f"Removed ref: {ref.path.name}")

    def _on_export_all(self) -> None:
        if not self._project:
            return
        from unityaml.base import AssetType

        blend_refs = [r for r in self._project.asset_refs if r.asset_type == AssetType.BLEND]
        if not blend_refs:
            self.status_message.emit("No .blend assets in this project")
            return

        dlg = QProgressDialog(
            f"Exporting {len(blend_refs)} .blend file(s)…",
            "Cancel",
            0,
            len(blend_refs),
            self,
        )
        dlg.setWindowModality(Qt.WindowModality.WindowModal)
        dlg.setMinimumDuration(0)

        errors = []
        for i, ref in enumerate(blend_refs):
            if dlg.wasCanceled():
                break
            dlg.setLabelText(f"Exporting {ref.path.name}…")
            dlg.setValue(i)
            try:
                from blender_export.api import export_blend

                output = ref.path.with_suffix(".yaml")
                export_blend(ref.path, output)
            except Exception as e:
                errors.append(f"{ref.path.name}: {e}")

        dlg.setValue(len(blend_refs))
        if errors:
            self.status_message.emit(f"Export done with {len(errors)} error(s)")
        else:
            self.status_message.emit(f"Exported {len(blend_refs)} .blend file(s) successfully")

    def _on_open_folder(self) -> None:
        if not self._project:
            return
        path = self._project.project_dir
        path.mkdir(parents=True, exist_ok=True)
        try:
            if sys.platform == "win32":
                os.startfile(str(path))
            elif sys.platform == "darwin":
                subprocess.Popen(["open", str(path)])
            else:
                subprocess.Popen(["xdg-open", str(path)])
        except Exception as e:
            self.status_message.emit(f"Could not open folder: {e}")


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #2A2B38;")
    return line
