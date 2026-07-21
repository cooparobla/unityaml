"""Detail panel dispatcher — shows the correct type-specific sub-panel.

Receives a file path, loads the matching handler, and swaps to the
corresponding panel in a QStackedWidget.
"""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import (
    QLabel,
    QScrollArea,
    QSizePolicy,
    QStackedWidget,
    QVBoxLayout,
    QWidget,
)

from unityaml_gui.views.detail.blend_detail import BlendDetailPanel
from unityaml_gui.views.detail.image_detail import ImageDetailPanel
from unityaml_gui.views.detail.json_detail import JsonDetailPanel
from unityaml_gui.views.detail.yaml_detail import YamlDetailPanel

_IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".gif", ".bmp", ".tga", ".webp"}


class DetailPanel(QWidget):
    """Right-side panel that dispatches to file-type-specific sub-panels."""

    export_requested = Signal(Path)
    status_message = Signal(str)

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)

        self._stack = QStackedWidget()

        # Index 0 — empty / placeholder
        self._empty_panel = _EmptyPanel()
        self._stack.addWidget(self._empty_panel)      # 0

        # Index 1 — .blend
        self._blend_panel = BlendDetailPanel()
        self._blend_panel.export_requested.connect(self.export_requested)
        self._stack.addWidget(_scrolled(self._blend_panel))  # 1

        # Index 2 — image
        self._image_panel = ImageDetailPanel()
        self._stack.addWidget(_scrolled(self._image_panel))  # 2

        # Index 3 — yaml
        self._yaml_panel = YamlDetailPanel()
        self._stack.addWidget(_scrolled(self._yaml_panel))   # 3

        # Index 4 — json
        self._json_panel = JsonDetailPanel()
        self._stack.addWidget(_scrolled(self._json_panel))   # 4

        root.addWidget(self._stack)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def show_file(self, path: Path, all_version_paths: list[Path]) -> None:
        """Load and display properties for the given file."""
        ext = path.suffix.lower()
        try:
            if ext == ".blend":
                self._blend_panel.load(path, all_version_paths)
                self._stack.setCurrentIndex(1)
            elif ext in _IMAGE_EXTS:
                self._image_panel.load(path, all_version_paths)
                self._stack.setCurrentIndex(2)
            elif ext in (".yaml", ".yml"):
                self._yaml_panel.load(path, all_version_paths)
                self._stack.setCurrentIndex(3)
            elif ext == ".json":
                self._json_panel.load(path, all_version_paths)
                self._stack.setCurrentIndex(4)
            else:
                self._stack.setCurrentIndex(0)
        except Exception as e:
            self.status_message.emit(f"Error loading {path.name}: {e}")
            self._stack.setCurrentIndex(0)

    def clear(self) -> None:
        self._stack.setCurrentIndex(0)

    def refresh_projects(self, projects: list[str], path: Path | None) -> None:
        """Update the project membership list after project changes."""
        # Reload the currently shown panel if applicable
        if path:
            ext = path.suffix.lower()
            if ext == ".blend" and self._stack.currentIndex() == 1:
                self._blend_panel._props and setattr(
                    self._blend_panel._props, "projects", projects
                )
            # Other panels similarly — simplified: just re-show same file
            if self._stack.currentIndex() > 0:
                self.show_file(path, [path])


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

class _EmptyPanel(QWidget):
    """Shown when no file is selected."""

    def __init__(self) -> None:
        super().__init__()
        layout = QVBoxLayout(self)
        layout.setContentsMargins(32, 48, 32, 32)
        lbl = QLabel("Select a file to view its properties")
        lbl.setProperty("subheading", True)
        layout.addWidget(lbl)
        layout.addStretch()


def _scrolled(widget: QWidget) -> QScrollArea:
    """Wrap widget in a scroll area."""
    scroll = QScrollArea()
    scroll.setWidgetResizable(True)
    scroll.setWidget(widget)
    scroll.setFrameShape(scroll.Shape.NoFrame)
    return scroll
