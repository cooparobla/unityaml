"""Detail panel for .json files — displays JsonProperties with a syntax-highlighted preview."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtGui import QColor, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QVBoxLayout,
    QWidget,
)

from unityaml.json_file import JsonFileHandler, JsonProperties
from unityaml_gui.views.detail.version_selector import VersionSelector


class JsonDetailPanel(QWidget):
    """Renders JsonProperties for a selected .json file."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._props: JsonProperties | None = None
        self._handler = JsonFileHandler()
        self._build_ui()

    # ------------------------------------------------------------------
    # UI construction
    # ------------------------------------------------------------------

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        self._title = QLabel()
        self._title.setProperty("heading", True)
        root.addWidget(self._title)

        self._path_label = QLabel()
        self._path_label.setProperty("subheading", True)
        self._path_label.setWordWrap(True)
        root.addWidget(self._path_label)

        self._version_sel = VersionSelector()
        self._version_sel.version_changed.connect(self._on_version_changed)
        root.addWidget(self._version_sel)

        root.addWidget(_separator())

        group = QGroupBox("File Info")
        glayout = QVBoxLayout(group)
        glayout.setSpacing(6)
        self._keys_label = _prop_row(glayout, "Top-level Keys")
        self._size_label = _prop_row(glayout, "File Size")
        self._modified_label = _prop_row(glayout, "Last Modified")
        self._projects_label = _prop_row(glayout, "Projects")
        root.addWidget(group)

        root.addWidget(_separator())

        preview_lbl = QLabel("Preview")
        preview_lbl.setProperty("subheading", True)
        root.addWidget(preview_lbl)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setMaximumHeight(260)
        self._highlighter = JsonHighlighter(self._preview.document())
        root.addWidget(self._preview)

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
        if not self._props:
            return
        p = self._props
        self._title.setText(p.path.name)
        self._path_label.setText(str(p.path))
        self._keys_label.setText(", ".join(p.top_level_keys[:8]) or "—")
        self._size_label.setText(_fmt_size(p.file_size_bytes))
        self._modified_label.setText(p.last_modified.strftime("%Y-%m-%d %H:%M"))
        self._projects_label.setText(", ".join(p.projects) if p.projects else "—")

        content = self._handler.read_content(p)
        lines = content.splitlines()
        if len(lines) > 200:
            content = "\n".join(lines[:200]) + "\n... (truncated)"
        self._preview.setPlainText(content)

    def _on_version_changed(self, version) -> None:
        if version and version.path.exists():
            self.load(version.path, self._all_version_paths)


# ──────────────────────────────────────────────────────────────────────────────
# JSON syntax highlighter
# ──────────────────────────────────────────────────────────────────────────────

class JsonHighlighter(QSyntaxHighlighter):
    """Minimal JSON syntax highlighter."""

    def __init__(self, doc) -> None:
        super().__init__(doc)
        import re

        self._rules: list[tuple] = []
        self._add(r'"[^"]*"\s*:', "#9AA0C0")    # keys
        self._add(r':\s*"[^"]*"', "#7EC8A0")    # string values
        self._add(r'\b(true|false|null)\b', "#C090D8")  # literals
        self._add(r'\b\d+(?:\.\d+)?\b', "#E8A84C")      # numbers
        self._add(r'[{}\[\]]', "#5E6AD2")               # brackets

    def _add(self, pattern: str, color: str) -> None:
        import re

        fmt = QTextCharFormat()
        fmt.setForeground(QColor(color))
        self._rules.append((re.compile(pattern), fmt))

    def highlightBlock(self, text: str) -> None:
        for regex, fmt in self._rules:
            for m in regex.finditer(text):
                self.setFormat(m.start(), m.end() - m.start(), fmt)


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
    key.setFixedWidth(110)
    val = QLabel("—")
    val.setWordWrap(True)
    row.addWidget(key)
    row.addWidget(val, 1)
    layout.addLayout(row)
    return val
