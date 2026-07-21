# Plan: PySide File Explorer UI

## Goal

Build a PySide6 application with two main tabs — **Assets** and **Projects** — that serves as the primary interface for constructing Unity projects from Blender exports, supplementary YAML configs, and image assets. Never touch the Unity editor UI beyond build settings and scene management.

## Architecture

### Main Window Layout

```
┌──────────────────────────────────────────────────────────┐
│  [Assets]  [Projects]                          toolbar   │
├──────────────────────────────────────────────────────────┤
│                                                          │
│              (tab content — see below)                   │
│                                                          │
├──────────────────────────────────────────────────────────┤
│  Status / Log Bar                                        │
└──────────────────────────────────────────────────────────┘
```

### Assets Tab

Browse the filesystem, preview files, and trigger Blender exports. The tree starts **fully collapsed** — child items are only loaded when the user expands a directory (lazy loading).

```
┌──────────────────────────────────────────────────────────────────┐
│  [Filter: .blend .yaml .json .png]  [⟳ Refresh]                 │
├─────────────────────────┬────────────────────────────────────────┤
│  Tree View              │  Detail / Preview Panel                │
│                         │                                        │
│  ▸ 📁 assets/           │  ┌────────────────────────────────┐    │
│  ▾ 📁 models/           │  │  BlenderProperties             │    │
│    ▾ 📁 characters/     │  │                                │    │
│      ▸ 📁 animations/   │  │  File: character.blend (v2.3)  │    │
│        📦 character.blend│  │  Objects: Body, Armature       │    │
│        📦 weapon.blend   │  │  Meshes: 3                     │    │
│    ▸ 📁 environment/    │  │  Has Armature: ✓               │    │
│  ▾ 📁 config/           │  │  Animations: 4 clips           │    │
│      📄 scene.yaml      │  │  Exported: 2026-07-18 14:30    │    │
│      📄 materials.yaml  │  │  Status: ⚠ Stale               │    │
│  ▸ 📁 textures/         │  │                                │    │
│                         │  │  [Version: v2.3 ▾]             │    │
│                         │  │  Projects: MyGame, Demo        │    │
│                         │  └────────────────────────────────┘    │
│                         │                                        │
├─────────────────────────┴────────────────────────────────────────┤
│  Status / Log Bar                                                │
└──────────────────────────────────────────────────────────────────┘
```

**Tree behaviour:**
- `▸` = collapsed (children not yet loaded)
- `▾` = expanded (children loaded on demand)
- All nodes start collapsed; expanding a directory triggers a filesystem scan filtered to the active extensions
- Depth is reflected by indentation (2 spaces per level)
- Versioned files are grouped: `character.v1.0.blend` + `character.v2.3.blend` → single row `character.blend (v2.3)`

### Projects Tab

Manage saved projects and their asset assignments. A **project is a combination of YAML config files and references to assets** — it doesn't copy files, it points at them.

```
┌──────────────────────────────────────────────────┐
│  [+ New Project]  [Delete]                       │
├──────────────┬───────────────────────────────────┤
│  Project     │  Project Detail                   │
│  List        │                                   │
│              │  Name: MyGame                     │
│  ▸ MyGame    │  Path: ~/.unityaml/projects/mygame│
│  ▸ Prototype │  ───────────────────────────────  │
│  ▸ Demo      │  Config Files:                    │
│              │    📄 scene_layout.yaml           │
│              │    📄 materials.yaml              │
│              │  ───────────────────────────────  │
│              │  Asset References:                 │
│              │    📦 character.blend (v2.3)      │
│              │    📄 level1.yaml                 │
│              │    🖼 skin.png (v1.0)             │
│              │  ───────────────────────────────  │
│              │  [Export All]  [Open Folder]       │
└──────────────┴───────────────────────────────────┘
```

---

## Data Layer (Backend)

Strict separation: **dataclasses define all state**, UI reads from them. Each file type has its own handler class and properties dataclass.

### File Type Hierarchy

All file types inherit from a common base. Every file handler knows which projects reference it and supports the versioning convention.

