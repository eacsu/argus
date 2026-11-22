"""Build the gimbal and fasteners from one resolved base configuration."""

from dataclasses import replace
from math import atan2, degrees

from build123d import Location, Pos, Rot

from argus.assembly import BRACKET, HEAD, PartSpec, PlacedPart
from argus.models.base.parameters import BASE_POSE
from argus.models.base_servo.parameters import HornProfile
from argus.models.base_split import BaseConnection, SplitBaseParameters, build_bolt, build_insert, build_lower, build_upper
from argus.models.base_split.parameters import HORNS
from argus.models.bracket import build_bracket
from argus.models.bracket.parameters import BRACKET_PARAMETERS, BRACKET_POSE
from argus.models.head import build_head
from argus.models.head.parameters import HEAD_PARAMETERS, HEAD_POSE
from argus.models.servo_horn import build_servo_horn
from argus.models.servo_horn.single import build_single_horn
from argus.models.sg90s import build_servo
from argus.models.sg90s.parameters import SG90S


LOWER_BASE = PartSpec("下座", "gimbal_base_lower", (0, 0, 0))
UPPER_BASE = PartSpec("上盖", "gimbal_base_upper", (0, 0, 0))
SNAP_UPPER_BASE = replace(UPPER_BASE, print_rotation=(180, 0, 0))
SERVO = PartSpec("SG90S 舵机", "sg90s", (0, 0, 0))
LOWER_SERVO = replace(SERVO, source_label="底部舵机", output_stem="sg90s_bottom")
UPPER_SERVO = replace(SERVO, source_label="上部舵机", output_stem="sg90s_top")
UPPER_HORN = PartSpec("单臂舵盘", "servo_horn_single", (0, 0, 0))
ASSEMBLY_STEM = "argus_gimbal_assembly"

# The source frame already encodes the upper pivot axis and its clocking.
UPPER_SERVO_POSE = Location(
    (-13.37166149668, 20.641817075014, -16.54912455083), (0.0, 87.22195369908, 101.80908053768),
)
LOWER_SERVO_CLOCK = 76.39171489348
REFERENCE_TIP_Z = 5.4
SPLINE_END_CLEARANCE = 0.1

HORN_PARTS = {
    HornProfile.LONG: PartSpec("长短臂舵盘", "servo_horn_long", (0, 0, 0)),
    HornProfile.EQUAL: PartSpec("MG90S 十字舵盘", "mg90s_servo_horn", (0, 0, 0)),
}


def upper_horn_pose() -> Location:
    bracket = BRACKET_PARAMETERS
    return BRACKET_POSE * bracket.horn_seat.horn_pose(bracket.right_arm_x, bracket.shaft_axis)


def upper_servo_parameters():
    socket = BRACKET_PARAMETERS.horn_seat.horn.socket
    frame = UPPER_SERVO_POSE.inverse() * upper_horn_pose()
    across = (frame * Pos(1, 0, 0)).position - frame.position
    phase = degrees(atan2(across.Y, across.X)) - socket.phase
    return replace(SG90S, spline=replace(socket, phase=phase))


def base_parts(base: SplitBaseParameters) -> tuple[PlacedPart, PlacedPart]:
    upper_spec = SNAP_UPPER_BASE if base.connection == BaseConnection.SNAP else UPPER_BASE
    return (
        PlacedPart(LOWER_BASE, build_lower(base), BASE_POSE),
        PlacedPart(upper_spec, build_upper(base), BASE_POSE * Pos(0, 0, base.lower_thickness)),
    )


def gimbal_parts(profile: HornProfile, base: SplitBaseParameters) -> tuple[PlacedPart, ...]:
    horn = HORNS[profile]
    horn_pose = BASE_POSE * Pos(*base.center, base.seat_height)
    tip = base.seat_height + horn.envelope.overall_height - horn.socket.depth + SPLINE_END_CLEARANCE
    offset = BASE_POSE * Pos(0, 0, tip - REFERENCE_TIP_Z) * BASE_POSE.inverse()
    lower_servo = replace(SG90S, spline=replace(horn.socket, phase=LOWER_SERVO_CLOCK - horn.socket.phase))
    lower_pose = (
        BASE_POSE * Pos(*base.center, tip) * Rot(180, 0, -LOWER_SERVO_CLOCK)
        * Pos(-lower_servo.shaft_x, 0, -lower_servo.tip_height)
    )
    parts = [
        *base_parts(base),
        PlacedPart(HORN_PARTS[profile], build_servo_horn(horn), horn_pose),
        PlacedPart(LOWER_SERVO, build_servo(lower_servo), lower_pose),
        PlacedPart(UPPER_SERVO, build_servo(upper_servo_parameters()), offset * UPPER_SERVO_POSE),
        PlacedPart(BRACKET, build_bracket(BRACKET_PARAMETERS), offset * BRACKET_POSE),
        PlacedPart(HEAD, build_head(HEAD_PARAMETERS), offset * HEAD_POSE),
        PlacedPart(UPPER_HORN, build_single_horn(BRACKET_PARAMETERS.horn_seat.horn), offset * upper_horn_pose()),
    ]
    if base.connection == BaseConnection.SNAP:
        return tuple(parts)
    hardware = base.fasteners
    bolt, insert = build_bolt(hardware), build_insert(hardware)
    for index, (x, y) in enumerate(base.bolt_centers(), 1):
        parts.extend((
            PlacedPart(
                PartSpec(f"M3 螺栓 {index}", f"m3_bolt_{index}", (0, 0, 0)), bolt,
                BASE_POSE * Pos(x, y, hardware.recess_depth - hardware.head_height),
            ),
            PlacedPart(
                PartSpec(f"M3 热熔螺母 {index}", f"m3_insert_{index}", (0, 0, 0)), insert,
                BASE_POSE * Pos(x, y, base.lower_thickness),
            ),
        ))
    return tuple(parts)
