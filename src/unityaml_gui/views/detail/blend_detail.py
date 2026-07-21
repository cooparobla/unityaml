"""Detail panel for .blend files — displays BlenderProperties."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt, Signal
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPushButton,
    QScrollArea,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from unityaml.blend import BlenderFileHandler, BlenderProperties
from unityaml_gui.views.detail.version_selector import VersionSelector


class BlendDetailPanel(QWidget):
    """Renders BlenderProperties for a selected .blend file."""

    export_requested = Signal(Path)    # user clicked Export
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._props: BlenderProperties | None = None
        self._handler = BlenderFileHandler()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # ── Header ────────────────────────────────────────────────────
        self._title = QLabel()
        self._title.setProperty("heading", True)
        self._title.setWordWrap(True)
        root.addWidget(self._title)

        self._path_label = QLabel()
        self._path_label.setProperty("subheading", True)
        self._path_label.setWordWrap(True)
        root.addWidget(self._path_label)

        # ── Version selector ──────────────────────────────────────────
        self._version_sel = VersionSelector()
        self._version_sel.version_changed.connect(self._on_version_changed)
        root.addWidget(self._version_sel)

        # ── Separator ─────────────────────────────────────────────────
        root.addWidget(_separator())

        # ── Properties group ──────────────────────────────────────────
        props_group = QGroupBox("Blend Properties")
        props_layout = QVBoxLayout(props_group)
        props_layout.setSpacing(6)

        self._objects_label = _prop_row(props_layout, "Objects")
        self._meshes_label = _prop_row(props_layout, "Meshes")
        self._armature_label = _prop_row(props_layout, "Has Armature")
        self._anims_label = _prop_row(props_layout, "Animations")
        self._modified_label = _prop_row(props_layout, "Last Modified")
        self._exported_label = _prop_row(props_layout, "Last Exported")
        self._status_label = _prop_row(props_layout, "Export Status")

        root.addWidget(props_group)

        # ── Projects section ──────────────────────────────────────────
        proj_group = QGroupBox("Referenced by Projects")
        proj_layout = QVBoxLayout(proj_group)
        self._projects_label = QLabel("—")
        self._projects_label.setWordWrap(True)
        proj_layout.addWidget(self._projects_label)
        root.addWidget(proj_group)

        # ── Action buttons ────────────────────────────────────────────
        btn_row = QHBoxLayout()
        self._export_btn = QPushButton("⚡ Export → YAML")
        self._export_btn.setProperty("accent", True)
        self._export_btn.clicked.connect(self._on_export_clicked)
        btn_row.addWidget(self._export_btn)
        btn_row.addStretch()
        root.addLayout(btn_row)

        root.addStretch()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, path: Path, all_version_paths: list[Path]) -> None:
        props = self._handler.load(path)
        self._props = props
        self._all_version_paths = all_version_paths
        self._refresh_ui()

        # Populate version selector
        self._version_sel.setVisible(props.is_versioned)
        if props.is_versioned:
            self._version_sel.set_versions(props.versions, props.active_version)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _refresh_ui(self) -> None:
        if self._props is None:
            return
        p = self._props
        self._title.setText(p.path.stem)
        self._path_label.setText(str(p.path))

        obj_count = len(p.object_names)
        obj_text = (
            ", ".join(p.object_names[:4]) + ("…" if obj_count > 4 else "")
            if p.object_names
            else "—"
        )
        self._objects_label.setText(obj_text)
        self._meshes_label.setText(str(p.mesh_count) if p.mesh_count else "—")
        self._armature_label.setText("✓" if p.has_armature else "—")
        self._anims_label.setText("✓ clips present" if p.has_animations else "—")
        self._modified_label.setText(_fmt_dt(p.last_modified))
        self._exported_label.setText(_fmt_dt(p.last_exported) if p.last_exported else "Never")

        if p.last_exported is None:
            self._status_label.setText("Not exported")
            self._status_label.setProperty("warning", False)
            self._status_label.setProperty("ok", False)
        elif p.stale:
            self._status_label.setText("⚠ Stale — source is newer than export")
            self._status_label.setProperty("warning", True)
            self._status_label.setProperty("ok", False)
        else:
            self._status_label.setText("✓ Up to date")
            self._status_label.setProperty("warning", False)
            self._status_label.setProperty("ok", True)
        _refresh_style(self._status_label)

        self._projects_label.setText(", ".join(p.projects) if p.projects else "—")

    def _on_version_changed(self, version) -> None:
        if version and version.path.exists():
            self.load(version.path, self._all_version_paths)

    def _on_export_clicked(self) -> None:
        if self._props:
            self.export_requested.emit(self._props.path)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_dt(dt) -> str:
    if dt is None:
        return "—"
    return dt.strftime("%Y-%m-%d %H:%M")


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #2A2B38;")
    return line


def _prop_row(layout: QVBoxLayout, label: str) -> QLabel:
    """Add a key:value row to the layout, return the value label."""
    row = QHBoxLayout()
    key = QLabel(label + ":")
    key.setProperty("subheading", True)
    key.setFixedWidth(110)
    val = QLabel("—")
    val.setWordWrap(True)
    row.addWidget(key)
    row.addWidget(val, 1)
    layout.addLayout(row)
    return val


def _refresh_style(widget: QWidget) -> None:
    widget.style().unpolish(widget)
    widget.style().polish(widget)
