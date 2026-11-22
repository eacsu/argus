"""Machining and fit parameters available for the reference horn."""

from dataclasses import replace

from argus.models.preview import PreviewField, PreviewParameterError
from argus.models.servo_horn import ServoHornParameters, build_servo_horn
from argus.models.servo_horn.parameters import SERVO_HORN_PARAMETERS


def fields_for_horn(horn: ServoHornParameters) -> tuple[PreviewField, ...]:
    return (
        PreviewField("arm_hole_diameter", "臂孔直径", "螺钉孔", horn.arm_hole_diameter, 0.8, 2),
        PreviewField("center_hole_diameter", "中心通孔直径", "螺钉孔", horn.center_hole_diameter, 1.8, 2.5),
        PreviewField("major_diameter", "轴齿顶径", "内花键", horn.socket.major_diameter, 4.2, 5.8),
        PreviewField("minor_diameter", "轴齿根径", "内花键", horn.socket.minor_diameter, 3.4, 5.4),
        PreviewField("depth", "啮合深度", "内花键", horn.socket.depth, 1.5, 3.8),
        PreviewField("clearance", "径向余量", "内花键", horn.socket.clearance, 0, 0.25),
    )


FIELDS = fields_for_horn(SERVO_HORN_PARAMETERS)


def build_preview(values: dict[str, float], *, horn: ServoHornParameters = SERVO_HORN_PARAMETERS):
    socket = replace(
        horn.socket, major_diameter=values["major_diameter"], minor_diameter=values["minor_diameter"],
        depth=values["depth"], clearance=values["clearance"],
    )
    if socket.minor_diameter >= socket.major_diameter:
        raise PreviewParameterError({"minor_diameter": "轴齿根径必须小于轴齿顶径。"})
    if socket.major_diameter + 2 * socket.clearance > horn.envelope.hub_diameter - 1:
        raise PreviewParameterError({"major_diameter": "花键外侧至少需保留 0.5 mm 凸台壁厚。"})
    if socket.depth > horn.envelope.overall_height - 0.8:
        raise PreviewParameterError({"depth": "中心螺钉承压台阶至少需保留 0.8 mm 厚度。"})
    minimum_spacing = min(
        right - left for arm in horn.envelope.arms() for left, right in zip(arm.hole_offsets, arm.hole_offsets[1:])
    )
    if values["arm_hole_diameter"] >= minimum_spacing:
        raise PreviewParameterError({"arm_hole_diameter": "臂孔直径必须小于该舵盘的最小孔距。"})
    return build_servo_horn(replace(
        horn, socket=socket, arm_hole_diameter=values["arm_hole_diameter"],
        center_hole_diameter=values["center_hole_diameter"],
    ))
