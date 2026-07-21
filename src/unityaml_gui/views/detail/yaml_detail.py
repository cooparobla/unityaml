"""Detail panel for .yaml files — displays YamlProperties with syntax-highlighted preview."""

from __future__ import annotations

from pathlib import Path

from PySide6.QtCore import Qt
from PySide6.QtGui import QColor, QFont, QSyntaxHighlighter, QTextCharFormat
from PySide6.QtWidgets import (
    QFrame,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QPlainTextEdit,
    QSplitter,
    QVBoxLayout,
    QWidget,
)

from unityaml.yaml_file import YamlFileHandler, YamlProperties
from unityaml_gui.views.detail.version_selector import VersionSelector


class YamlDetailPanel(QWidget):
    """Renders YamlProperties for a selected .yaml file."""

    def __init__(self, parent: QWidget | None = None) -> None:
        super().__init__(parent)
        self._props: YamlProperties | None = None
        self._handler = YamlFileHandler()
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
        root.addWidget(self._title)

        self._path_label = QLabel()
        self._path_label.setProperty("subheading", True)
        self._path_label.setWordWrap(True)
        root.addWidget(self._path_label)

        self._version_sel = VersionSelector()
        self._version_sel.version_changed.connect(self._on_version_changed)
        root.addWidget(self._version_sel)

        root.addWidget(_separator())

        # ── Tags / badges ─────────────────────────────────────────────
        tag_row = QHBoxLayout()
        self._tag_scene = _make_tag("Scene Export")
        self._tag_config = _make_tag("Config")
        tag_row.addWidget(self._tag_scene)
        tag_row.addWidget(self._tag_config)
        tag_row.addStretch()
        root.addLayout(tag_row)

        # ── Properties group ──────────────────────────────────────────
        group = QGroupBox("File Info")
        glayout = QVBoxLayout(group)
        glayout.setSpacing(6)
        self._keys_label = _prop_row(glayout, "Top-level Keys")
        self._lines_label = _prop_row(glayout, "Line Count")
        self._modified_label = _prop_row(glayout, "Last Modified")
        self._projects_label = _prop_row(glayout, "Projects")
        root.addWidget(group)

        root.addWidget(_separator())

        # ── Text preview ──────────────────────────────────────────────
        preview_lbl = QLabel("Preview")
        preview_lbl.setProperty("subheading", True)
        root.addWidget(preview_lbl)

        self._preview = QPlainTextEdit()
        self._preview.setReadOnly(True)
        self._preview.setMaximumHeight(260)
        self._highlighter = YamlHighlighter(self._preview.document())
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
        self._tag_scene.setVisible(p.is_scene_export)
        self._tag_config.setVisible(p.is_config)
        self._keys_label.setText(", ".join(p.top_level_keys[:8]) or "—")
        self._lines_label.setText(f"{p.line_count:,}")
        self._modified_label.setText(p.last_modified.strftime("%Y-%m-%d %H:%M"))
        self._projects_label.setText(", ".join(p.projects) if p.projects else "—")

        content = self._handler.read_content(p)
        # Truncate huge files
        lines = content.splitlines()
        if len(lines) > 200:
            content = "\n".join(lines[:200]) + "\n... (truncated)"
        self._preview.setPlainText(content)

    def _on_version_changed(self, version) -> None:
        if version and version.path.exists():
            self.load(version.path, self._all_version_paths)


# ──────────────────────────────────────────────────────────────────────────────
# YAML syntax highlighter
# ──────────────────────────────────────────────────────────────────────────────

class YamlHighlighter(QSyntaxHighlighter):
    """Minimal YAML syntax highlighter."""

    def __init__(self, doc) -> None:
        super().__init__(doc)
        import re

        self._rules: list[tuple] = []
        self._add(r"^[\w\-]+(?=\s*:)", "#9AA0C0")   # keys
        self._add(r"(?<=:\s).*$", "#7EC8A0")           # values
        self._add(r"#.*$", "#4A4E6A")                  # comments
        self._add(r"^\s*-\s", "#C090D8")               # list dash
        self._add(r'"[^"]*"', "#E8A84C")               # quoted strings
        self._add(r"'[^']*'", "#E8A84C")               # single-quoted

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


def _make_tag(text: str) -> QLabel:
    lbl = QLabel(text)
    lbl.setProperty("tag", True)
    lbl.setVisible(False)
    return lbl
