"""Editable dimensions of the gimbal head."""

from dataclasses import replace

from argus.models.common import Circle
from argus.models.head import HeadParameters, build_head
from argus.models.head.parameters import HEAD_PARAMETERS
from argus.models.preview import PreviewField


_LUGS = (
    ("main_pivot_diameter", "主轴孔直径", 0, 3, 5),
    ("upper_lug_diameter", "上耳孔直径", 2, 1.5, 2.6),
    ("lower_lug_diameter", "下耳孔直径", 1, 1.5, 2.6),
)


def _bore(index: int) -> Circle:
    (hole,) = HEAD_PARAMETERS.lugs[index].holes
    assert isinstance(hole, Circle)
    return hole


FIELDS = tuple(
    PreviewField(key, label, "耳座孔", 2 * _bore(index).radius, minimum, maximum)
    for key, label, index, minimum, maximum in _LUGS
)


def preview_parameters(values: dict[str, float]) -> HeadParameters:
    lugs = list(HEAD_PARAMETERS.lugs)
    for key, _, index, _, _ in _LUGS:
        lugs[index] = replace(lugs[index], holes=(replace(_bore(index), radius=values[key] / 2),))
    return replace(HEAD_PARAMETERS, lugs=tuple(lugs))


def build_preview(values: dict[str, float]):
    return build_head(preview_parameters(values))
