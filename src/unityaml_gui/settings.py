"""Settings persistence — window geometry, splitter positions, active tab.

Stored as ~/.unityaml/settings.yaml.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from unityaml.persistence import load_yaml, dump_yaml


def _settings_path() -> Path:
    root = Path.home() / ".unityaml"
    root.mkdir(parents=True, exist_ok=True)
    return root / "settings.yaml"


class AppSettings:
    """Thin wrapper around ~/.unityaml/settings.yaml."""

    def __init__(self) -> None:
        self._path = _settings_path()
        self._data: dict[str, Any] = load_yaml(self._path)

    def get(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def set(self, key: str, value: Any) -> None:
        self._data[key] = value

    def save(self) -> None:
        dump_yaml(self._data, self._path)
