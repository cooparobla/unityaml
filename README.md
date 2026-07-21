# UnityYAML

A PySide6-based file explorer and project construction tool for building Unity projects entirely outside the Unity editor UI.

---

## Overview

UnityYAML provides a desktop GUI and CLI toolset to construct Unity project data — scene hierarchies, mesh references, materials, and component configurations — by assembling `.yaml` files from Blender exports, supplementary YAML config files, and raw image assets.

The primary workflow goal is to assemble and manage Unity scene data through pure YAML configurations and Blender exports, avoiding the Unity UI for scene construction.

---

## Features

- **Dual-Tab Architecture**:
  - **Assets Tab**: Lazy-loading directory tree view with custom filtering (`.blend`, `.yaml`, `.json`, `.png`, etc.), background headless Blender exports, and context-sensitive inspection panels.
  - **Projects Tab**: Manage project targets, track assigned config files and asset references, and trigger batch exports.
- **Automatic Version Grouping**:
  - Files following the `<name>.v<major>.<minor>.<ext>` convention (e.g. `character.v1.0.blend` and `character.v2.3.blend`) automatically collapse into a single tree item showing the highest version.
  - Inspect any historical version using the version selector dropdown.
- **Fast Sidecar Metadata**:
  - `.blend` metadata (objects, mesh counts, armature/animation flags) is cached in lightweight `.blend.meta.yaml` sidecar files after export, avoiding heavy Blender launches just to view file details.
- **Pure-Python Serializer**:
  - Custom YAML dumper (`blender_export.yaml_dump`) producing compact, human-readable YAML with inline flow-styles for simple structures and `!Tag` support.
- **Dark Mode UI**:
  - Custom dark theme built with PySide6 widgets.

---

## Directory Structure

```
src/
  blender_export/       # Headless Blender-to-YAML export pipeline
    api.py              # Export API (export_blend, extract_blend_data)
    yaml_dump.py        # Pure-Python YAML serializer
    _blender_script.py  # Script executed inside Blender's Python interpreter
  unityaml/             # Pure-Python data layer (dataclasses, handlers, versioning, persistence)
  unityaml_gui/         # PySide6 desktop application (views, models, dark stylesheet)

tests/                  # Unit and GUI test suite (360+ tests)
  blender_export/       # Serializer tests
  unityaml/             # Data layer, versioning, handler, and persistence tests
  unityaml_gui/         # PySide6 widget, model, signal, and app tests
```

---

## Quick Start

### Installation

Ensure Python ≥ 3.10 is installed.

```bash
# Clone and install system-wide CLI via uv
git clone https://github.com/cooparobla/unityaml.git
cd unityaml
./install.sh
```

To uninstall:
```bash
./uninstall.sh
```

### Running the GUI

Once installed, launch the desktop app from anywhere:

```bash
# Open GUI in the current working directory
unityaml

# Open GUI rooted at a specific asset directory
unityaml /path/to/my/assets
```

Alternatively, run directly with `uv`:
```bash
uv run unityaml
```

#### GUI Workflows:
1. **Filtering Assets**: Use the top filter bar in the Assets tab to specify active file extensions (e.g. `.blend .yaml .png`).
2. **Version Inspection**: Select a versioned asset to view its metadata. Use the **Version** dropdown in the detail panel to switch versions.
3. **Exporting Blender Files**: Right-click any `.blend` file in the tree (or click **⚡ Export → YAML** in the detail panel) to run a background export.
4. **Project Management**: Switch to the **Projects** tab to create a new project, add asset references or config files, and run **⚡ Export All** to batch-export all `.blend` files in the project.

---

## Command Line Export

Export `.blend` scenes to YAML directly from the terminal without opening the GUI:

```bash
# Basic export
uv run blender-export character.blend -o character.yaml

# Specify custom Blender executable path
uv run blender-export model.blend -o model.yaml --blender /opt/blender/blender
```

---

## Testing

Run the comprehensive test suite with `pytest`:

```bash
# Run all tests (data layer, exporter, and PySide6 GUI)
uv run pytest tests/ -v

# Run specific package tests
uv run pytest tests/unityaml/ -v
uv run pytest tests/unityaml_gui/ -v
uv run pytest tests/blender_export/ -v
```

---

## Configuration & Storage

User settings and project configurations are automatically saved under `~/.unityaml/`:

- `~/.unityaml/settings.yaml` — Remembers window geometry, splitter sizes, and active tab.
- `~/.unityaml/projects/<project_name>/project.yaml` — Stores project definition, config files, and asset references.

---

## Dependencies

- **Python** ≥ 3.10
- **PySide6** — Qt-based GUI framework
- **PyYAML** — YAML parsing
- **Blender** — Required on system `$PATH` (or via `--blender` flag) for exporting `.blend` files