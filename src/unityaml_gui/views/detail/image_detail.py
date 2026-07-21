"""Detail panel for image files — displays ImageProperties with a thumbnail."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QSizePolicy,
    QVBoxLayout,
    QWidget,
)

from unityaml.image import ImageFileHandler, ImageProperties
from unityaml_gui.views.detail.version_selector import VersionSelector


class ImageDetailPanel(QWidget):
    """Renders ImageProperties for a selected image file."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._props: ImageProperties | None = None
        self._handler = ImageFileHandler()
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

        root.addWidget(_separator())

        # ── Thumbnail ─────────────────────────────────────────────────
        self._thumbnail = QLabel()
        self._thumbnail.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self._thumbnail.setMinimumHeight(160)
        self._thumbnail.setMaximumHeight(240)
        self._thumbnail.setSizePolicy(
            QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed
        )
        self._thumbnail.setStyleSheet(
            "background: #0F1016; border: 1px solid #2A2B38; border-radius: 6px;"
        )
        root.addWidget(self._thumbnail)

        # ── Properties group ──────────────────────────────────────────
        group = QGroupBox("Image Properties")
        layout = QVBoxLayout(group)
        layout.setSpacing(6)

        self._size_label = _prop_row(layout, "Dimensions")
        self._channels_label = _prop_row(layout, "Channels")
        self._format_label = _prop_row(layout, "Format")
        self._filesize_label = _prop_row(layout, "File Size")
        self._modified_label = _prop_row(layout, "Last Modified")

        root.addWidget(group)

        # ── Projects section ──────────────────────────────────────────
        proj_group = QGroupBox("Referenced by Projects")
        proj_layout = QVBoxLayout(proj_group)
        self._projects_label = QLabel("—")
        self._projects_label.setWordWrap(True)
        proj_layout.addWidget(self._projects_label)
        root.addWidget(proj_group)

        root.addStretch()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def load(self, path: Path, all_version_paths: list[Path]) -> None:
        props = self._handler.load(path)
        self._props = props
        self._all_version_paths = all_version_paths
        self._refresh_ui()

        self._version_sel.setVisible(props.is_versioned)
        if props.is_versioned:
            self._version_sel.set_versions(props.versions, props.active_version)

    # ------------------------------------------------------------------
    # Internal
    # ------------------------------------------------------------------

    def _refresh_ui(self) -> None:
        if self._props is None:
            return
        p = self._props
        self._title.setText(p.path.stem)
        self._path_label.setText(str(p.path))

        # Thumbnail
        px = QPixmap(str(p.path))
        if not px.isNull():
            px = px.scaled(
                280, 200,
                Qt.AspectRatioMode.KeepAspectRatio,
                Qt.TransformationMode.SmoothTransformation,
            )
            self._thumbnail.setPixmap(px)
            self._thumbnail.setText("")
        else:
            self._thumbnail.setPixmap(QPixmap())
            self._thumbnail.setText("⚠ Preview unavailable")

        w_str = f"{p.width} × {p.height} px" if p.width and p.height else "—"
        self._size_label.setText(w_str)

        ch_map = {1: "Grayscale", 2: "Grayscale + Alpha", 3: "RGB", 4: "RGBA"}
        self._channels_label.setText(ch_map.get(p.channels, str(p.channels) or "—"))
        self._format_label.setText(p.format or "—")
        self._filesize_label.setText(_fmt_size(p.file_size_bytes))
        self._modified_label.setText(p.last_modified.strftime("%Y-%m-%d %H:%M"))
        self._projects_label.setText(", ".join(p.projects) if p.projects else "—")

    def _on_version_changed(self, version) -> None:
        if version and version.path.exists():
            self.load(version.path, self._all_version_paths)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

def _fmt_size(b: int) -> str:
    if b == 0:
        return "—"
    for unit in ("B", "KB", "MB", "GB"):
        if b < 1024:
            return f"{b:.1f} {unit}"
        b /= 1024  # type: ignore[assignment]
    return f"{b:.1f} TB"


def _separator() -> QFrame:
    line = QFrame()
    line.setFrameShape(QFrame.Shape.HLine)
    line.setStyleSheet("color: #2A2B38;")
    return line


def _prop_row(layout: QVBoxLayout, label: str) -> QLabel:
    row = QHBoxLayout()
    key = QLabel(label + ":")
    key.setProperty("subheading", True)
    key.setFixedWidth(90)
    val = QLabel("—")
    val.setWordWrap(True)
    row.addWidget(key)
    row.addWidget(val, 1)
    layout.addLayout(row)
    return val
