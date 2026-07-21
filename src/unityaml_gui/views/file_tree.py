"""Lazy-loading, version-grouping file tree model and view.

Architecture
------------
FileTreeNode      — lightweight node stored in the model
FileTreeModel     — QAbstractItemModel backed by FileTreeNodes
FileTreeView      — QTreeView subclass with context menu & helpers
VersionGroupProxy — NOT used: grouping is done directly in FileTreeModel
                    so we avoid two levels of model indirection.
"""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

from PySide6.QtCore import (
    QAbstractItemModel,
    QModelIndex,
    Qt,
    Signal,
)
from PySide6.QtGui import QColor, QFont, QIcon
from PySide6.QtWidgets import (
    QAbstractItemView,
    QMenu,
    QTreeView,
)

from unityaml.versioning import group_versioned_files, highest_version, parse_version

# ──────────────────────────────────────────────────────────────────────────────
# Node
# ──────────────────────────────────────────────────────────────────────────────

class FileTreeNode:
    """One row in the tree."""

    __slots__ = (
        "path",
        "is_dir",
        "display_name",
        "version_label",
        "parent",
        "children",
        "loaded",
        "all_version_paths",  # list[Path] for versioned files
    )

    def __init__(
        self,
        path: Path,
        is_dir: bool,
        display_name: str,
        parent: "FileTreeNode | None" = None,
        version_label: str = "",
        all_version_paths: list[Path] | None = None,
    ) -> None:
        self.path = path
        self.is_dir = is_dir
        self.display_name = display_name
        self.version_label = version_label
        self.parent = parent
        self.children: list[FileTreeNode] = []
        self.loaded = False
        self.all_version_paths: list[Path] = all_version_paths or [path]

    def row(self) -> int:
        if self.parent:
            return self.parent.children.index(self)
        return 0


# ──────────────────────────────────────────────────────────────────────────────
# Model
# ──────────────────────────────────────────────────────────────────────────────

# Custom roles
PathRole = Qt.ItemDataRole.UserRole + 1
NodeRole = Qt.ItemDataRole.UserRole + 2


