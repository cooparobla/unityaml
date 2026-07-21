"""Handler for .yaml files."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from unityaml.base import AssetType, BaseFileHandler, BaseProperties
from unityaml.versioning import resolve_versions

# Keys written by blender_export that identify a scene-export YAML
_SCENE_EXPORT_KEYS = {"format", "mesh", "scene", "animations"}


@dataclass
class YamlProperties(BaseProperties):
    """Properties specific to .yaml files."""

    asset_type: AssetType = field(default=AssetType.YAML, init=False)
    top_level_keys: list[str] = field(default_factory=list)
    is_scene_export: bool = False
    is_config: bool = False
    line_count: int = 0


class YamlFileHandler(BaseFileHandler):
    """Handles .yaml files — parsing and key inspection."""

    def load(self, path: Path) -> YamlProperties:
        path = path.resolve()
        stat = path.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime)
        versions = resolve_versions(path)

        top_level_keys: list[str] = []
        is_scene_export = False
        line_count = 0

        try:
            text = path.read_text(encoding="utf-8", errors="replace")
            line_count = text.count("\n")
            import yaml  # PyYAML

            doc = yaml.safe_load(text)
            if isinstance(doc, dict):
                top_level_keys = list(doc.keys())
                is_scene_export = bool(_SCENE_EXPORT_KEYS & set(top_level_keys))
        except Exception:
            pass

        is_config = not is_scene_export and bool(top_level_keys)

        return YamlProperties(
            path=path,
            versions=versions,
            projects=[],
            last_modified=last_modified,
            top_level_keys=top_level_keys,
            is_scene_export=is_scene_export,
            is_config=is_config,
            line_count=line_count,
        )

    def read_content(self, props: YamlProperties) -> str:
        """Return the raw text content of the file."""
        try:
            return props.path.read_text(encoding="utf-8", errors="replace")
        except OSError:
            return ""
