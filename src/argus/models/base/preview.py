"""Editable dimensions of the base."""

from dataclasses import replace

from argus.models.base import build_base
from argus.models.base.parameters import BASE_PARAMETERS
from argus.models.preview import PreviewField, PreviewParameterError


FIELDS = (
    PreviewField("plate_side", "底板边长", "底板", BASE_PARAMETERS.plate_side, 34, 50),
    PreviewField("plate_thickness", "板厚", "底板", BASE_PARAMETERS.plate_thickness, 2.5, 6),
    PreviewField("corner_hole_pitch", "角孔孔距", "角孔", 2 * BASE_PARAMETERS.corner_holes.offset[0], 26, 42),
    PreviewField("corner_hole_diameter", "角孔直径", "角孔", 2 * BASE_PARAMETERS.corner_holes.radius, 2, 4),
    PreviewField("ring_height", "卡环高度", "卡环", round(BASE_PARAMETERS.ring.height, 6), 6, 14),
)


def build_preview(values: dict[str, float]):
    side = values["plate_side"]
    pitch = values["corner_hole_pitch"]
    diameter = values["corner_hole_diameter"]
    if pitch + diameter > side - 2 * BASE_PARAMETERS.plate_corner_radius:
        raise PreviewParameterError({
            "corner_hole_pitch": "孔距和孔径合计过大。请缩小其中一项，或增大底板边长。",
        })

    return build_base(replace(
        BASE_PARAMETERS,
        plate_side=side,
        plate_thickness=values["plate_thickness"],
        ring=replace(BASE_PARAMETERS.ring, height=values["ring_height"]),
        corner_holes=replace(BASE_PARAMETERS.corner_holes, offset=(pitch / 2, pitch / 2), radius=diameter / 2),
    ))