class FileTreeModel(QAbstractItemModel):
    """Lazy-loading file tree with version grouping.

    Directories are always shown.  Files are shown only if their extension
    matches one of the active filters.  Versioned siblings are collapsed into
    a single row showing the highest version.
    """

    def __init__(self, root: Path, file_filter: list[str], parent: Any = None) -> None:
        super().__init__(parent)
        self.root_path = root
        self.file_filter = [f.lower() for f in file_filter]
        self._root_node = FileTreeNode(root, True, root.name)
        self._load_children(self._root_node)  # load top level eagerly

    # ------------------------------------------------------------------
    # QAbstractItemModel interface
    # ------------------------------------------------------------------

    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()) -> QModelIndex:
        if not self.hasIndex(row, column, parent):
            return QModelIndex()
        parent_node = parent.internalPointer() if parent.isValid() else self._root_node
        if row < len(parent_node.children):
            return self.createIndex(row, column, parent_node.children[row])
        return QModelIndex()

    def parent(self, index: QModelIndex) -> QModelIndex:  # type: ignore[override]
        if not index.isValid():
            return QModelIndex()
        node: FileTreeNode = index.internalPointer()
        if node.parent is None or node.parent is self._root_node:
            return QModelIndex()
        return self.createIndex(node.parent.row(), 0, node.parent)

    def rowCount(self, parent: QModelIndex = QModelIndex()) -> int:
        node = parent.internalPointer() if parent.isValid() else self._root_node
        return len(node.children)

    def columnCount(self, parent: QModelIndex = QModelIndex()) -> int:
        return 1

    def hasChildren(self, parent: QModelIndex = QModelIndex()) -> bool:
        node = parent.internalPointer() if parent.isValid() else self._root_node
        if node.is_dir:
            if not node.loaded:
                # Optimistically return True to show expand arrow;
                # loading happens in canFetchMore/fetchMore
                return True
            return bool(node.children)
        return False

    def canFetchMore(self, parent: QModelIndex) -> bool:
        if not parent.isValid():
            return False
        node: FileTreeNode = parent.internalPointer()
        return node.is_dir and not node.loaded

    def fetchMore(self, parent: QModelIndex) -> None:
        if not parent.isValid():
            return
        node: FileTreeNode = parent.internalPointer()
        if node.loaded:
            return
        self._load_children(node)
        # Notify the view
        if node.children:
            self.beginInsertRows(parent, 0, len(node.children) - 1)
            self.endInsertRows()

    def data(self, index: QModelIndex, role: int = Qt.ItemDataRole.DisplayRole) -> Any:
        if not index.isValid():
            return None
        node: FileTreeNode = index.internalPointer()

        if role == Qt.ItemDataRole.DisplayRole:
            return node.display_name
        if role == Qt.ItemDataRole.DecorationRole:
            return _icon_for_node(node)
        if role == Qt.ItemDataRole.ForegroundRole:
            if not node.is_dir and node.version_label:
                return QColor("#9AA0C0")
            if not node.is_dir:
                return QColor("#C4C8E0")
            return QColor("#E2E4F0")
        if role == Qt.ItemDataRole.FontRole:
            if node.is_dir:
                f = QFont()
                f.setWeight(QFont.Weight.Medium)
                return f
            if node.version_label:
                f = QFont()
                f.setItalic(True)
                return f
            return None
        if role == PathRole:
            return node.path
        if role == NodeRole:
            return node
        if role == Qt.ItemDataRole.ToolTipRole:
            return str(node.path)
        return None

    def flags(self, index: QModelIndex) -> Qt.ItemFlag:
        if not index.isValid():
            return Qt.ItemFlag.NoItemFlags
        return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_filter(self, extensions: list[str]) -> None:
        """Update the extension filter and refresh the tree."""
        self.file_filter = [e.lower() for e in extensions]
        self._invalidate_all(self._root_node)
        self.beginResetModel()
        self._root_node.children.clear()
        self._root_node.loaded = False
        self._load_children(self._root_node)
        self.endResetModel()

    def refresh(self) -> None:
        """Rescan the entire tree."""
        self.beginResetModel()
        self._invalidate_all(self._root_node)
        self._root_node.children.clear()
        self._root_node.loaded = False
        self._load_children(self._root_node)
        self.endResetModel()

    def refresh_node(self, index: QModelIndex) -> None:
        """Rescan a single directory node."""
        if not index.isValid():
            return
        node: FileTreeNode = index.internalPointer()
        if not node.is_dir:
            return
        old_count = len(node.children)
        if old_count:
            self.beginRemoveRows(index, 0, old_count - 1)
            node.children.clear()
            node.loaded = False
            self.endRemoveRows()
        self._load_children(node)
        if node.children:
            self.beginInsertRows(index, 0, len(node.children) - 1)
            self.endInsertRows()

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------

    def _load_children(self, node: FileTreeNode) -> None:
        """Scan a directory and populate node.children."""
        node.loaded = True
        try:
            entries = sorted(node.path.iterdir(), key=lambda p: (not p.is_dir(), p.name.lower()))
        except PermissionError:
            return

        dirs = [e for e in entries if e.is_dir() and not e.name.startswith(".")]
        files = [e for e in entries if e.is_file() and self._accept(e)]

        # Add directory children
        for d in dirs:
            child = FileTreeNode(d, True, d.name, parent=node)
            node.children.append(child)

        # Group files by canonical name + extension → version grouping
        groups = group_versioned_files(files)
        seen_canonical: set[str] = set()
        for e in files:
            name, _ver = parse_version(e)
            key = f"{name}{e.suffix}"
            if key in seen_canonical:
                continue
            seen_canonical.add(key)
            versions_for_key = groups.get(key, [])
            if not versions_for_key:
                continue
            highest = highest_version(versions_for_key)
            # Display name
            if highest.major == 0 and highest.minor == 0:
                display = e.name
                version_label = ""
            else:
                display = f"{name}{e.suffix}  ({highest.label})"
                version_label = highest.label
            all_ver_paths = [v.path for v in versions_for_key]
            child = FileTreeNode(
                path=highest.path,
                is_dir=False,
                display_name=display,
                parent=node,
                version_label=version_label,
                all_version_paths=all_ver_paths,
            )
            node.children.append(child)

    def _accept(self, path: Path) -> bool:
        return path.suffix.lower() in self.file_filter

    def _invalidate_all(self, node: FileTreeNode) -> None:
        node.loaded = False
        for child in node.children:
            self._invalidate_all(child)