```python
class AssetType(Enum):
    BLEND = "blend"
    IMAGE = "image"     # .png, .jpg, etc.
    YAML  = "yaml"
    JSON  = "json"

@dataclass
class FileVersion:
    """A single version of a file on disk."""
    path: Path              # e.g. /assets/char.v2.3.blend
    major: int              # 2
    minor: int              # 3

@dataclass
class BaseProperties:
    """Base properties shared by all file types."""
    path: Path                          # canonical path (highest version)
    asset_type: AssetType
    versions: list[FileVersion]         # all discovered versions, sorted
    active_version: FileVersion         # currently selected (defaults to highest)
    projects: list[str]                 # names of projects that reference this file
    last_modified: datetime

    @property
    def is_versioned(self) -> bool:
        return len(self.versions) > 1


@dataclass
class BlenderProperties(BaseProperties):
    """Properties specific to .blend files."""
    asset_type: AssetType = field(default=AssetType.BLEND, init=False)
    object_names: list[str] = field(default_factory=list)
    mesh_count: int = 0
    has_armature: bool = False
    has_animations: bool = False
    last_exported: datetime | None = None
    export_path: Path | None = None     # path to the exported .yaml
    stale: bool = False                 # source newer than export?


@dataclass
class ImageProperties(BaseProperties):
    """Properties specific to image files (.png, .jpg, etc.)."""
    asset_type: AssetType = field(default=AssetType.IMAGE, init=False)
    width: int = 0
    height: int = 0
    channels: int = 0                   # 3=RGB, 4=RGBA
    file_size_bytes: int = 0
    format: str = ""                    # "PNG", "JPEG", etc.


@dataclass
class YamlProperties(BaseProperties):
    """Properties specific to .yaml files."""
    asset_type: AssetType = field(default=AssetType.YAML, init=False)
    top_level_keys: list[str] = field(default_factory=list)
    is_scene_export: bool = False       # true if produced by blender_export
    is_config: bool = False             # true if hand-authored config
    line_count: int = 0


@dataclass
class JsonProperties(BaseProperties):
    """Properties specific to .json files."""
    asset_type: AssetType = field(default=AssetType.JSON, init=False)
    top_level_keys: list[str] = field(default_factory=list)
    file_size_bytes: int = 0
```

### File Handler Classes

Each file type has a handler that owns reading, writing, and populating its properties dataclass. All handlers inherit from `BaseFileHandler`.

```python
class BaseFileHandler:
    """Base class for all file type handlers."""

    def load(self, path: Path) -> BaseProperties:
        """Read the file and return a populated properties dataclass."""
        ...

    def resolve_versions(self, path: Path) -> list[FileVersion]:
        """Scan siblings for version variants of this file.
        e.g. char.v1.0.blend, char.v2.3.blend → [v1.0, v2.3]"""
        ...

    def get_projects(self, path: Path, all_projects: list[ProjectConfig]) -> list[str]:
        """Return names of projects that reference this file."""
        ...


class BlenderFileHandler(BaseFileHandler):
    """Handles .blend files — metadata extraction, export triggering."""

    def load(self, path: Path) -> BlenderProperties: ...
    def export_to_yaml(self, props: BlenderProperties, output: Path) -> None: ...
    def check_stale(self, props: BlenderProperties) -> bool: ...


class ImageFileHandler(BaseFileHandler):
    """Handles image files — reads dimensions, format, thumbnail."""

    def load(self, path: Path) -> ImageProperties: ...
    def generate_thumbnail(self, props: ImageProperties, size: tuple) -> QPixmap: ...


class YamlFileHandler(BaseFileHandler):
    """Handles .yaml files — parsing, key inspection."""

    def load(self, path: Path) -> YamlProperties: ...
    def read_content(self, props: YamlProperties) -> str: ...


class JsonFileHandler(BaseFileHandler):
    """Handles .json files — parsing, key inspection."""

    def load(self, path: Path) -> JsonProperties: ...
    def read_content(self, props: JsonProperties) -> str: ...
```

### Version Convention

Files follow the pattern `<name>.v<major>.<minor>.<ext>`:

| On disk | Parsed as |
|---------|-----------|
| `character.v1.0.blend` | name=`character`, version=1.0, ext=`.blend` |
| `character.v2.3.blend` | name=`character`, version=2.3, ext=`.blend` |
| `skin.v1.0.png` | name=`skin`, version=1.0, ext=`.png` |
| `scene.yaml` | name=`scene`, version=None (unversioned), ext=`.yaml` |

