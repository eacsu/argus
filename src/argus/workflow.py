"""Coordinate structural reconstruction, export and publication."""

import logging
from collections.abc import Iterable
from pathlib import Path
from shutil import copy2
from tempfile import TemporaryDirectory

from filelock import FileLock

from argus.assembly import BASE, BRACKET, HEAD, PARTS, PlacedPart, read_structural_parts
from argus.exporting import ExportError, stage_part
from argus.fitting import FitError, check_fit, fit_base, fit_bracket, fit_head
from argus.models.catalog import BRACKET_PRINT, HEAD_PRINT, MODELS


logger = logging.getLogger(__name__)

_FITTERS = {BRACKET: fit_bracket, BASE: fit_base, HEAD: fit_head}
_MODELS_BY_SPEC = {model.spec: model for model in MODELS.values()}


def publish(output, files, staging):
    """Keep the previous files available until all replacements have succeeded."""
    output = output.resolve()
    output.mkdir(parents=True, exist_ok=True)
    lock_path = output.parent / f".{output.name}.argus.lock"
    with FileLock(lock_path):
        _replace_batch(output, files, staging)


def _replace_batch(output, files, staging):
    backups = staging / "previous"
    backups.mkdir()
    for path in files:
        target = output / path.name
        if target.is_symlink() or target.is_file():
            copy2(target, backups / path.name, follow_symlinks=False)
        elif target.exists():
            raise OSError(f"输出路径已被占用：{target}")

    published = []
    try:
        for path in files:
            target = output / path.name
            path.replace(target)
            published.append(target)
    except OSError:
        for target in reversed(published):
            backup = backups / target.name
            if backup.exists() or backup.is_symlink():
                backup.replace(target)
            else:
                target.unlink()
        raise


def fit_and_export(source: Path, output: Path) -> None:
    fitted = []
    for reference in read_structural_parts(source):
        spec = reference.spec
        try:
            part = _FITTERS[spec](reference.local_shape)
            deviation = check_fit(reference.local_shape, part)
        except Exception as exc:
            raise FitError(f"「{spec.source_label}」拟合失败：{exc}") from exc
        logger.info(
            "%s (%s) 双向差集 %.6f%%，边界采样最大偏差 %.6f mm",
            spec.source_label, spec.output_stem, 100 * deviation.volume_ratio, deviation.boundary_mm,
        )
        fitted.append(PlacedPart(spec, part, reference.assembly_pose))
    _export_and_publish(output, fitted)


def build_and_export(output: Path, *, bracket_print: bool = False, head_print: bool = False) -> None:
    variants = tuple(spec for spec, selected in ((BRACKET_PRINT, bracket_print), (HEAD_PRINT, head_print)) if selected)
    parts = []
    for spec in variants or PARTS:
        model = _MODELS_BY_SPEC[spec]
        try:
            shape = model.build_default()
            if len(shape.solids()) != 1 or not shape.is_valid:
                raise ValueError("建模结果应为单一有效实体")
        except Exception as exc:
            raise ExportError(f"{spec.output_stem} 参数化建模失败：{exc}") from exc
        parts.append(PlacedPart(spec, shape, model.assembly_pose))
    _export_and_publish(output, parts)


def export_reference_parts(source: Path, output: Path) -> None:
    _export_and_publish(output, read_structural_parts(source), is_reference=True)


def _export_and_publish(output: Path, parts: Iterable[PlacedPart], *, is_reference: bool = False) -> None:
    output = output.resolve()
    output.parent.mkdir(parents=True, exist_ok=True)
    with TemporaryDirectory(prefix=".argus-", dir=output.parent) as directory:
        staging = Path(directory)
        files = []
        for part in parts:
            try:
                files.extend(stage_part(part, staging, is_reference=is_reference))
            except Exception as exc:
                raise ExportError(f"{part.spec.output_stem} 导出失败：{exc}") from exc
        publish(output, files, staging)
    logger.info("已导出 %d 个文件到 %s", len(files), output)
