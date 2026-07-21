"""Blender-side extraction script.

This script is designed to run *inside* Blender's embedded Python interpreter
(via ``blender --background --python ...``).  It reads a .blend file, extracts
mesh, scene-hierarchy, and animation data using the same logic as the
yaml_exporter addon, then writes the result as JSON to stdout (or a temp file)
so the outer CLI / API can post-process it.

It is NOT importable from regular CPython — it depends on the ``bpy`` and
``mathutils`` packages that only exist inside Blender.
"""

from __future__ import annotations

import json
import math
import sys

import bpy
from mathutils import Matrix


# ── Coordinate conversion ─────────────────────────────────────────────────


def convert_transform(matrix: Matrix, *, unity_axes: bool = True) -> dict:
    """Decompose a Blender matrix into position/rotation/scale dicts.

    When *unity_axes* is ``True`` the Y/Z axes are swapped (Blender Z-up
    right-hand → Unity Y-up left-hand).
    """
    if unity_axes:
        M = Matrix(
            (
                (1, 0, 0, 0),
                (0, 0, 1, 0),
                (0, 1, 0, 0),
                (0, 0, 0, 1),
            )
        )
        matrix = M @ matrix @ M

    pos, rot_quat, sca = matrix.decompose()
    euler = rot_quat.to_euler("ZXY")

    return {
        "position": {"x": round(pos.x, 4), "y": round(pos.y, 4), "z": round(pos.z, 4)},
        "rotation": {
            "x": round(math.degrees(euler.x), 4),
            "y": round(math.degrees(euler.y), 4),
            "z": round(math.degrees(euler.z), 4),
        },
        "scale": {"x": round(sca.x, 4), "y": round(sca.y, 4), "z": round(sca.z, 4)},
    }


def convert_coords_list(coords, *, unity_axes: bool = True) -> list[float]:
    """Swap Y/Z for Unity when *unity_axes* is True."""
    if unity_axes:
        return [round(coords[0], 4), round(coords[2], 4), round(coords[1], 4)]
    return [round(v, 4) for v in coords]


# ── Mesh extraction ───────────────────────────────────────────────────────


def get_mesh_data(obj, depsgraph, *, unity_axes: bool = True) -> dict:
    """Extract mesh geometry, UVs, colours, and bone weights from *obj*."""
    # Disable armature modifiers so we export the bind pose
    armature_mods = [
        m for m in obj.modifiers if m.type == "ARMATURE" and m.show_viewport
    ]
    for m in armature_mods:
        m.show_viewport = False

    try:
        eval_obj = obj.evaluated_get(depsgraph)
        mesh = eval_obj.to_mesh()
    finally:
        for m in armature_mods:
            m.show_viewport = True

    mesh_data: dict = {
        "vertices": [],
        "normals": [],
        "uvs": [],
        "faces": [],
        "colors": [],
        "weights": [],
    }

    group_names = {g.index: g.name for g in obj.vertex_groups}

    # Filter to bones that actually belong to the armature
    allowed_groups: set[str] = set()
    for mod in obj.modifiers:
        if mod.type == "ARMATURE" and mod.object:
            allowed_groups = {bone.name for bone in mod.object.data.bones}
            break

    for v in mesh.vertices:
        mesh_data["vertices"].append(convert_coords_list(v.co, unity_axes=unity_axes))
        mesh_data["normals"].append(
            convert_coords_list(v.normal, unity_axes=unity_axes)
        )

        v_weights: dict[str, float] = {}
        for g in v.groups:
            if g.group in group_names:
                gn = group_names[g.group]
                if (not allowed_groups or gn in allowed_groups) and g.weight > 0.0001:
                    v_weights[gn] = round(g.weight, 4)
        mesh_data["weights"].append(v_weights)

    if mesh.uv_layers.active:
        uv_layer = mesh.uv_layers.active.data
        v_uvs = [[0.0, 0.0] for _ in range(len(mesh.vertices))]
        for loop in mesh.loops:
            uv = uv_layer[loop.index].uv
            v_uvs[loop.vertex_index] = [round(uv[0], 4), round(uv[1], 4)]
        mesh_data["uvs"] = v_uvs

    for poly in mesh.polygons:
        face_verts = list(poly.vertices)
        if unity_axes:
            face_verts.reverse()
        mesh_data["faces"].append(face_verts)

    # Vertex colours
    if hasattr(mesh, "color_attributes") and mesh.color_attributes:
        attr = mesh.color_attributes.active
        if attr:
            v_colors: list = [None] * len(mesh.vertices)
            for loop in mesh.loops:
                data_elem = (
                    attr.data[loop.index]
                    if attr.domain == "CORNER"
                    else attr.data[loop.vertex_index]
                )
                if hasattr(data_elem, "color"):
                    col = list(data_elem.color)
                elif hasattr(data_elem, "vector"):
                    col = list(data_elem.vector) + [1.0]
                else:
                    col = [1.0, 1.0, 1.0, 1.0]
                v_colors[loop.vertex_index] = [round(c, 4) for c in col[:4]]
            mesh_data["colors"] = [c if c else [1.0, 1.0, 1.0, 1.0] for c in v_colors]

    eval_obj.to_mesh_clear()
    return mesh_data


# ── Scene hierarchy ───────────────────────────────────────────────────────