**Rules:**
- The tree view **groups versions** under the canonical name and **only shows the highest version**
- If a file has no `.v<N>.<M>` suffix, it's treated as unversioned (single version)
- The detail panel shows a **version dropdown** when `is_versioned` is true, letting the user switch which version they're inspecting
- Version parsing uses regex: `r'^(.+)\.v(\d+)\.(\d+)$'` applied to the stem (filename without final extension)

### Project Model

A project is fundamentally **a collection of YAML config files + references to assets**. It doesn't own or copy files — it points at them.

```python
@dataclass
class AssetRef:
    """A reference from a project to an asset file."""
    path: Path              # absolute path to the file (highest version)
    asset_type: AssetType
    pinned_version: FileVersion | None = None  # None = always use latest

@dataclass
class ProjectConfig:
    """Serialized to ~/.unityaml/projects/<name>/project.yaml."""
    name: str
    created: datetime
    config_files: list[Path]        # hand-authored .yaml configs
    asset_refs: list[AssetRef]      # references to .blend, .png, .yaml exports, etc.
    export_dir: Path | None = None  # where final assembled output goes

@dataclass
class AppState:
    """Top-level application state."""
    asset_root: Path                # cwd where the tool was launched
    file_filter: list[str]          # e.g. [".blend", ".yaml", ".json", ".png"]
    projects: list[ProjectConfig]   # loaded from ~/.unityaml/projects/
    active_project: str | None = None
```

### Persistence

- **Projects** saved as `.yaml` under `~/.unityaml/projects/<name>/project.yaml`
- **App preferences** (window geometry, filter, last active tab) saved to `~/.unityaml/settings.yaml`
- All serialization uses `yaml_dump.py` for writing and `PyYAML` for reading

### Directory Layout on Disk

```
~/.unityaml/
  settings.yaml
  projects/
    mygame/
      project.yaml          # ProjectConfig serialized
    prototype/
      project.yaml
```

---

## Phase 1 — Assets Tab (File Explorer Core)

### Tree View
- [ ] `QTreeView` backed by `QFileSystemModel` + custom proxy for version grouping
- [ ] Root at the directory where the tool is launched (`cwd`)
- [ ] **All nodes start collapsed** — no upfront directory traversal
- [ ] **Lazy loading** — children are only scanned/loaded when the user expands a node
- [ ] Configurable file extension filter (default: `.blend`, `.yaml`, `.json`, `.png`)
- [ ] Directories always visible; filtered files shown within them
- [ ] Indentation reflects depth (2 spaces per level)
- [ ] **Version grouping** — collapse `char.v1.0.blend` / `char.v2.3.blend` into a single `character.blend (v2.3)` row
- [ ] Expand/collapse with standard `▸` / `▾` tree affordances

### Toolbar / Filter Bar
- [ ] Text input to edit the extension filter list at runtime
- [ ] Refresh button to rescan the filesystem
- [ ] Toggle to show/hide hidden files

### Detail Panel (right side)
- [ ] **Dispatches to file-type-specific properties** via the handler classes
- [ ] `.blend` selected → `BlenderProperties` displayed (object names, mesh count, armature, export status)
- [ ] `.png` / `.jpg` selected → `ImageProperties` displayed (dimensions, format, thumbnail)
- [ ] `.yaml` selected → `YamlProperties` displayed (top-level keys, line count, syntax-highlighted preview)
- [ ] `.json` selected → `JsonProperties` displayed (top-level keys, size, syntax-highlighted preview)
- [ ] **Version dropdown** — shown when `is_versioned` is true; switching re-loads properties for that version
- [ ] **Project membership** — shows which projects reference this file

### Context Actions (right-click / toolbar)
- [ ] **Export .blend → .yaml** — invoke `blender_export` headlessly
- [ ] **Open in external editor** — launch system default editor
- [ ] **Add to project** — assign file to the currently active project

## Phase 2 — Projects Tab

### Project List (left side)
- [ ] `QListView` showing all projects from `~/.unityaml/projects/`
- [ ] Create / rename / delete projects
- [ ] Load `ProjectConfig` dataclass from `project.yaml` on selection

