"""Version parsing, grouping, and resolution utilities.

Implements the versioning convention: <name>.v<major>.<minor>.<ext>

Examples:
  character.v1.0.blend + character.v2.3.blend → grouped under "character.blend"
  scene.yaml                                  → unversioned
"""

from __future__ import annotations

import re
from pathlib import Path

from unityaml.base import FileVersion

# Matches stems like "character.v2.3" — captures (name, major, minor)
_VERSION_RE = re.compile(r"^(.+)\.v(\d+)\.(\d+)$")


def parse_version(path: Path) -> tuple[str, FileVersion | None]:
    """Parse a file path into (canonical_name, FileVersion or None).

    Returns the canonical name (without version suffix) and the parsed
    FileVersion, or None if the file has no version suffix.

    Examples:
        parse_version(Path("character.v2.3.blend"))
          → ("character", FileVersion(path=..., major=2, minor=3))
        parse_version(Path("scene.yaml"))
          → ("scene", None)
    """
    m = _VERSION_RE.match(path.stem)
    if m:
        name, major, minor = m.group(1), int(m.group(2)), int(m.group(3))
        return name, FileVersion(path=path, major=major, minor=minor)
    return path.stem, None


def resolve_versions(path: Path) -> list[FileVersion]:
    """Scan sibling files for all version variants of the given file.

    Includes the file itself. If there are no version-tagged siblings,
    returns a single unversioned FileVersion for the file.
    """
    canonical_name, _ = parse_version(path)
    ext = path.suffix
    parent = path.parent

    versions: list[FileVersion] = []
    for sibling in parent.iterdir():
        if sibling.suffix != ext:
            continue
        sib_name, sib_ver = parse_version(sibling)
        if sib_name == canonical_name:
            if sib_ver is not None:
                versions.append(sib_ver)
            else:
                # Unversioned file matches canonical name — add as v0.0
                versions.append(FileVersion(path=sibling, major=0, minor=0))

    if not versions:
        # Fallback: just the file itself
        versions = [FileVersion(path=path, major=0, minor=0)]

    return sorted(versions)


def canonical_stem(path: Path) -> str:
    """Return the stem without version suffix.

    character.v2.3.blend → "character"
    scene.yaml           → "scene"
    """
    name, _ = parse_version(path)
    return name


def group_versioned_files(paths: list[Path]) -> dict[str, list[FileVersion]]:
    """Group a flat list of file paths by canonical name.

    Returns a dict mapping canonical_name → sorted list of FileVersions.
    Files with the same extension and same canonical name are grouped together.

    Example:
        [char.v1.0.blend, char.v2.3.blend, scene.yaml]
        → {
            "char.blend": [FileVersion(v1.0), FileVersion(v2.3)],
            "scene.yaml": [FileVersion(v0.0)],
          }
    """
    groups: dict[str, list[FileVersion]] = {}
    for p in paths:
        name, ver = parse_version(p)
        key = f"{name}{p.suffix}"
        if key not in groups:
            groups[key] = []
        if ver is not None:
            groups[key].append(ver)
        else:
            groups[key].append(FileVersion(path=p, major=0, minor=0))

    # Sort each group
    for key in groups:
        groups[key].sort()

    return groups


def highest_version(versions: list[FileVersion]) -> FileVersion:
    """Return the highest version from a list."""
    return max(versions)
