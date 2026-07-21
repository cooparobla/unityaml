"""Pure-Python YAML serializer.

Replicates the dumping logic from the Blender addon with no external
dependencies.  Produces a compact, human-readable YAML dialect that uses
flow-style for small dicts/lists and YAML tags (``!TagName``) for typed
nodes.
"""

from __future__ import annotations

from typing import Any


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def is_simple_dict(d: Any) -> bool:
    """Check if a dictionary is simple enough to be dumped on one line."""
    if not isinstance(d, dict) or "_tag" in d:
        return False
    if len(d) > 4:
        return False
    return all(not isinstance(v, (dict, list)) for v in d.values())


def dump_simple_dict(d: dict) -> str:
    """Dump a simple dictionary as a single-line flow-style YAML mapping."""
    items = []
    for k, v in d.items():
        val_str = str(v).lower() if isinstance(v, bool) else str(v)
        items.append(f"{k}: {val_str}")
    return f"{{ {', '.join(items)} }}"


def is_simple_list(lst: Any) -> bool:
    """Check if a list is simple enough to be dumped as a flow-style YAML sequence."""
    return (
        isinstance(lst, list)
        and all(not isinstance(v, (dict, list)) for v in lst)
        and len(lst) <= 10
    )


def dump_simple_list(lst: list) -> str:
    """Dump a simple list as a single-line flow-style YAML sequence."""
    items = []
    for v in lst:
        val_str = str(v).lower() if isinstance(v, bool) else str(v)
        items.append(val_str)
    return f"[{', '.join(items)}]"


# ---------------------------------------------------------------------------
# Main dumper
# ---------------------------------------------------------------------------


def manual_yaml_dump(data: Any, indent: int = 0) -> list[str]:
    """YAML dumper supporting tags and compact flow-style for simple types.

    Returns a list of lines (without trailing newlines).
    """
    lines: list[str] = []
    space = "  " * indent

    if isinstance(data, dict):
        keys = list(data.keys())
        # Ensure "mesh" sorts before "scene" when both are present.
        if "mesh" in keys and "scene" in keys:
            keys.sort(key=lambda x: 0 if x == "mesh" else 1)

        if "_tag" in data:
            lines.append(f"{space}!{data['_tag']}")
            for key, value in data.items():
                if key == "_tag":
                    continue
                if is_simple_dict(value):
                    lines.append(f"{space}  {key}: {dump_simple_dict(value)}")
                elif is_simple_list(value):
                    lines.append(f"{space}  {key}: {dump_simple_list(value)}")
                elif isinstance(value, (dict, list)):
                    lines.append(f"{space}  {key}:")
                    lines.extend(manual_yaml_dump(value, indent + 2))
                else:
                    val_str = (
                        str(value).lower() if isinstance(value, bool) else str(value)
                    )
                    lines.append(f"{space}  {key}: {val_str}")
            return lines

        for key in keys:
            value = data[key]
            if is_simple_dict(value):
                lines.append(f"{space}{key}: {dump_simple_dict(value)}")
            elif is_simple_list(value):
                lines.append(f"{space}{key}: {dump_simple_list(value)}")
            elif isinstance(value, (dict, list)):
                lines.append(f"{space}{key}:")
                lines.extend(manual_yaml_dump(value, indent + 1))
            else:
                val_str = str(value).lower() if isinstance(value, bool) else str(value)
                lines.append(f"{space}{key}: {val_str}")

    elif isinstance(data, list):
        for item in data:
            if is_simple_list(item):
                lines.append(f"{space}- {dump_simple_list(item)}")
            elif isinstance(item, dict) and is_simple_dict(item):
                lines.append(f"{space}- {dump_simple_dict(item)}")
            elif isinstance(item, (dict, list)):
                res = manual_yaml_dump(item, indent + 1)
                if res:
                    first_line = res[0].lstrip()
                    res[0] = space + "- " + first_line
                    lines.extend(res)
            else:
                val_str = str(item).lower() if isinstance(item, bool) else str(item)
                lines.append(f"{space}- {val_str}")
    else:
        val_str = str(data).lower() if isinstance(data, bool) else str(data)
        lines.append(f"{space}{val_str}")

    return lines