### Project Detail (right side)
- [ ] Show project name, creation date, export directory
- [ ] **Config files** section — list hand-authored `.yaml` configs
- [ ] **Asset references** section — list referenced assets with version and stale status
- [ ] Each asset reference shows its type icon and current version
- [ ] **Export All** button — batch-export all `.blend` assets, then assemble final `.yaml`
- [ ] **Open Folder** — open the project directory in the system file manager

### Data Flow
- [ ] Adding an asset in the Assets tab updates `ProjectConfig.asset_refs`
- [ ] Adding a config in the Assets tab updates `ProjectConfig.config_files`
- [ ] Changes auto-save to `project.yaml`
- [ ] Stale detection: compare `.blend` mtime vs `BlenderProperties.last_exported`
- [ ] `BaseProperties.projects` populated by scanning all `ProjectConfig.asset_refs`

## Phase 3 — Polish & Assembly

### Scene Assembly
- [ ] Combine multiple exported `.yaml` files and config overlays into a unified scene descriptor
- [ ] Preview the merged result in the detail panel

### Batch Operations
- [ ] Multi-select in Assets tab for bulk export
- [ ] Batch re-export all stale `.blend` files in a project

### UX
- [ ] Persist window geometry, splitter positions, active tab across sessions
- [ ] Keyboard shortcuts for common actions
- [ ] Progress dialog for long Blender exports

---

## Tech Stack

| Component | Choice | Rationale |
|-----------|--------|-----------|
| UI Framework | PySide6 | Qt — mature, cross-platform, native look |
| File Model | `QFileSystemModel` + custom proxy | Built-in FS watching + version grouping |
| Data Layer | Python `dataclasses` | Clean separation, easy serialization |
| Persistence | `.yaml` files | Human-readable, editable, consistent with project format |
| Blender Integration | `blender_export` module | Already built — headless subprocess |
| YAML Write | `yaml_dump.py` | Custom, no PyYAML dependency for output |
| YAML Read | `PyYAML` (or `ruamel.yaml`) | Need a parser for loading saved projects |
| Package Manager | `uv` | Fast, lockfile-based |

## Module Layout

```
src/
  blender_export/              # ✅ Done — headless export pipeline
  unityaml/                    # Core backend logic (NO Qt imports)
    __init__.py
    base.py                  # BaseProperties, BaseFileHandler, FileVersion
    blend.py                 # BlenderProperties, BlenderFileHandler
    image.py                 # ImageProperties, ImageFileHandler
    yaml_file.py             # YamlProperties, YamlFileHandler
    json_file.py             # JsonProperties, JsonFileHandler
    project.py               # ProjectConfig, AssetRef
    app_state.py             # AppState, load/save logic
    versioning.py            # Version parsing, grouping, resolution
    persistence.py           # YAML read/write helpers
  unityaml_gui/                # PySide6 GUI layer (depends on unityaml, not vice-versa)
    __init__.py
    __main__.py              # Entry-point: `uv run unityaml-gui`
    app.py                   # QApplication setup, load AppState
    main_window.py           # QMainWindow, tab bar, status bar
    views/                   # UI layer — reads from models
      assets_tab.py          # Assets tab: tree view + detail panel
      projects_tab.py        # Projects tab: project list + detail
      file_tree.py           # Filtered QTreeView + version-grouping proxy model
      detail_panel.py        # Right-side dispatcher → type-specific panels
      detail/                # Type-specific detail sub-panels
        blend_detail.py      # Renders BlenderProperties
        image_detail.py      # Renders ImageProperties
        yaml_detail.py       # Renders YamlProperties
        json_detail.py       # Renders JsonProperties
        version_selector.py  # Dropdown widget for version switching
      project_detail.py      # Right-side project info panel
    settings.py              # QSettings / settings.yaml persistence
```

## Scope

This repo is **Python only**. No C# code — the Unity runtime that consumes the generated `.yaml` files lives in a separate repository.

## Open Questions

1. Should the tree view support multi-select for batch operations (e.g. export several `.blend` files at once)?
2. Do you want the filter list persisted per-directory or globally?
3. Should the detail panel be tabbed (preview / properties / log) or a single scrollable view?
4. Can a project pin a specific version of an asset, or always track latest?
