"""Editable dimensions of the bracket."""

from dataclasses import replace

from argus.models.bracket import BracketParameters, build_bracket
from argus.models.bracket.parameters import BRACKET_PARAMETERS
from argus.models.preview import PreviewField


FIELDS = (
    PreviewField("window_width", "安装窗宽", "安装窗", BRACKET_PARAMETERS.window_width, 10, 18),
    PreviewField("window_height", "安装窗高", "安装窗", BRACKET_PARAMETERS.window_height, 16, 28),
    PreviewField("pin_diameter", "定位销直径", "定位销", 2 * BRACKET_PARAMETERS.pin_radius, 3, 5),
    PreviewField("pin_depth", "定位销伸出量", "定位销", BRACKET_PARAMETERS.pin_depth, 1.5, 4),
    PreviewField("horn_clearance", "舵盘槽单边间隙", "舵盘槽", BRACKET_PARAMETERS.horn_seat.side_clearance, 0.1, 0.4),
)


def preview_parameters(values: dict[str, float]) -> BracketParameters:
    return replace(
        BRACKET_PARAMETERS,
        window_width=values["window_width"],
        window_height=values["window_height"],
        pin_radius=values["pin_diameter"] / 2,
        pin_depth=values["pin_depth"],
        horn_seat=replace(BRACKET_PARAMETERS.horn_seat, side_clearance=values["horn_clearance"]),
    )


def build_preview(values: dict[str, float]):
    return build_bracket(preview_parameters(values))
