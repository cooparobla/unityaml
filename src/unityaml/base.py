"""Base types shared across all file handlers.

Defines the core dataclasses (AssetType, FileVersion, BaseProperties) and the
abstract base class (BaseFileHandler) that all file-type handlers inherit from.
No Qt or third-party imports — stdlib only.
"""

from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from unityaml.project import ProjectConfig


class AssetType(Enum):
    BLEND = "blend"
    IMAGE = "image"
    YAML = "yaml"
    JSON = "json"
    UNKNOWN = "unknown"


@dataclass
class FileVersion:
    """A single version of a file on disk.

    Example: /assets/char.v2.3.blend → path=..., major=2, minor=3
    An unversioned file gets major=0, minor=0.
    """

    path: Path
    major: int = 0
    minor: int = 0

    @property
    def label(self) -> str:
        if self.major == 0 and self.minor == 0:
            return ""
        return f"v{self.major}.{self.minor}"

    def __lt__(self, other: "FileVersion") -> bool:
        return (self.major, self.minor) < (other.major, other.minor)

    def __le__(self, other: "FileVersion") -> bool:
        return (self.major, self.minor) <= (other.major, other.minor)

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, FileVersion):
            return NotImplemented
        return (self.major, self.minor) == (other.major, other.minor)

    def __hash__(self) -> int:
        return hash((self.major, self.minor, str(self.path)))


@dataclass
class BaseProperties:
    """Properties shared by all file types."""

    path: Path
    asset_type: AssetType
    versions: list[FileVersion] = field(default_factory=list)
    active_version: FileVersion | None = None
    projects: list[str] = field(default_factory=list)
    last_modified: datetime = field(default_factory=datetime.now)

    @property
    def is_versioned(self) -> bool:
        return len(self.versions) > 1

    @property
    def display_name(self) -> str:
        """Human-readable name shown in the tree view."""
        if self.active_version and self.active_version.label:
            stem = _canonical_stem(self.path)
            return f"{stem}{self.path.suffix} ({self.active_version.label})"
        return self.path.name

    def __post_init__(self) -> None:
        if self.active_version is None and self.versions:
            self.active_version = max(self.versions)


def _canonical_stem(path: Path) -> str:
    """Return the stem without any version suffix.

    character.v2.3.blend → character
    scene.yaml            → scene
    """
    import re

    m = re.match(r"^(.+)\.v\d+\.\d+$", path.stem)
    return m.group(1) if m else path.stem


class BaseFileHandler(ABC):
    """Abstract base class for all file-type handlers."""

    @abstractmethod
    def load(self, path: Path) -> BaseProperties:
        """Read the file and return a populated properties dataclass."""
        ...

    def resolve_versions(self, path: Path) -> list[FileVersion]:
        """Scan siblings for version variants of this file.

        e.g. char.v1.0.blend, char.v2.3.blend → [FileVersion(v1.0), FileVersion(v2.3)]
        """
        from unityaml.versioning import resolve_versions

        return resolve_versions(path)

    def get_projects(
        self, path: Path, all_projects: list["ProjectConfig"]
    ) -> list[str]:
        """Return names of projects that reference this file."""
        result = []
        canonical = path.resolve()
        for proj in all_projects:
            for ref in proj.asset_refs:
                if ref.path.resolve() == canonical:
                    result.append(proj.name)
                    break
            for cfg in proj.config_files:
                if cfg.resolve() == canonical:
                    result.append(proj.name)
                    break
        return list(dict.fromkeys(result))  # deduplicate, preserve order
