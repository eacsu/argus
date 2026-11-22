"""Measured SG90S dimensions in a local frame with the output directed along +Z."""

from dataclasses import replace

from argus.models.preview import PreviewField
from argus.models.servo_horn.parameters import SERVO_HORN_PARAMETERS
from argus.models.sg90s import ServoParameters, build_servo


SG90S = ServoParameters(
    body_length=23.0, body_width=12.5, body_height=23.0,
    ear_span=33.0, ear_pitch=27.0, ear_height=18.5, ear_thickness=3.0, mounting_hole=2.2,
    shaft_x=-5.25, cover_height=5.8, output_height=3.5, screw_hole=2.05,
    spline=replace(SERVO_HORN_PARAMETERS.socket, phase=63.0),
)

FIELDS = (
    PreviewField("body_length", "机壳长度", "机壳", SG90S.body_length, 22, 25),
    PreviewField("body_width", "机壳宽度", "机壳", SG90S.body_width, 11.5, 14),
    PreviewField("body_height", "机壳高度", "机壳", SG90S.body_height, 22, 25),
    PreviewField("ear_pitch", "安装孔距", "安装耳", SG90S.ear_pitch, 26, 29),
    PreviewField("mounting_hole", "安装孔径", "安装耳", SG90S.mounting_hole, 1.8, 2.6),
    PreviewField("output_height", "轴伸长度", "输出轴", SG90S.output_height, 2.5, 4.5),
)


def build_preview(values: dict[str, float]):
    return build_servo(replace(SG90S, **values))
