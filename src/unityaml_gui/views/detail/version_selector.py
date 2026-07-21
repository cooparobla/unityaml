"""Version selector widget — a labelled combo box for switching file versions."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Signal
from PySide6.QtWidgets import QComboBox, QHBoxLayout, QLabel, QWidget

from unityaml.base import FileVersion


class VersionSelector(QWidget):
    """A compact combo box that lets the user pick which version to inspect."""

    version_changed = Signal(FileVersion)  # emitted on user selection

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(6)

        lbl = QLabel("Version:")
        lbl.setObjectName("versionLabel")
        layout.addWidget(lbl)

        self._combo = QComboBox()
        self._combo.setMinimumWidth(100)
        layout.addWidget(self._combo)
        layout.addStretch()

        self._versions: list[FileVersion] = []
        self._combo.currentIndexChanged.connect(self._on_index_changed)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_versions(self, versions: list[FileVersion], active: FileVersion | None = None) -> None:
        """Populate the combo with a list of versions."""
        self._combo.blockSignals(True)
        self._versions = sorted(versions, reverse=True)
        self._combo.clear()
        for v in self._versions:
            label = v.label or "unversioned"
            self._combo.addItem(label)

        # Select the active version
        if active and self._versions:
            try:
                idx = self._versions.index(active)
                self._combo.setCurrentIndex(idx)
            except ValueError:
                self._combo.setCurrentIndex(0)
        self._combo.blockSignals(False)

    def current_version(self) -> FileVersion | None:
        idx = self._combo.currentIndex()
        if 0 <= idx < len(self._versions):
            return self._versions[idx]
        return None

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_index_changed(self, idx: int) -> None:
        if 0 <= idx < len(self._versions):
            self.version_changed.emit(self._versions[idx])