# ──────────────────────────────────────────────────────────────────────────────
# View
# ──────────────────────────────────────────────────────────────────────────────

class FileTreeView(QTreeView):
    """QTreeView wired to FileTreeModel with right-click context menu."""

    file_selected = Signal(Path, list)   # (highest_version_path, [all_version_paths])
    export_requested = Signal(Path)
    add_to_project_requested = Signal(Path)
    open_external_requested = Signal(Path)
    refresh_requested = Signal()

    def __init__(self, root: Path, file_filter: list[str], parent: Any = None) -> None:
        super().__init__(parent)
        self._tree_model = FileTreeModel(root, file_filter, self)
        self.setModel(self._tree_model)

        self.setHeaderHidden(True)
        self.setAnimated(True)
        self.setUniformRowHeights(True)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self._show_context_menu)
        self.selectionModel().selectionChanged.connect(self._on_selection_changed)

        # All nodes start collapsed (model root children are loaded but collapsed)
        self.collapseAll()

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------

    def set_filter(self, extensions: list[str]) -> None:
        self._tree_model.set_filter(extensions)

    def refresh(self) -> None:
        self._tree_model.refresh()

    @property
    def tree_model(self) -> FileTreeModel:
        return self._tree_model

    # ------------------------------------------------------------------
    # Slots
    # ------------------------------------------------------------------

    def _on_selection_changed(self, selected, _deselected) -> None:
        indexes = selected.indexes()
        if not indexes:
            return
        node: FileTreeNode = indexes[0].internalPointer()
        if not node.is_dir:
            self.file_selected.emit(node.path, node.all_version_paths)

    def _show_context_menu(self, pos) -> None:
        index = self.indexAt(pos)
        if not index.isValid():
            return
        node: FileTreeNode = index.internalPointer()
        menu = QMenu(self)

        if not node.is_dir:
            if node.path.suffix.lower() == ".blend":
                act_export = menu.addAction("⚡ Export → YAML")
                act_export.triggered.connect(lambda: self.export_requested.emit(node.path))
            act_open = menu.addAction("🔗 Open in External Editor")
            act_open.triggered.connect(lambda: self.open_external_requested.emit(node.path))
            act_add = menu.addAction("📌 Add to Active Project")
            act_add.triggered.connect(lambda: self.add_to_project_requested.emit(node.path))
            menu.addSeparator()

        act_refresh = menu.addAction("⟳ Refresh")
        act_refresh.triggered.connect(self.refresh_requested.emit)
        menu.exec(self.viewport().mapToGlobal(pos))


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────

_EXT_ICONS: dict[str, str] = {
    ".blend": "📦",
    ".yaml": "📄",
    ".yml": "📄",
    ".json": "📄",
    ".png": "🖼",
    ".jpg": "🖼",
    ".jpeg": "🖼",
    ".gif": "🖼",
    ".bmp": "🖼",
    ".tga": "🖼",
    ".webp": "🖼",
}


def _icon_for_node(node: FileTreeNode) -> str:
    if node.is_dir:
        return "📁"
    return _EXT_ICONS.get(node.path.suffix.lower(), "📄")
