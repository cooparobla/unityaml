"""Tests for FileTreeModel and FileTreeView.

Qt strategy
-----------
- FileTreeModel is a QAbstractItemModel — it needs a live QApplication but
  does NOT need to be shown on screen.  We test its API directly (row counts,
  data roles, flags, canFetchMore/fetchMore, set_filter, refresh, version
  grouping).
- FileTreeView is tested for signal wiring only (no user-click simulation
  needed for business logic coverage).

pytest-qt's `qtbot` fixture ensures a QApplication exists.
"""

from __future__ import annotations

from pathlib import Path

import pytest

from PySide6.QtCore import QModelIndex, Qt

from unityaml_gui.views.file_tree import (
    FileTreeModel,
    FileTreeNode,
    FileTreeView,
    NodeRole,
    PathRole,
    _icon_for_node,
)


# ──────────────────────────────────────────────────────────────────────────────
# Helpers
# ──────────────────────────────────────────────────────────────────────────────


def _model(root: Path, exts: list[str] | None = None) -> FileTreeModel:
    if exts is None:
        exts = [".blend", ".yaml", ".json", ".png"]
    return FileTreeModel(root, exts)


# ──────────────────────────────────────────────────────────────────────────────
# FileTreeNode (no Qt required)
# ──────────────────────────────────────────────────────────────────────────────


class TestFileTreeNode:
    def test_row_is_zero_without_parent(self, tmp_path):
        node = FileTreeNode(tmp_path, True, "root")
        assert node.row() == 0

    def test_row_reflects_position_in_parent(self, tmp_path):
        parent = FileTreeNode(tmp_path, True, "parent")
        c1 = FileTreeNode(tmp_path / "a", False, "a", parent=parent)
        c2 = FileTreeNode(tmp_path / "b", False, "b", parent=parent)
        parent.children = [c1, c2]
        assert c1.row() == 0
        assert c2.row() == 1

    def test_all_version_paths_default(self, tmp_path):
        p = tmp_path / "char.blend"
        node = FileTreeNode(p, False, "char.blend")
        assert node.all_version_paths == [p]

    def test_all_version_paths_explicit(self, tmp_path):
        p1 = tmp_path / "char.v1.0.blend"
        p2 = tmp_path / "char.v2.0.blend"
        node = FileTreeNode(p2, False, "char.blend", all_version_paths=[p1, p2])
        assert node.all_version_paths == [p1, p2]

    def test_loaded_starts_false(self, tmp_path):
        node = FileTreeNode(tmp_path, True, "root")
        assert node.loaded is False

    def test_is_dir_attribute(self, tmp_path):
        d = FileTreeNode(tmp_path, True, "dir")
        f = FileTreeNode(tmp_path / "x.blend", False, "x.blend")
        assert d.is_dir is True
        assert f.is_dir is False


# ──────────────────────────────────────────────────────────────────────────────
# _icon_for_node
# ──────────────────────────────────────────────────────────────────────────────


class TestIconForNode:
    def test_dir_gets_folder_icon(self, tmp_path):
        node = FileTreeNode(tmp_path, True, "assets")
        assert _icon_for_node(node) == "📁"

    def test_blend_icon(self, tmp_path):
        node = FileTreeNode(tmp_path / "scene.blend", False, "scene.blend")
        assert _icon_for_node(node) == "📦"

    def test_png_icon(self, tmp_path):
        node = FileTreeNode(tmp_path / "texture.png", False, "texture.png")
        assert _icon_for_node(node) == "🖼"

    def test_yaml_icon(self, tmp_path):
        node = FileTreeNode(tmp_path / "config.yaml", False, "config.yaml")
        assert _icon_for_node(node) == "📄"

    def test_unknown_ext_icon(self, tmp_path):
        node = FileTreeNode(tmp_path / "file.xyz", False, "file.xyz")
        assert _icon_for_node(node) == "📄"


# ──────────────────────────────────────────────────────────────────────────────
# FileTreeModel — structural methods
# ──────────────────────────────────────────────────────────────────────────────


