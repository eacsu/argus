"""Editable bores of the single-arm reference horn."""

from dataclasses import replace

from argus.models.preview import PreviewField
from argus.models.servo_horn.single import SINGLE_HORN, build_single_horn


FIELDS = (
    PreviewField("arm_hole_diameter", "臂孔直径", "螺钉孔", SINGLE_HORN.arm_hole_diameter, 0.8, 1.6),
    PreviewField("center_hole_diameter", "中心通孔直径", "螺钉孔", SINGLE_HORN.center_hole_diameter, 1.8, 2.6),
    PreviewField("spline_clearance", "花键径向余量", "内花键", SINGLE_HORN.socket.clearance, 0, 0.2),
)


def build_preview(values: dict[str, float]):
    return build_single_horn(replace(
        SINGLE_HORN,
        arm_hole_diameter=values["arm_hole_diameter"],
        center_hole_diameter=values["center_hole_diameter"],
        socket=replace(SINGLE_HORN.socket, clearance=values["spline_clearance"]),
    ))
