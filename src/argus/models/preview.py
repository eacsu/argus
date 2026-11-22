"""Dimensions that can be edited in a model preview."""

from dataclasses import dataclass
from math import isfinite


@dataclass(frozen=True)
class PreviewField:
    key: str
    label: str
    group: str
    default: float
    minimum: float
    maximum: float
    unit: str = "mm"


class PreviewParameterError(ValueError):
    def __init__(self, fields: dict[str, str]):
        super().__init__("请检查参数后重新生成。")
        self.fields = fields


def resolve_fields(fields: tuple[PreviewField, ...], changes: dict) -> dict[str, float]:
    known = {field.key for field in fields}
    errors = {key: "未知参数。" for key in changes.keys() - known}
    values = {}
    for field in fields:
        value = changes.get(field.key, field.default)
        if (
            type(value) not in (int, float)
            or not field.minimum <= value <= field.maximum
            or not isfinite(value)
        ):
            errors[field.key] = (
                f"请输入 {field.minimum:g}–{field.maximum:g} {field.unit} 范围内的数值。"
            )
        else:
            values[field.key] = float(value)
    if errors:
        raise PreviewParameterError(errors)
    return values
