"""Place, write and verify a structural part's export files."""

import logging
from pathlib import Path
from typing import Literal

from build123d import Compound, GeomType, Mesher, Pos, Rot, Shape, export_step, export_stl, import_step, import_stl

from argus.assembly import PartSpec, PlacedPart


logger = logging.getLogger(__name__)

ExportFormat = Literal["step", "3mf", "stl"]
_MESH_DEFLECTION = 0.01
_MESH_ANGLE = 0.1


class ExportError(ValueError):
    """A part could not be exported or verified."""


class FormatExportError(ExportError):
    def __init__(self, export_format: ExportFormat, reason: str):
        self.export_format = export_format
        super().__init__(f"{export_format.upper()}：{reason}")


def _write_step(placed: Shape, path: Path, *, is_reference: bool) -> float:
    if is_reference:
        model = Compound(children=[placed], label=placed.label)
        volume_tolerance, bounds_tolerance = 1e-4, 1e-5
    else:
        model = placed
        volume_tolerance, bounds_tolerance = 0.01, 0.001

    if not export_step(model, path):
        raise ExportError("STEP 写入失败")
    reread = import_step(path)
    expected, actual = placed.bounding_box(), reread.bounding_box()
    if (
        len(reread.solids()) != 1
        or not reread.is_valid
        or abs(reread.volume - placed.volume) > volume_tolerance
        or (actual.min - expected.min).length > bounds_tolerance
        or (actual.max - expected.max).length > bounds_tolerance
    ):
        raise ExportError("STEP 回读的实体、体积或装配位姿不一致")
    return reread.volume


def _printable_shape(local_shape: Shape, spec: PartSpec) -> tuple[Shape, float]:
    oriented = Rot(*spec.print_rotation) * local_shape
    bounds = oriented.bounding_box()
    center = bounds.center()
    printable = Pos(-center.X, -center.Y, -bounds.min.Z) * oriented
    printable.label = spec.output_stem
    contact_area = sum(
        face.area for face in printable.faces()
        if face.geom_type == GeomType.PLANE
        and face.normal_at().Z < -0.999
        and abs(face.center().Z) < 1e-5
    )
    if contact_area <= 0:
        raise ExportError("打印朝向缺少贴床平面")
    return printable, contact_area


def _check_mesh_bounds(printable: Shape, mesh: Shape, bed_tolerance: float) -> float:
    bounds = printable.bounding_box()
    mesh_bounds = mesh.bounding_box()
    if abs(mesh_bounds.min.Z) > bed_tolerance or (mesh_bounds.size - bounds.size).length > 0.05:
        raise ExportError("网格回读的贴床高度或外形尺寸不一致")
    return mesh_bounds.size.Z


def _write_3mf(printable: Shape, path: Path, *, bed_tolerance: float) -> tuple[int, float]:
    mesher = Mesher()
    mesher.add_shape(printable, linear_deflection=_MESH_DEFLECTION, angular_deflection=_MESH_ANGLE)
    mesher.write(path)
    reader = Mesher()
    meshes = reader.read(path)
    if len(meshes) != 1 or reader.triangle_counts[0] <= 0:
        raise ExportError("3MF 回读没有有效网格")
    mesh = meshes[0]
    mesh_height = _check_mesh_bounds(printable, mesh, bed_tolerance)
    if not any(
        abs(face.center().Z) <= bed_tolerance
        and face.normal_at().Z < -0.999
        and face.bounding_box().size.Z <= bed_tolerance
        for face in mesh.faces()
    ):
        raise ExportError("3MF 回读的网格缺少贴床平面")
    return reader.triangle_counts[0], mesh_height


def _write_stl(printable: Shape, path: Path, *, bed_tolerance: float) -> None:
    if not export_stl(printable, path, tolerance=_MESH_DEFLECTION, angular_tolerance=_MESH_ANGLE, ascii_format=False):
        raise ExportError("STL 写入失败")
    with path.open("rb") as file:
        file.seek(80)
        triangles = int.from_bytes(file.read(4), "little")
    if triangles <= 0 or path.stat().st_size != 84 + 50 * triangles:
        raise ExportError("STL 回读没有有效网格")
    _check_mesh_bounds(printable, import_stl(path), bed_tolerance)


def stage_part(
    part: PlacedPart, directory: Path, *, is_reference: bool = False,
    formats: tuple[ExportFormat, ...] = ("step", "3mf"),
) -> tuple[Path, ...]:
    """Write the supplied local geometry in assembly and print coordinates."""
    spec = part.spec
    bed_tolerance = 0.03 if is_reference else 0.02
    printable = None
    step_volume = mesh_stats = None
    contact_area = 0.0
    files = []
    for export_format in formats:
        path = directory / f"{spec.output_stem}.{export_format}"
        try:
            if export_format == "step":
                placed = part.local_shape.moved(part.assembly_pose)
                placed.label = spec.output_stem
                step_volume = _write_step(placed, path, is_reference=is_reference)
            else:
                if printable is None:
                    printable, contact_area = _printable_shape(part.local_shape, spec)
                if export_format == "3mf":
                    mesh_stats = _write_3mf(printable, path, bed_tolerance=bed_tolerance)
                elif export_format == "stl":
                    _write_stl(printable, path, bed_tolerance=bed_tolerance)
                else:
                    raise ExportError("不支持的导出格式")
        except Exception as exc:
            raise FormatExportError(export_format, str(exc)) from exc
        files.append(path)

    if is_reference and step_volume is not None and mesh_stats is not None:
        triangles, print_height = mesh_stats
        logger.info(
            "%s: STEP volume %.2f mm^3, 3MF triangles %d, bed contact %.2f mm^2, height %.2f mm",
            spec.output_stem, step_volume, triangles, contact_area, print_height,
        )
    return tuple(files)