def process_object(obj, objects_list, *, unity_axes: bool = True) -> None:
    """Recursively process Blender objects into a nested hierarchy list."""
    transform_data = convert_transform(obj.matrix_local, unity_axes=unity_axes)
    obj_cfg: dict = {
        "name": obj.name,
        "active": not obj.hide_get(),
        "components": [
            {
                "_tag": "Transform",
                "position": transform_data["position"],
                "rotation": transform_data["rotation"],
                "scale": transform_data["scale"],
            }
        ],
        "children": [],
    }

    if obj.type == "MESH":
        is_skinned = any(m.type == "ARMATURE" for m in obj.modifiers)
        renderer_tag = "SkinnedMeshRenderer" if is_skinned else "MeshRenderer"
        comp: dict = {"_tag": renderer_tag, "meshPath": obj.name}
        if obj.data.materials:
            mat = obj.data.materials[0]
            if mat:
                comp["materialName"] = mat.name
        obj_cfg["components"].append(comp)

    for child in obj.children:
        process_object(child, obj_cfg["children"], unity_axes=unity_axes)

    if obj.type == "ARMATURE":
        for bone in obj.data.bones:
            if not bone.parent:
                process_bone(bone, obj, obj_cfg["children"], unity_axes=unity_axes)

    objects_list.append(obj_cfg)


def process_bone(bone, armature_obj, parent_list, *, unity_axes: bool = True) -> None:
    """Recursively process bones into nested hierarchy list."""
    if bone.parent:
        matrix = bone.parent.matrix_local.inverted() @ bone.matrix_local
    else:
        matrix = bone.matrix_local

    transform_data = convert_transform(matrix, unity_axes=unity_axes)

    bone_cfg: dict = {
        "name": bone.name,
        "active": True,
        "components": [
            {
                "_tag": "Transform",
                "position": transform_data["position"],
                "rotation": transform_data["rotation"],
                "scale": transform_data["scale"],
            }
        ],
        "children": [],
    }

    for child_bone in bone.children:
        process_bone(
            child_bone, armature_obj, bone_cfg["children"], unity_axes=unity_axes
        )

    parent_list.append(bone_cfg)


# ── Animation extraction ──────────────────────────────────────────────────


def get_bone_transform_at_frame(pbone, *, unity_axes: bool = True) -> dict:
    if pbone.parent:
        matrix = pbone.parent.matrix.inverted() @ pbone.matrix
    else:
        matrix = pbone.matrix
    return convert_transform(matrix, unity_axes=unity_axes)


def get_animation_data(armature_obj, *, unity_axes: bool = True) -> list[dict]:
    if not armature_obj.animation_data:
        return []

    animations: list[dict] = []
    original_action = armature_obj.animation_data.action
    original_frame = bpy.context.scene.frame_current

    bone_names = {b.name for b in armature_obj.pose.bones}

    applicable_actions = []
    for action in bpy.data.actions:
        for fcurve in action.fcurves:
            if fcurve.data_path.startswith("pose.bones["):
                parts = fcurve.data_path.split('"')
                if len(parts) > 1 and parts[1] in bone_names:
                    applicable_actions.append(action)
                    break

    for action in applicable_actions:
        armature_obj.animation_data.action = action
        start = int(action.frame_range[0])
        end = int(action.frame_range[1])

        anim_frames = []
        for f in range(start, end + 1):
            bpy.context.scene.frame_set(f)
            frame_bones = {}
            for pbone in armature_obj.pose.bones:
                frame_bones[pbone.name] = get_bone_transform_at_frame(
                    pbone, unity_axes=unity_axes
                )
            anim_frames.append({"number": f, "bones": frame_bones})

        animations.append(
            {
                "name": action.name,
                "fps": bpy.context.scene.render.fps,
                "frameCount": len(anim_frames),
                "frames": anim_frames,
            }
        )

    armature_obj.animation_data.action = original_action
    bpy.context.scene.frame_set(original_frame)
    return animations


# ── Main entry-point (executed inside Blender) ────────────────────────────


def main() -> None:
    """Extract scene data and write JSON to the path given via ``--output``.

    Expected argv (after ``--``):
        --output <path>
        [--selection-only]
        [--no-animations]
        [--no-unity-axes]
    """
    import argparse

    # Blender passes everything after "--" to sys.argv; strip the leading
    # elements that Blender itself consumed.
    try:
        argv = sys.argv[sys.argv.index("--") + 1 :]
    except ValueError:
        argv = []

    parser = argparse.ArgumentParser(description="Blender-side data extractor")
    parser.add_argument("--output", required=True, help="Path to write JSON output")
    parser.add_argument("--selection-only", action="store_true", default=False)
    parser.add_argument("--no-animations", action="store_true", default=False)
    parser.add_argument("--no-unity-axes", action="store_true", default=False)
    args = parser.parse_args(argv)

    unity_axes = not args.no_unity_axes

    if args.selection_only:
        objs = list(bpy.context.selected_objects)
    else:
        objs = list(bpy.context.scene.objects)

    selected_set = set(objs)
    roots = [obj for obj in objs if obj.parent not in selected_set]

    dg = bpy.context.evaluated_depsgraph_get()

    mesh_dict: dict = {}
    for obj in objs:
        if obj.type == "MESH":
            mesh_dict[obj.name] = get_mesh_data(obj, dg, unity_axes=unity_axes)

    root_objects: list[dict] = []
    for obj in roots:
        process_object(obj, root_objects, unity_axes=unity_axes)

    animations: list[dict] = []
    if not args.no_animations:
        exported_actions: set[str] = set()
        for obj in objs:
            if obj.type == "ARMATURE":
                arm_anims = get_animation_data(obj, unity_axes=unity_axes)
                for anim in arm_anims:
                    if anim["name"] not in exported_actions:
                        animations.append(anim)
                        exported_actions.add(anim["name"])

    data: dict = {
        "format": "blender",
        "mesh": mesh_dict,
        "scene": {
            "sceneName": bpy.context.scene.name,
            "rootObjects": root_objects,
        },
    }
    if animations:
        data["animations"] = animations

    with open(args.output, "w") as f:
        json.dump(data, f)


if __name__ == "__main__":
    main()