class TestFileTreeModelStructure:
    def test_column_count_always_one(self, qtbot, tmp_path):
        m = _model(tmp_path)
        assert m.columnCount() == 1
        assert m.columnCount(m.index(0, 0)) == 1

    def test_empty_root_has_no_rows(self, qtbot, tmp_path):
        m = _model(tmp_path)
        assert m.rowCount() == 0

    def test_single_file_appears_as_one_row(self, qtbot, tmp_path):
        (tmp_path / "scene.yaml").write_text("x: 1")
        m = _model(tmp_path)
        assert m.rowCount() == 1

    def test_filtered_out_file_not_shown(self, qtbot, tmp_path):
        (tmp_path / "scene.yaml").write_text("x: 1")
        m = _model(tmp_path, exts=[".blend"])  # .yaml not in filter
        assert m.rowCount() == 0

    def test_subdirectory_always_shown(self, qtbot, tmp_path):
        (tmp_path / "models").mkdir()
        m = _model(tmp_path, exts=[".blend"])
        assert m.rowCount() == 1  # dir shown even with no matching files

    def test_hidden_dir_excluded(self, qtbot, tmp_path):
        (tmp_path / ".hidden").mkdir()
        m = _model(tmp_path)
        assert m.rowCount() == 0

    def test_multiple_files_multiple_rows(self, qtbot, tmp_path):
        for name in ["a.yaml", "b.yaml", "c.json"]:
            (tmp_path / name).write_text("{}")
        m = _model(tmp_path)
        assert m.rowCount() == 3

    def test_dirs_before_files(self, qtbot, tmp_path):
        (tmp_path / "models").mkdir()
        (tmp_path / "scene.yaml").write_text("{}")
        m = _model(tmp_path)
        first_index = m.index(0, 0)
        first_node: FileTreeNode = first_index.internalPointer()
        assert first_node.is_dir  # dirs sorted before files


# ──────────────────────────────────────────────────────────────────────────────
# FileTreeModel — data roles
# ──────────────────────────────────────────────────────────────────────────────


class TestFileTreeModelData:
    def test_display_role_file(self, qtbot, tmp_path):
        (tmp_path / "scene.yaml").write_text("{}")
        m = _model(tmp_path)
        idx = m.index(0, 0)
        assert m.data(idx, Qt.ItemDataRole.DisplayRole) == "scene.yaml"

    def test_display_role_dir(self, qtbot, tmp_path):
        (tmp_path / "meshes").mkdir()
        m = _model(tmp_path)
        idx = m.index(0, 0)
        assert m.data(idx, Qt.ItemDataRole.DisplayRole) == "meshes"

    def test_path_role_returns_path(self, qtbot, tmp_path):
        p = tmp_path / "config.json"
        p.write_text("{}")
        m = _model(tmp_path)
        idx = m.index(0, 0)
        result = m.data(idx, PathRole)
        assert isinstance(result, Path)
        assert result.name == "config.json"

    def test_node_role_returns_node(self, qtbot, tmp_path):
        (tmp_path / "x.yaml").write_text("{}")
        m = _model(tmp_path)
        idx = m.index(0, 0)
        node = m.data(idx, NodeRole)
        assert isinstance(node, FileTreeNode)

    def test_tooltip_role_returns_path_string(self, qtbot, tmp_path):
        (tmp_path / "scene.yaml").write_text("{}")
        m = _model(tmp_path)
        idx = m.index(0, 0)
        tooltip = m.data(idx, Qt.ItemDataRole.ToolTipRole)
        assert "scene.yaml" in tooltip

    def test_data_invalid_index_returns_none(self, qtbot, tmp_path):
        m = _model(tmp_path)
        assert m.data(QModelIndex()) is None

    def test_foreground_role_dir_is_light(self, qtbot, tmp_path):
        (tmp_path / "models").mkdir()
        m = _model(tmp_path)
        idx = m.index(0, 0)
        color = m.data(idx, Qt.ItemDataRole.ForegroundRole)
        assert color is not None

    def test_font_role_dir_is_bold_ish(self, qtbot, tmp_path):
        (tmp_path / "models").mkdir()
        m = _model(tmp_path)
        idx = m.index(0, 0)
        font = m.data(idx, Qt.ItemDataRole.FontRole)
        assert font is not None  # dirs get a medium-weight font


# ──────────────────────────────────────────────────────────────────────────────
# FileTreeModel — flags
# ──────────────────────────────────────────────────────────────────────────────


class TestFileTreeModelFlags:
    def test_valid_index_is_enabled_and_selectable(self, qtbot, tmp_path):
        (tmp_path / "scene.yaml").write_text("{}")
        m = _model(tmp_path)
        idx = m.index(0, 0)
        flags = m.flags(idx)
        assert flags & Qt.ItemFlag.ItemIsEnabled
        assert flags & Qt.ItemFlag.ItemIsSelectable

    def test_invalid_index_has_no_flags(self, qtbot, tmp_path):
        m = _model(tmp_path)
        assert m.flags(QModelIndex()) == Qt.ItemFlag.NoItemFlags


# ──────────────────────────────────────────────────────────────────────────────
# FileTreeModel — lazy loading (canFetchMore / fetchMore)
# ──────────────────────────────────────────────────────────────────────────────


