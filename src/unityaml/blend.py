"""Handler for .blend files.

Extracts metadata from Blender files and exposes export functionality.
Heavy Blender introspection (object list, mesh count, armature) is read from
a sidecar meta-file (<name>.blend.meta.yaml) if present — this avoids
launching Blender just to display the file tree.  The sidecar is written
automatically after each export.
"""

from __future__ import annotations

import os
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from unityaml.base import AssetType, BaseFileHandler, BaseProperties, FileVersion
from unityaml.versioning import resolve_versions


@dataclass
class BlenderProperties(BaseProperties):
    """Properties specific to .blend files."""

    asset_type: AssetType = field(default=AssetType.BLEND, init=False)
    object_names: list[str] = field(default_factory=list)
    mesh_count: int = 0
    has_armature: bool = False
    has_animations: bool = False
    last_exported: datetime | None = None
    export_path: Path | None = None
    stale: bool = False

    def __post_init__(self) -> None:
        super().__post_init__()
        # Compute stale status when we have enough info
        if self.last_exported and self.export_path:
            self.stale = self.last_modified > self.last_exported


class BlenderFileHandler(BaseFileHandler):
    """Handles .blend files — metadata extraction and export triggering."""

    def load(self, path: Path) -> BlenderProperties:
        """Read a .blend file and return populated BlenderProperties.

        Metadata is loaded from an optional sidecar YAML file
        (<stem>.blend.meta.yaml) written by a previous export.
        """
        path = path.resolve()
        stat = path.stat()
        last_modified = datetime.fromtimestamp(stat.st_mtime)
        versions = resolve_versions(path)

        # Attempt to load sidecar
        meta = _load_sidecar(path)

        # Pull fields from sidecar if available
        object_names: list[str] = meta.get("objects", [])
        mesh_count: int = meta.get("mesh_count", 0)
        has_armature: bool = meta.get("has_armature", False)
        has_animations: bool = meta.get("has_animations", False)
        last_exported: datetime | None = None
        export_path: Path | None = None

        if "last_exported" in meta:
            try:
                last_exported = datetime.fromisoformat(meta["last_exported"])
            except (ValueError, TypeError):
                pass
        if "export_path" in meta and meta["export_path"]:
            export_path = Path(meta["export_path"])

        props = BlenderProperties(
            path=path,
            versions=versions,
            projects=[],
            last_modified=last_modified,
            object_names=object_names,
            mesh_count=mesh_count,
            has_armature=has_armature,
            has_animations=has_animations,
            last_exported=last_exported,
            export_path=export_path,
        )
        props.stale = self.check_stale(props)
        return props

    def check_stale(self, props: BlenderProperties) -> bool:
        """Return True if the source .blend is newer than the last export."""
        if props.last_exported is None or props.export_path is None:
            return False
        if not props.export_path.exists():
            return True
        export_mtime = datetime.fromtimestamp(props.export_path.stat().st_mtime)
        return props.last_modified > export_mtime

    def export_to_yaml(
        self,
        props: BlenderProperties,
        output: Path,
        *,
        blender: str | None = None,
    ) -> None:
        """Headlessly export the .blend file to YAML via blender_export.

        Also writes a sidecar .meta.yaml alongside the .blend for fast future
        metadata reads.
        """
        from blender_export.api import export_blend, extract_blend_data

        data = extract_blend_data(str(props.path), blender=blender)
        from blender_export.yaml_dump import manual_yaml_dump

        yaml_text = "\n".join(manual_yaml_dump(data)) + "\n"
        output.parent.mkdir(parents=True, exist_ok=True)
        output.write_text(yaml_text)

        # Update props
        now = datetime.now()
        props.last_exported = now
        props.export_path = output

        # Extract objects / meshes / armature from the exported data
        scene = data.get("scene", {})
        mesh_data = data.get("mesh", {})
        props.object_names = list(scene.get("objects", {}).keys())
        props.mesh_count = len(mesh_data) if isinstance(mesh_data, dict) else 0
        props.has_armature = any(
            o.get("type") == "ARMATURE"
            for o in scene.get("objects", {}).values()
            if isinstance(o, dict)
        )
        props.has_animations = bool(data.get("animations"))
        props.stale = False

        # Write sidecar
        _write_sidecar(props)


# ---------------------------------------------------------------------------
# Sidecar helpers
# ---------------------------------------------------------------------------

def _sidecar_path(blend_path: Path) -> Path:
    return blend_path.with_suffix(".blend.meta.yaml")


def _load_sidecar(blend_path: Path) -> dict:
    sidecar = _sidecar_path(blend_path)
    if not sidecar.exists():
        return {}
    try:
        import yaml  # PyYAML

        return yaml.safe_load(sidecar.read_text()) or {}
    except Exception:
        return {}


def _write_sidecar(props: BlenderProperties) -> None:
    sidecar = _sidecar_path(props.path)
    data = {
        "objects": props.object_names,
        "mesh_count": props.mesh_count,
        "has_armature": props.has_armature,
        "has_animations": props.has_animations,
        "last_exported": props.last_exported.isoformat() if props.last_exported else None,
        "export_path": str(props.export_path) if props.export_path else "",
    }
    from blender_export.yaml_dump import manual_yaml_dump

    sidecar.write_text("\n".join(manual_yaml_dump(data)) + "\n")
