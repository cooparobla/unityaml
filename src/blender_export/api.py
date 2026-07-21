"""Public Python API for blender_export.

Provides :func:`export_blend` which drives a headless Blender process to
extract scene data from a ``.blend`` file and serializes it to YAML.
"""

from __future__ import annotations

import json
import os
import shutil
import subprocess
import tempfile
from pathlib import Path
from typing import Any

from blender_export.yaml_dump import manual_yaml_dump

# Path to the Blender-side extraction script that lives next to this file.
_BLENDER_SCRIPT = str(Path(__file__).with_name("_blender_script.py"))


def find_blender() -> str:
    """Locate the ``blender`` executable.

    Resolution order:
    1. ``BLENDER_PATH`` environment variable
    2. ``blender`` on ``$PATH``
    """
    env_path = os.environ.get("BLENDER_PATH")
    if env_path and os.path.isfile(env_path):
        return env_path
    found = shutil.which("blender")
    if found:
        return found
    raise FileNotFoundError(
        "Could not find the Blender executable. Set BLENDER_PATH or ensure "
        "'blender' is on your PATH."
    )


def extract_blend_data(
    blend_path: str | os.PathLike,
    *,
    blender: str | None = None,
    selection_only: bool = False,
    export_animations: bool = True,
    unity_axes: bool = True,
) -> dict[str, Any]:
    """Run Blender headlessly and return the extracted scene data as a dict.

    Parameters
    ----------
    blend_path:
        Path to the ``.blend`` file to open.
    blender:
        Explicit path to the Blender executable.  Discovered automatically
        when *None*.
    selection_only:
        Only export selected objects (usually ``False`` in headless mode
        since there is no interactive selection).
    export_animations:
        Include animation data in the export.
    unity_axes:
        Swap Y/Z axes for Unity's coordinate system.

    Returns
    -------
    dict
        The full export payload (``format``, ``mesh``, ``scene``, and
        optionally ``animations``).
    """
    blender = blender or find_blender()
    blend_path = Path(blend_path).resolve()
    if not blend_path.exists():
        raise FileNotFoundError(f"Blend file not found: {blend_path}")

    with tempfile.NamedTemporaryFile(suffix=".json", delete=False) as tmp:
        tmp_path = tmp.name

    try:
        cmd = [
            blender,
            "--background",
            str(blend_path),
            "--python",
            _BLENDER_SCRIPT,
            "--",
            "--output",
            tmp_path,
        ]
        if selection_only:
            cmd.append("--selection-only")
        if not export_animations:
            cmd.append("--no-animations")
        if not unity_axes:
            cmd.append("--no-unity-axes")

        result = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=300,
        )
        if result.returncode != 0:
            raise RuntimeError(
                f"Blender exited with code {result.returncode}.\n"
                f"stderr:\n{result.stderr}"
            )

        with open(tmp_path) as f:
            return json.load(f)
    finally:
        if os.path.exists(tmp_path):
            os.unlink(tmp_path)


def data_to_yaml(data: dict[str, Any]) -> str:
    """Serialize an export payload dict to a YAML string."""
    lines = manual_yaml_dump(data)
    return "\n".join(lines) + "\n"


def export_blend(
    blend_path: str | os.PathLike,
    output_path: str | os.PathLike,
    *,
    blender: str | None = None,
    selection_only: bool = False,
    export_animations: bool = True,
    unity_axes: bool = True,
) -> None:
    """Export a ``.blend`` file to YAML.

    This is the main convenience function.  It runs Blender in the background,
    extracts scene data, serializes it to YAML, and writes the result to
    *output_path*.

    Parameters
    ----------
    blend_path:
        Path to the source ``.blend`` file.
    output_path:
        Destination ``.yaml`` file path.
    blender:
        Explicit path to the Blender executable (auto-discovered if *None*).
    selection_only:
        Only export selected objects.
    export_animations:
        Include animation clips.
    unity_axes:
        Convert coordinates to Unity's left-hand Y-up system.
    """
    data = extract_blend_data(
        blend_path,
        blender=blender,
        selection_only=selection_only,
        export_animations=export_animations,
        unity_axes=unity_axes,
    )
    yaml_text = data_to_yaml(data)
    out = Path(output_path)
    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_text(yaml_text)
