"""Entry point: uv run unityaml-gui [<directory>]"""

from __future__ import annotations

import sys
from pathlib import Path


def main() -> None:
    import argparse

    parser = argparse.ArgumentParser(
        description="Unity YAML — asset management GUI"
    )
    parser.add_argument(
        "directory",
        nargs="?",
        default=None,
        help="Root directory to browse (defaults to cwd)",
    )
    args = parser.parse_args()

    asset_root = Path(args.directory).resolve() if args.directory else Path.cwd()

    from PySide6.QtWidgets import QApplication

    from unityaml.app_state import create_app_state
    from unityaml_gui.app import UnityYamlApp

    qt_app = QApplication(sys.argv)
    qt_app.setApplicationName("UnityYAML")
    qt_app.setOrganizationName("unityaml")

    state = create_app_state(asset_root)
    window = UnityYamlApp(state)
    window.show()

    sys.exit(qt_app.exec())


if __name__ == "__main__":
    main()