class TestFileTreeModelLazyLoad:
    def test_root_level_not_fetchable(self, qtbot, tmp_path):
        m = _model(tmp_path)
        assert m.canFetchMore(QModelIndex()) is False

    def test_unloaded_dir_can_fetch_more(self, qtbot, tmp_path):
        (tmp_path / "models").mkdir()
        m = _model(tmp_path)
        dir_idx = m.index(0, 0)
        # After initial load the root children are loaded but the subdir is not
        node: FileTreeNode = dir_idx.internalPointer()
        node.loaded = False  # force unloaded state
        assert m.canFetchMore(dir_idx) is True

    def test_already_loaded_dir_cannot_fetch_more(self, qtbot, tmp_path):
        (tmp_path / "models").mkdir()
        m = _model(tmp_path)
        dir_idx = m.index(0, 0)
        node: FileTreeNode = dir_idx.internalPointer()
        node.loaded = True
        assert m.canFetchMore(dir_idx) is False

    def test_file_node_cannot_fetch_more(self, qtbot, tmp_path):
        (tmp_path / "x.yaml").write_text("{}")
        m = _model(tmp_path)
        file_idx = m.index(0, 0)
        assert m.canFetchMore(file_idx) is False

    def test_fetch_more_populates_children(self, qtbot, tmp_path):
        subdir = tmp_path / "models"
        subdir.mkdir()
        (subdir / "hero.yaml").write_text("{}")
        m = _model(tmp_path)
        dir_idx = m.index(0, 0)
        node: FileTreeNode = dir_idx.internalPointer()
        node.loaded = False
        node.children.clear()
        m.fetchMore(dir_idx)
        assert len(node.children) == 1
        assert node.children[0].path.name == "hero.yaml"

    def test_has_children_true_for_dir(self, qtbot, tmp_path):
        (tmp_path / "models").mkdir()
        m = _model(tmp_path)
        dir_idx = m.index(0, 0)
        assert m.hasChildren(dir_idx) is True

    def test_has_children_false_for_file(self, qtbot, tmp_path):
        (tmp_path / "x.yaml").write_text("{}")
        m = _model(tmp_path)
        file_idx = m.index(0, 0)
        assert m.hasChildren(file_idx) is False


# ──────────────────────────────────────────────────────────────────────────────
# FileTreeModel — version grouping
# ──────────────────────────────────────────────────────────────────────────────


class TestFileTreeModelVersionGrouping:
    def test_versioned_siblings_collapsed_to_one_row(self, qtbot, tmp_path):
        (tmp_path / "char.v1.0.blend").write_bytes(b"")
        (tmp_path / "char.v2.3.blend").write_bytes(b"")
        m = _model(tmp_path)
        assert m.rowCount() == 1  # both versions → single row

    def test_highest_version_shown_in_display_name(self, qtbot, tmp_path):
        (tmp_path / "char.v1.0.blend").write_bytes(b"")
        (tmp_path / "char.v2.3.blend").write_bytes(b"")
        m = _model(tmp_path)
        idx = m.index(0, 0)
        display = m.data(idx, Qt.ItemDataRole.DisplayRole)
        assert "v2.3" in display

    def test_all_version_paths_stored_on_node(self, qtbot, tmp_path):
        (tmp_path / "char.v1.0.blend").write_bytes(b"")
        (tmp_path / "char.v2.3.blend").write_bytes(b"")
        m = _model(tmp_path)
        idx = m.index(0, 0)
        node: FileTreeNode = idx.internalPointer()
        assert len(node.all_version_paths) == 2

    def test_unversioned_file_shows_plain_name(self, qtbot, tmp_path):
        (tmp_path / "config.yaml").write_text("{}")
        m = _model(tmp_path)
        idx = m.index(0, 0)
        display = m.data(idx, Qt.ItemDataRole.DisplayRole)
        assert display == "config.yaml"
        assert "v" not in display

    def test_different_extensions_not_grouped(self, qtbot, tmp_path):
        (tmp_path / "asset.v1.0.blend").write_bytes(b"")
        (tmp_path / "asset.v1.0.yaml").write_text("{}")
        m = _model(tmp_path)
        # Two separate rows: one .blend, one .yaml
        assert m.rowCount() == 2

    def test_versioned_font_is_italic(self, qtbot, tmp_path):
        (tmp_path / "char.v1.0.blend").write_bytes(b"")
        (tmp_path / "char.v2.3.blend").write_bytes(b"")
        m = _model(tmp_path)
        idx = m.index(0, 0)
        font = m.data(idx, Qt.ItemDataRole.FontRole)
        assert font is not None
        assert font.italic() is True


# ──────────────────────────────────────────────────────────────────────────────
# FileTreeModel — set_filter / refresh
# ──────────────────────────────────────────────────────────────────────────────


