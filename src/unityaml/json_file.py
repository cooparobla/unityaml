"""Handler for .json files."""

from __future__ import annotations

import json
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from unityaml.base import AssetType, BaseFileHandler, BaseProperties
from unityaml.versioning import resolve_versions


@dataclass
class JsonProperties(BaseProperties):
    """Properties specific to .json files."""

    asset_type: AssetType = field(default=AssetType.JSON, init=False)
    top_level_keys: list[str] = field(default_factory=list)
    file_size_bytes: int = 0


class JsonFileHandler(BaseFileHandler):
    """Handles .json files — parsing and key inspection."""

    def load(self, path: Path) -> JsonProperties:
        path = path.resolve()
        stat = path.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime)
        versions = resolve_versions(path)

        top_level_keys: list[str] = []
        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            doc = json.loads(text)
            if isinstance(doc, dict):
                top_level_keys = list(doc.keys())
        except Exception:
            pass

        return JsonProperties(
            path=path,
            versions=versions,
            projects=[],
            last_modified=last_modified,
            top_level_keys=top_level_keys,
            file_size_bytes=stat.st_size,
        )

    def read_content(self, props: JsonProperties) -> str:
        """Return the raw text content of the file (pretty-printed if valid JSON)."""
        try:
            text = props.path.read_text(encoding="utf-8", errors="replace")
            # Try to re-format for readability
            doc = json.loads(text)
            return json.dumps(doc, indent=2, ensure_ascii=False)
        except Exception:
            try:
                return props.path.read_text(encoding="utf-8", errors="replace")
            except OSError:
                return ""
