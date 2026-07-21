"""Persistence helpers — reading and writing YAML for projects and settings.

Writing uses blender_export.yaml_dump (no PyYAML dependency for output).
Reading uses PyYAML safe_load.
"""

from __future__ import annotations

from datetime import datetime
from pathlib import Path
from typing import Any

import yaml  # PyYAML — for reading


# ---------------------------------------------------------------------------
# Filesystem layout
# ---------------------------------------------------------------------------

def unityaml_root() -> Path:
    """~/.unityaml — user-level data directory."""
    root = Path.home() / ".unityaml"
    root.mkdir(parents=True, exist_ok=True)
    return root


def projects_root() -> Path:
    root = unityaml_root() / "projects"
    root.mkdir(parents=True, exist_ok=True)
    return root


def settings_path() -> Path:
    return unityaml_root() / "settings.yaml"


# ---------------------------------------------------------------------------
# Low-level YAML I/O
# ---------------------------------------------------------------------------

def load_yaml(path: Path) -> dict:
    """Load a YAML file and return a dict (empty dict on error)."""
    if not path.exists():
        return {}
    try:
        text = path.read_text(encoding="utf-8")
        doc = yaml.safe_load(text)
        return doc if isinstance(doc, dict) else {}
    except Exception:
        return {}


def dump_yaml(data: dict, path: Path) -> None:
    """Write a dict to YAML using blender_export.yaml_dump."""
    from blender_export.yaml_dump import manual_yaml_dump

    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(manual_yaml_dump(data)) + "\n", encoding="utf-8")


# ---------------------------------------------------------------------------
# Project serialization
# ---------------------------------------------------------------------------

def save_project(project: "ProjectConfig") -> None:  # noqa: F821
    from unityaml.project import AssetRef

    data: dict[str, Any] = {
        "name": project.name,
        "created": project.created.isoformat(),
        "config_files": [str(p) for p in project.config_files],
        "asset_refs": [
            {
                "path": str(ref.path),
                "asset_type": ref.asset_type.value,
                "pinned_version": (
                    {"major": ref.pinned_version.major, "minor": ref.pinned_version.minor}
                    if ref.pinned_version
                    else None
                ),
            }
            for ref in project.asset_refs
        ],
        "export_dir": str(project.export_dir) if project.export_dir else "",
    }
    dump_yaml(data, project.project_yaml_path)


def load_project(project_yaml: Path) -> "ProjectConfig":  # noqa: F821
    from unityaml.base import AssetType, FileVersion
    from unityaml.project import AssetRef, ProjectConfig

    data = load_yaml(project_yaml)
    name = data.get("name", project_yaml.parent.name)
    created_str = data.get("created", "")
    try:
        created = datetime.fromisoformat(created_str)
    except (ValueError, TypeError):
        created = datetime.now()

    config_files = [Path(p) for p in data.get("config_files", [])]

    asset_refs = []
    for ref_data in data.get("asset_refs", []):
        try:
            asset_type = AssetType(ref_data.get("asset_type", "unknown"))
        except ValueError:
            asset_type = AssetType.UNKNOWN
        pv_data = ref_data.get("pinned_version")
        pinned_version = None
        if pv_data and isinstance(pv_data, dict):
            pinned_version = FileVersion(
                path=Path(ref_data["path"]),
                major=pv_data.get("major", 0),
                minor=pv_data.get("minor", 0),
            )
        asset_refs.append(
            AssetRef(
                path=Path(ref_data["path"]),
                asset_type=asset_type,
                pinned_version=pinned_version,
            )
        )

    export_dir_str = data.get("export_dir", "")
    export_dir = Path(export_dir_str) if export_dir_str and export_dir_str != "None" else None

    return ProjectConfig(
        name=name,
        created=created,
        config_files=config_files,
        asset_refs=asset_refs,
        export_dir=export_dir,
    )


def load_all_projects() -> list["ProjectConfig"]:  # noqa: F821
    """Load all projects from ~/.unityaml/projects/."""
    root = projects_root()
    if not root.exists():
        return []
    projects = []
    for subdir in sorted(root.iterdir()):
        if subdir.is_dir():
            yaml_file = subdir / "project.yaml"
            if yaml_file.exists():
                try:
                    projects.append(load_project(yaml_file))
                except Exception:
                    pass
    return projects


def delete_project(project: "ProjectConfig") -> None:  # noqa: F821
    """Remove the project directory from disk."""
    import shutil

    if project.project_dir.exists():
        shutil.rmtree(project.project_dir)
