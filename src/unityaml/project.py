"""Project model — ProjectConfig, AssetRef, and related types."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path

from unityaml.base import AssetType, FileVersion


@dataclass
class AssetRef:
    """A reference from a project to an asset file."""

    path: Path
    asset_type: AssetType
    pinned_version: FileVersion | None = None  # None = always use latest

    @property
    def display_name(self) -> str:
        if self.pinned_version and self.pinned_version.label:
            return f"{self.path.name} ({self.pinned_version.label})"
        return self.path.name


@dataclass
class ProjectConfig:
    """Serialized to ~/.unityaml/projects/<name>/project.yaml."""

    name: str
    created: datetime
    config_files: list[Path] = field(default_factory=list)
    asset_refs: list[AssetRef] = field(default_factory=list)
    export_dir: Path | None = None

    @property
    def project_dir(self) -> Path:
        from unityaml.persistence import projects_root

        return projects_root() / self.name.lower().replace(" ", "_")

    @property
    def project_yaml_path(self) -> Path:
        return self.project_dir / "project.yaml"

    def save(self) -> None:
        from unityaml.persistence import save_project

        save_project(self)

    def add_asset_ref(self, path: Path, asset_type: AssetType) -> None:
        """Add an asset reference if not already present."""
        canonical = path.resolve()
        for ref in self.asset_refs:
            if ref.path.resolve() == canonical:
                return
        self.asset_refs.append(AssetRef(path=path, asset_type=asset_type))
        self.save()

    def remove_asset_ref(self, path: Path) -> None:
        canonical = path.resolve()
        self.asset_refs = [r for r in self.asset_refs if r.path.resolve() != canonical]
        self.save()

    def add_config_file(self, path: Path) -> None:
        canonical = path.resolve()
        for cfg in self.config_files:
            if cfg.resolve() == canonical:
                return
        self.config_files.append(path)
        self.save()

    def remove_config_file(self, path: Path) -> None:
        canonical = path.resolve()
        self.config_files = [c for c in self.config_files if c.resolve() != canonical]
        self.save()
