"""Meshes and downloadable files from the shared gimbal configuration."""

from pathlib import Path

from build123d import Compound, Shape

from argus.exporting import ExportFormat, stage_assembly, stage_part
from argus.models.base.parameters import BASE_POSE
from argus.models.base_split.parameters import FIELDS, split_configuration
from argus.models.gimbal import ASSEMBLY_STEM, base_parts, gimbal_parts
from argus.models.preview import resolve_fields


WORKSPACE_VIEWS = {"base-split": "分体底座", "gimbal-assembly": "整机装配"}
WORKSPACE_EXPORTS = {"base-lower", "base-upper", "gimbal-assembly"}


def mesh_payload(shape: Shape) -> dict:
    vertices, triangles = shape.tessellate(0.05, 0.15)
    if not vertices or not triangles:
        raise ValueError("Preview mesh is empty")
    return {
        "positions": [value for vertex in vertices for value in vertex],
        "indices": [index for triangle in triangles for index in triangle],
    }


def bounds_payload(shape: Shape) -> dict:
    bounds = shape.bounding_box()
    return {"min": tuple(bounds.min), "max": tuple(bounds.max)}


def assembly_preview(model_id: str, changes: dict) -> dict:
    values = resolve_fields(FIELDS, changes)
    profile, base = split_configuration(values)
    parts = gimbal_parts(profile, base)
    shapes = [part.local_shape.moved(BASE_POSE.inverse() * part.assembly_pose) for part in parts]
    return {
        "model": model_id,
        "parameters": values,
        "bounds": bounds_payload(Compound(children=shapes)),
        "parts": [
            {"id": part.spec.output_stem, "name": part.spec.source_label,
             "bounds": bounds_payload(shape), "mesh": mesh_payload(shape)}
            for part, shape in zip(parts, shapes)
        ],
    }


def export_assembly_selection(
    ids: set[str], values: dict[str, float], formats: tuple[ExportFormat, ...], directory: Path,
) -> list[Path]:
    profile, base = split_configuration(values)
    parts = gimbal_parts(profile, base) if "gimbal-assembly" in ids else base_parts(base)
    files = []
    for id, part in zip(("base-lower", "base-upper"), parts):
        if id in ids:
            files.extend(stage_part(part, directory, formats=formats))
    if "gimbal-assembly" in ids:
        files.append(stage_assembly(parts, directory / f"{ASSEMBLY_STEM}.step"))
    return files
