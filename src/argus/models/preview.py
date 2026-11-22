"""Dimensions that can be edited in a model preview."""

from dataclasses import dataclass, field
from math import isfinite


@dataclass(frozen=True)
class PreviewChoice:
    value: int
    label: str
    defaults: dict[str, float] = field(default_factory=dict)


@dataclass(frozen=True)
class PreviewField:
    key: str
    label: str
    group: str
    default: float
    minimum: float
    maximum: float
    unit: str = "mm"
    choices: tuple[PreviewChoice, ...] = ()
    active_when: tuple[str, int] | None = None


class PreviewParameterError(ValueError):
    def __init__(self, fields: dict[str, str]):
        super().__init__("请检查参数后重新生成。")
        self.fields = fields


def resolve_fields(fields: tuple[PreviewField, ...], changes: dict) -> dict[str, float]:
    known = {field.key for field in fields}
    errors = {key: "未知参数。" for key in changes.keys() - known}
    defaults = {field.key: field.default for field in fields}
    for field in fields:
        if not field.choices:
            continue
        value = changes.get(field.key, field.default)
        choice = next((choice for choice in field.choices if type(value) in (int, float) and value == choice.value), None)
        if choice is None:
            errors[field.key] = "请选择列表中的型号。"
        else:
            defaults.update(choice.defaults)
    values = {}
    for field in fields:
        if field.key in errors:
            continue
        if field.active_when:
            key, required = field.active_when
            if changes.get(key, defaults[key]) != required:
                values[field.key] = field.default
                continue
        value = changes.get(field.key, defaults[field.key])
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
