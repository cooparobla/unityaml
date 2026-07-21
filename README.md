# UnityYAML

A PySide-based file explorer and project construction tool for building Unity projects entirely outside the Unity editor UI.

## Overview

UnityYAML lets you construct Unity project data — scene hierarchies, mesh references, materials, and component configurations — by assembling `.yaml` files from `.blend` exports, supplementary `.yaml` config files, and raw assets. The goal is to never need the Unity UI for anything beyond basic build settings and scene management.

## Core Concepts

- **File Explorer** — A tree-view of the filesystem rooted where the tool is opened, filtered to show only project-relevant files (`.blend`, `.yaml`, `.json`, `.png`).
- **Blender Export** — Headless extraction of mesh, skeleton, and animation data from `.blend` files into structured `.yaml` via the `blender_export` module.
- **YAML Assembly** — Combine exported Blender data with hand-authored config `.yaml` files to produce complete Unity-ready scene descriptions.

## Project Structure

```
src/
  blender_export/       # Headless Blender-to-YAML export pipeline
    __init__.py
    __main__.py          # CLI: python -m blender_export scene.blend -o scene.yaml
    api.py               # Python API: export_blend(), extract_blend_data()
    yaml_dump.py         # Pure-Python YAML serializer (no dependencies)
    _blender_script.py   # Runs inside Blender's Python interpreter
  unityaml/             # Pure Python backend logic (dataclasses, file handlers, versioning, projects)
  unityaml_gui/         # PySide6 GUI application (depends on unityaml)
plans/                   # Design documents and roadmap
```

## Quick Start

```bash
# Setup
uv venv && uv sync

# Export a .blend file to YAML
uv run blender-export scene.blend -o scene.yaml

# Launch the file explorer UI (planned)
uv run unityaml-gui
```

## File Filter

The tree view filters to these extensions by default:

| Extension | Purpose |
|-----------|---------|
| `.blend`  | Blender scene/mesh source files |
| `.yaml`   | Exported scene data and hand-authored configs |
| `.json`   | Metadata and configuration |
| `.png`    | Texture and image assets |

## Scope

This repository contains **Python code only** — the tooling side (export pipeline, file explorer UI, YAML assembly). The Unity C# runtime that consumes the generated `.yaml` files lives in a separate repository.

## Dependencies

- **Python** ≥ 3.10
- **PySide6** — Qt-based UI framework
- **Blender** — Required on `$PATH` or via `BLENDER_PATH` for `.blend` export (not a Python dependency)