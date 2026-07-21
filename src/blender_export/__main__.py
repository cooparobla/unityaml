"""CLI entry-point for blender_export.

Run with::

    python -m blender_export scene.blend -o scene.yaml
"""

from __future__ import annotations

import argparse
import sys

from blender_export.api import export_blend


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="blender_export",
        description="Export a .blend file to YAML (headless Blender).",
    )
    parser.add_argument(
        "blend_file",
        help="Path to the .blend file to export.",
    )
    parser.add_argument(
        "-o",
        "--output",
        default=None,
        help=(
            "Output .yaml file path.  Defaults to the blend file name with a "
            ".yaml extension."
        ),
    )
    parser.add_argument(
        "--blender",
        default=None,
        help=(
            "Path to the Blender executable.  Auto-discovered from "
            "BLENDER_PATH or $PATH if not given."
        ),
    )
    parser.add_argument(
        "--all-objects",
        action="store_true",
        default=False,
        help="Export all objects, not just the selection.",
    )
    parser.add_argument(
        "--no-animations",
        action="store_true",
        default=False,
        help="Skip animation export.",
    )
    parser.add_argument(
        "--no-unity-axes",
        action="store_true",
        default=False,
        help="Keep Blender's native coordinate system (Z-up, right-hand).",
    )
    args = parser.parse_args(argv)

    output = args.output
    if output is None:
        # Derive from input: foo.blend → foo.yaml
        if args.blend_file.endswith(".blend"):
            output = args.blend_file[:-6] + ".yaml"
        else:
            output = args.blend_file + ".yaml"

    try:
        export_blend(
            args.blend_file,
            output,
            blender=args.blender,
            selection_only=not args.all_objects,
            export_animations=not args.no_animations,
            unity_axes=not args.no_unity_axes,
        )
    except FileNotFoundError as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 1
    except RuntimeError as exc:
        print(f"Blender error: {exc}", file=sys.stderr)
        return 2

    print(f"Exported to {output}")
    return 0


if __name__ == "__main__":
    sys.exit(main())
