"""Application-level state."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path

from unityaml.project import ProjectConfig

DEFAULT_FILTER = [".blend", ".yaml", ".json", ".png", ".jpg", ".jpeg"]


@dataclass
class AppState:
    """Top-level application state."""

    asset_root: Path
    file_filter: list[str] = field(default_factory=lambda: list(DEFAULT_FILTER))
    projects: list[ProjectConfig] = field(default_factory=list)
    active_project: str | None = None

    def reload_projects(self) -> None:
        from unityaml.persistence import load_all_projects

        self.projects = load_all_projects()

    def get_project(self, name: str) -> ProjectConfig | None:
        for p in self.projects:
            if p.name == name:
                return p
        return None

    def add_project(self, project: ProjectConfig) -> None:
        self.projects.append(project)
        project.save()

    def remove_project(self, name: str) -> None:
        project = self.get_project(name)
        if project:
            from unityaml.persistence import delete_project

            delete_project(project)
            self.projects = [p for p in self.projects if p.name != name]
            if self.active_project == name:
                self.active_project = None


def create_app_state(asset_root: Path | None = None) -> AppState:
    """Create and populate the initial AppState."""
    root = asset_root or Path.cwd()
    state = AppState(asset_root=root)
    state.reload_projects()
    return state
