"""Model catalog, build123d previews and file downloads."""

import logging
from dataclasses import asdict
from pathlib import Path
from tempfile import TemporaryDirectory
from threading import Lock
from zipfile import ZIP_DEFLATED, ZipFile

from build123d import Shape
from fastapi import APIRouter, HTTPException, Response
from pydantic import BaseModel, ConfigDict, Field

from argus.assembly import PlacedPart
from argus.exporting import ExportFormat, FormatExportError, stage_part
from argus.models.base_split.parameters import FIELDS as ASSEMBLY_FIELDS
from argus.models.catalog import MODELS as _MODELS, ConfiguredModel
from argus.models.preview import PreviewParameterError, resolve_fields
from argus.web.assembly_view import (
    WORKSPACE_EXPORTS, WORKSPACE_VIEWS, assembly_preview, bounds_payload, export_assembly_selection, mesh_payload,
)


logger = logging.getLogger(__name__)
router = APIRouter(prefix="/api")
_CAD_LOCK = Lock()


class PreviewRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    parameters: dict[str, object]


class ExportModelRequest(PreviewRequest):
    id: str
    parameters: dict[str, object] = Field(default_factory=dict)


class ExportRequest(BaseModel):
    model_config = ConfigDict(extra="forbid")
    models: list[ExportModelRequest] = Field(min_length=1, max_length=len(_MODELS) + len(WORKSPACE_EXPORTS))
    formats: list[ExportFormat] = Field(min_length=1, max_length=3)


def _model_or_404(model_id: str) -> ConfiguredModel:
    model = _MODELS.get(model_id)
    if model is None:
        raise HTTPException(404, detail={"message": "找不到指定零件。", "model": model_id})
    return model


def _build_shape(model: ConfiguredModel, values: dict[str, float]) -> Shape:
    shape = model.build(values)
    if not shape.is_valid or len(shape.solids()) != 1:
        raise ValueError("Model must be a single valid solid")
    return shape


@router.get("/models")
def models():
    assembly_fields = [asdict(field) for field in ASSEMBLY_FIELDS]
    workspaces = [{"id": key, "name": name, "fields": assembly_fields} for key, name in WORKSPACE_VIEWS.items()]
    return {"models": workspaces + [
        {"id": key, "name": model.name, "fields": [asdict(field) for field in model.fields]}
        for key, model in _MODELS.items()
    ]}


@router.post("/models/{model_id}/preview")
def preview(model_id: str, request: PreviewRequest):
    workspace = model_id in WORKSPACE_VIEWS
    model = None if workspace else _model_or_404(model_id)
    try:
        with _CAD_LOCK:
            if model is None:
                return assembly_preview(model_id, request.parameters)
            values = resolve_fields(model.fields, request.parameters)
            shape = _build_shape(model, values)
            mesh = mesh_payload(shape)
            bounds = bounds_payload(shape)
    except PreviewParameterError as exc:
        raise HTTPException(422, detail={"message": str(exc), "fields": exc.fields}) from exc
    except Exception as exc:
        logger.exception("Could not generate %s preview", model_id)
        raise HTTPException(500, detail={"message": "模型生成失败，可以调整参数后重试。"}) from exc

    return {
        "model": model_id,
        "parameters": values,
        "mesh": mesh,
        "bounds": bounds,
    }


@router.post("/exports")
def export_models(request: ExportRequest) -> Response:
    ids = {entry.id for entry in request.models}
    if len(ids) != len(request.models) or len(set(request.formats)) != len(request.formats):
        raise HTTPException(422, detail={"message": "零件和格式不能重复选择。"})

    formats = tuple(request.formats)
    workspace_entries = [entry for entry in request.models if entry.id in WORKSPACE_EXPORTS]
    selections = [(entry, _model_or_404(entry.id)) for entry in request.models if entry.id not in WORKSPACE_EXPORTS]
    if "gimbal-assembly" in ids and formats != ("step",):
        raise HTTPException(422, detail={"message": "整机装配支持 STEP 导出。"})
    try:
        with TemporaryDirectory(prefix="argus-export-") as directory:
            staging = Path(directory)
            files = []
            if workspace_entries:
                try:
                    configurations = [resolve_fields(ASSEMBLY_FIELDS, entry.parameters) for entry in workspace_entries]
                    values = configurations[0]
                    if any(configuration != values for configuration in configurations[1:]):
                        raise HTTPException(422, detail={"message": "分体底座和整机请使用同一组参数。"})
                    with _CAD_LOCK:
                        files.extend(export_assembly_selection(ids & WORKSPACE_EXPORTS, values, formats, staging))
                except PreviewParameterError as exc:
                    raise HTTPException(422, detail={"message": str(exc), "fields": exc.fields}) from exc
                except HTTPException:
                    raise
                except Exception as exc:
                    logger.exception("Gimbal export failed")
                    raise HTTPException(500, detail={"message": "分体底座或整机导出失败，请重试。"}) from exc
            for entry, model in selections:
                try:
                    values = resolve_fields(model.fields, entry.parameters)
                    with _CAD_LOCK:
                        shape = _build_shape(model, values)
                        files.extend(stage_part(PlacedPart(model.spec, shape, model.assembly_pose), staging, formats=formats))
                except PreviewParameterError as exc:
                    raise HTTPException(422, detail={
                        "message": f"{model.name}的参数无效。", "model": entry.id, "fields": exc.fields,
                    }) from exc
                except FormatExportError as exc:
                    logger.exception("Could not export %s as %s", entry.id, exc.export_format)
                    raise HTTPException(500, detail={
                        "message": f"{model.name}的 {exc.export_format.upper()} 导出失败，请重试。",
                        "model": entry.id, "format": exc.export_format,
                    }) from exc
                except Exception as exc:
                    logger.exception("Could not build %s for export", entry.id)
                    labels = "、".join(fmt.upper() for fmt in formats)
                    raise HTTPException(500, detail={
                        "message": f"{model.name}生成失败，无法导出 {labels}。", "model": entry.id,
                    }) from exc

            path, media_type = files[0], "application/octet-stream"
            if len(files) > 1:
                path, media_type = staging / "argus-models.zip", "application/zip"
                with ZipFile(path, "w", compression=ZIP_DEFLATED) as archive:
                    for file in files:
                        archive.write(file, arcname=file.name)
            return Response(path.read_bytes(), media_type=media_type, headers={
                "Content-Disposition": f'attachment; filename="{path.name}"',
            })
    except OSError as exc:
        logger.exception("Could not prepare the download")
        raise HTTPException(500, detail={"message": "下载文件准备失败，请重试。"}) from exc
