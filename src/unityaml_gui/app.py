"""Application stylesheet and QApplication wiring."""

from __future__ import annotations

from unityaml.app_state import AppState
from unityaml_gui.main_window import MainWindow

# Dark-mode palette with accent colour #5E6AD2 (indigo)
STYLESHEET = """
/* ── Global ──────────────────────────────────────────────────────────────── */
* {
    font-family: "Inter", "Segoe UI", "SF Pro Display", sans-serif;
    font-size: 13px;
    color: #E2E4F0;
}

QMainWindow, QDialog, QWidget {
    background: #13141A;
}

/* ── Tab Bar ──────────────────────────────────────────────────────────────── */
QTabBar::tab {
    background: #1C1D26;
    color: #8A8FA8;
    padding: 8px 22px;
    border: none;
    border-bottom: 2px solid transparent;
    min-width: 90px;
}
QTabBar::tab:selected {
    color: #E2E4F0;
    border-bottom: 2px solid #5E6AD2;
    background: #13141A;
}
QTabBar::tab:hover:!selected {
    color: #C4C8E0;
    background: #1E1F2B;
}
QTabWidget::pane {
    border: none;
    background: #13141A;
}

/* ── Toolbar ──────────────────────────────────────────────────────────────── */
QToolBar {
    background: #1C1D26;
    border-bottom: 1px solid #2A2B38;
    spacing: 6px;
    padding: 4px 8px;
}
QToolBar QToolButton {
    background: transparent;
    border: none;
    border-radius: 5px;
    padding: 5px 10px;
    color: #8A8FA8;
}
QToolBar QToolButton:hover {
    background: #2A2B3D;
    color: #E2E4F0;
}
QToolBar QToolButton:pressed {
    background: #3B3D54;
}

/* ── Status Bar ───────────────────────────────────────────────────────────── */
QStatusBar {
    background: #1C1D26;
    border-top: 1px solid #2A2B38;
    color: #6B7094;
    padding: 4px 12px;
    font-size: 12px;
}

/* ── Tree View ────────────────────────────────────────────────────────────── */
QTreeView {
    background: #13141A;
    alternate-background-color: #16171F;
    border: none;
    selection-background-color: #2A2B3D;
    selection-color: #E2E4F0;
    show-decoration-selected: 1;
    outline: none;
}
QTreeView::item {
    padding: 3px 4px;
    border-radius: 3px;
}
QTreeView::item:hover {
    background: #1E1F2B;
}
QTreeView::item:selected {
    background: #2A2B3D;
}
QTreeView::branch {
    background: #13141A;
}
QTreeView::branch:has-children:!has-siblings:closed,
QTreeView::branch:closed:has-children:has-siblings {
    image: url(none);  /* We use custom triangle indicators */
}

/* ── List View ────────────────────────────────────────────────────────────── */
QListView {
    background: #13141A;
    border: none;
    selection-background-color: #2A2B3D;
    selection-color: #E2E4F0;
    outline: none;
}
QListView::item {
    padding: 5px 8px;
    border-radius: 4px;
}
QListView::item:hover {
    background: #1E1F2B;
}
QListView::item:selected {
    background: #2A2B3D;
}

/* ── Scroll Bars ──────────────────────────────────────────────────────────── */
QScrollBar:vertical {
    background: #13141A;
    width: 8px;
    margin: 0;
}
QScrollBar::handle:vertical {
    background: #2E2F41;
    border-radius: 4px;
    min-height: 24px;
}
QScrollBar::handle:vertical:hover { background: #3E4058; }
QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical { height: 0; }
QScrollBar:horizontal {
    background: #13141A;
    height: 8px;
}
QScrollBar::handle:horizontal {
    background: #2E2F41;
    border-radius: 4px;
    min-width: 24px;
}
QScrollBar::handle:horizontal:hover { background: #3E4058; }
QScrollBar::add-line:horizontal, QScrollBar::sub-line:horizontal { width: 0; }

/* ── Splitter ─────────────────────────────────────────────────────────────── */
QSplitter::handle {
    background: #2A2B38;
}
QSplitter::handle:horizontal { width: 1px; }
QSplitter::handle:vertical   { height: 1px; }

/* ── Buttons ──────────────────────────────────────────────────────────────── */
QPushButton {
    background: #2A2B3D;
    color: #C4C8E0;
    border: 1px solid #3B3D54;
    border-radius: 6px;
    padding: 6px 14px;
    font-weight: 500;
}
QPushButton:hover {
    background: #353650;
    color: #E2E4F0;
    border-color: #5E6AD2;
}
QPushButton:pressed {
    background: #2A2B3D;
}
QPushButton[accent="true"] {
    background: #5E6AD2;
    color: #FFFFFF;
    border-color: #5E6AD2;
}
QPushButton[accent="true"]:hover {
    background: #6E7AE2;
}
QPushButton[danger="true"] {
    background: #3D2020;
    color: #E07070;
    border-color: #5A2828;
}
QPushButton[danger="true"]:hover {
    background: #4D2828;
    color: #F08080;
}

/* ── Line Edit / Combo Box ────────────────────────────────────────────────── */
QLineEdit {
    background: #1C1D26;
    border: 1px solid #2E2F41;
    border-radius: 5px;
    padding: 5px 8px;
    color: #E2E4F0;
    selection-background-color: #5E6AD2;
}
QLineEdit:focus {
    border-color: #5E6AD2;
}
QComboBox {
    background: #1C1D26;
    border: 1px solid #2E2F41;
    border-radius: 5px;
    padding: 5px 8px;
    color: #E2E4F0;
    min-width: 80px;
}
QComboBox:hover { border-color: #5E6AD2; }
QComboBox::drop-down { border: none; width: 20px; }
QComboBox QAbstractItemView {
    background: #1E1F2B;
    border: 1px solid #3B3D54;
    selection-background-color: #2A2B3D;
}

/* ── Labels ───────────────────────────────────────────────────────────────── */
QLabel[heading="true"] {
    font-size: 15px;
    font-weight: 600;
    color: #E2E4F0;
}
QLabel[subheading="true"] {
    font-size: 11px;
    font-weight: 500;
    color: #6B7094;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}
QLabel[tag="true"] {
    background: #2A2B3D;
    color: #9AA0C0;
    border-radius: 3px;
    padding: 1px 5px;
    font-size: 11px;
}
QLabel[warning="true"] {
    color: #E8A84C;
}
QLabel[ok="true"] {
    color: #5DBE7A;
}
QLabel[error="true"] {
    color: #E06060;
}

/* ── Group / Frame ────────────────────────────────────────────────────────── */
QGroupBox {
    border: 1px solid #2A2B38;
    border-radius: 8px;
    margin-top: 14px;
    padding-top: 6px;
}
QGroupBox::title {
    color: #6B7094;
    subcontrol-origin: margin;
    left: 10px;
    top: 2px;
    font-size: 11px;
    font-weight: 600;
    text-transform: uppercase;
    letter-spacing: 0.5px;
}

/* ── Text Edit ────────────────────────────────────────────────────────────── */
QTextEdit, QPlainTextEdit {
    background: #0F1016;
    border: 1px solid #2A2B38;
    border-radius: 5px;
    color: #C4C8E0;
    font-family: "JetBrains Mono", "Fira Code", "Cascadia Code", monospace;
    font-size: 12px;
    selection-background-color: #3B3D54;
    padding: 6px;
}

/* ── Progress Bar ─────────────────────────────────────────────────────────── */
QProgressBar {
    background: #1C1D26;
    border: 1px solid #2A2B38;
    border-radius: 4px;
    height: 6px;
    text-align: center;
    color: transparent;
}
QProgressBar::chunk {
    background: #5E6AD2;
    border-radius: 4px;
}

/* ── Menu ─────────────────────────────────────────────────────────────────── */
QMenu {
    background: #1E1F2B;
    border: 1px solid #3B3D54;
    border-radius: 6px;
    padding: 4px;
}
QMenu::item {
    padding: 6px 20px;
    border-radius: 4px;
}
QMenu::item:selected {
    background: #2A2B3D;
}
QMenu::separator {
    height: 1px;
    background: #2A2B38;
    margin: 4px 0;
}

/* ── Check Box ────────────────────────────────────────────────────────────── */
QCheckBox {
    spacing: 6px;
    color: #C4C8E0;
}
QCheckBox::indicator {
    width: 14px;
    height: 14px;
    border: 1px solid #3B3D54;
    border-radius: 3px;
    background: #1C1D26;
}
QCheckBox::indicator:checked {
    background: #5E6AD2;
    border-color: #5E6AD2;
}
"""


class UnityYamlApp(MainWindow):
    """Main application window — applies stylesheet and wires AppState."""

    def __init__(self, state: AppState) -> None:
        super().__init__(state)
        self._apply_stylesheet()

    def _apply_stylesheet(self) -> None:
        from PySide6.QtWidgets import QApplication

        QApplication.instance().setStyleSheet(STYLESHEET)