class TestFileTreeModelFilter:
    def test_set_filter_changes_visible_files(self, qtbot, tmp_path):
        (tmp_path / "scene.yaml").write_text("{}")
        (tmp_path / "model.blend").write_bytes(b"")
        m = _model(tmp_path, exts=[".blend", ".yaml"])
        assert m.rowCount() == 2
        m.set_filter([".blend"])
        assert m.rowCount() == 1

    def test_set_filter_normalises_case(self, qtbot, tmp_path):
        (tmp_path / "img.PNG").write_bytes(b"")
        m = _model(tmp_path, exts=[".PNG"])
        assert m.rowCount() == 1
        m.set_filter([".PNG"])
        assert m.rowCount() == 1

    def test_refresh_picks_up_new_files(self, qtbot, tmp_path):
        m = _model(tmp_path)
        assert m.rowCount() == 0
        (tmp_path / "new.yaml").write_text("{}")
        m.refresh()
        assert m.rowCount() == 1

    def test_refresh_removes_deleted_files(self, qtbot, tmp_path):
        p = tmp_path / "scene.yaml"
        p.write_text("{}")
        m = _model(tmp_path)
        assert m.rowCount() == 1
        p.unlink()
        m.refresh()
        assert m.rowCount() == 0

    def test_empty_filter_shows_no_files(self, qtbot, tmp_path):
        (tmp_path / "scene.yaml").write_text("{}")
        m = _model(tmp_path, exts=[])
        assert m.rowCount() == 0


# ──────────────────────────────────────────────────────────────────────────────
# FileTreeModel — parent/index navigation
# ──────────────────────────────────────────────────────────────────────────────


class TestFileTreeModelNavigation:
    def test_invalid_index_returns_invalid_parent(self, qtbot, tmp_path):
        m = _model(tmp_path)
        parent = m.parent(QModelIndex())
        assert not parent.isValid()

    def test_top_level_item_parent_is_invalid(self, qtbot, tmp_path):
        (tmp_path / "scene.yaml").write_text("{}")
        m = _model(tmp_path)
        idx = m.index(0, 0)
        assert not m.parent(idx).isValid()

    def test_nested_item_parent_is_dir(self, qtbot, tmp_path):
        subdir = tmp_path / "meshes"
        subdir.mkdir()
        (subdir / "hero.yaml").write_text("{}")
        m = _model(tmp_path)
        dir_idx = m.index(0, 0)
        # Force-load the subdir
        dir_node: FileTreeNode = dir_idx.internalPointer()
        dir_node.loaded = False
        dir_node.children.clear()
        m.fetchMore(dir_idx)
        child_idx = m.index(0, 0, dir_idx)
        parent_idx = m.parent(child_idx)
        assert parent_idx.isValid()
        parent_node: FileTreeNode = parent_idx.internalPointer()
        assert parent_node.is_dir

    def test_out_of_range_index_is_invalid(self, qtbot, tmp_path):
        m = _model(tmp_path)
        idx = m.index(99, 0)
        assert not idx.isValid()


# ──────────────────────────────────────────────────────────────────────────────
# FileTreeView — signal wiring
# ──────────────────────────────────────────────────────────────────────────────


class TestFileTreeViewSignals:
    def test_file_selected_emitted_on_file_click(self, qtbot, tmp_path):
        (tmp_path / "scene.yaml").write_text("{}")
        view = FileTreeView(tmp_path, [".yaml"])
        qtbot.addWidget(view)

        received = []
        view.file_selected.connect(lambda p, versions: received.append(p))
        # Simulate selection via the selection model
        idx = view.tree_model.index(0, 0)
        view.selectionModel().select(idx, view.selectionModel().SelectionFlag.Select)
        assert received, "file_selected signal not emitted"
        assert received[0].name == "scene.yaml"

    def test_no_signal_on_dir_selection(self, qtbot, tmp_path):
        (tmp_path / "models").mkdir()
        view = FileTreeView(tmp_path, [".yaml"])
        qtbot.addWidget(view)

        received = []
        view.file_selected.connect(lambda p, v: received.append(p))
        idx = view.tree_model.index(0, 0)
        view.selectionModel().select(idx, view.selectionModel().SelectionFlag.Select)
        assert received == [], "file_selected should not emit for directories"

    def test_tree_model_property(self, qtbot, tmp_path):
        view = FileTreeView(tmp_path, [".blend"])
        qtbot.addWidget(view)
        assert isinstance(view.tree_model, FileTreeModel)

    def test_set_filter_delegates_to_model(self, qtbot, tmp_path):
        (tmp_path / "a.yaml").write_text("{}")
        (tmp_path / "b.blend").write_bytes(b"")
        view = FileTreeView(tmp_path, [".yaml", ".blend"])
        qtbot.addWidget(view)
        assert view.tree_model.rowCount() == 2
        view.set_filter([".blend"])
        assert view.tree_model.rowCount() == 1
