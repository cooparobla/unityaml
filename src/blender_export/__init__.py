"""blender_export — headless Blender-to-YAML export module.

Provides both a Python API and a CLI for exporting Blender scenes to YAML
format, replicating the behaviour of the yaml_exporter Blender addon without
requiring the Blender GUI.

Usage (CLI)::

    python -m blender_export scene.blend -o scene.yaml
    python -m blender_export scene.blend --no-animations --all-objects

Usage (Python API)::

    from blender_export.api import export_blend
    export_blend("scene.blend", "scene.yaml")

    from blender_export.yaml_dump import manual_yaml_dump
    lines = manual_yaml_dump({"key": "value"})
"""

__all__ = ["api", "yaml_dump"]
