"""Identify structural parts in the input STEP and record their assembly poses."""

from dataclasses import dataclass
from pathlib import Path

from build123d import Location, Shape, import_step


class AssemblyError(ValueError):
    """The STEP cannot be read as the supported structural assembly."""


@dataclass(frozen=True)
class PartSpec:
    source_label: str
    output_stem: str
    print_rotation: tuple[int, int, int]


# Rotations from each part's local axes to its print orientation.
BRACKET = PartSpec("舵机云台-1", "gimbal_bracket", (90, 0, 0))  # local -Y mounting face
BASE = PartSpec("舵机云台底座-1", "gimbal_base", (0, 0, 0))  # local -Z square plate
HEAD = PartSpec("舵机云台头-1", "gimbal_head", (0, 90, 0))  # local +X flat exterior
PARTS = (BRACKET, BASE, HEAD)


@dataclass(frozen=True)
class PlacedPart:
    spec: PartSpec
    local_shape: Shape
    assembly_pose: Location


def read_structural_parts(source: Path) -> tuple[PlacedPart, ...]:
    if not source.is_file():
        raise AssemblyError(f"找不到装配 STEP：{source}")
    try:
        assembly = import_step(source)
    except Exception as exc:
        raise AssemblyError(f"无法读取装配 STEP {source}：{exc}") from exc

    parts = []
    for spec in PARTS:
        label = spec.source_label
        matches = [child for child in assembly.children if child.label == label]
        if len(matches) != 1:
            raise AssemblyError(f"装配中的「{label}」应有一件，实际找到 {len(matches)} 件")
        component = matches[0]
        if len(component.solids()) != 1 or not component.is_valid:
            raise AssemblyError(f"源件「{label}」应为单一有效实体")
        parts.append(PlacedPart(
            spec,
            component.located(Location()),
            assembly.location * component.location,
        ))
    return tuple(parts)
