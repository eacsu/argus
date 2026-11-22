"""Configured models and their shared preview and export metadata."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import partial

from build123d import Location, Shape

from argus.assembly import BASE, BRACKET, HEAD, PartSpec
from argus.models.base import build_base, preview as base
from argus.models.base.parameters import BASE_PARAMETERS, BASE_POSE
from argus.models.base_servo import preview as base_servo
from argus.models.base_servo.parameters import BASE_CONFIGURATIONS, HornProfile, build_base_for_horn
from argus.models.bracket import build_bracket, preview as bracket
from argus.models.bracket.parameters import BRACKET_PARAMETERS, BRACKET_POSE
from argus.models.bracket_print import build_print_bracket, preview as bracket_print
from argus.models.gimbal import HORN_PARTS, SERVO, UPPER_HORN, upper_horn_pose
from argus.models.head import build_head, preview as head
from argus.models.head.parameters import HEAD_PARAMETERS, HEAD_POSE
from argus.models.head_print import build_print_head, preview as head_print
from argus.models.preview import PreviewField
from argus.models.servo_horn import build_servo_horn, single_preview, preview as servo_horn
from argus.models.servo_horn.parameters import LONG_HORN_PARAMETERS, SERVO_HORN_PARAMETERS
from argus.models.servo_horn.single import build_single_horn
from argus.models.sg90s import build_servo
from argus.models.sg90s import parameters as sg90s


BASE_SERVO = replace(BASE, output_stem="gimbal_base_servo")
SERVO_HORN = HORN_PARTS[HornProfile.EQUAL]
LONG_SERVO_HORN = HORN_PARTS[HornProfile.LONG]
SERVO_HORN_SPECS = HORN_PARTS
BRACKET_PRINT = replace(BRACKET, output_stem="gimbal_bracket_print")
HEAD_PRINT = replace(HEAD, output_stem="gimbal_head_print")

def horn_pose(profile: HornProfile) -> Location:
    base, seat = BASE_CONFIGURATIONS[profile]
    return BASE_POSE * Location((*base.ring.center, base.plate_thickness - seat.arm_depth))


@dataclass(frozen=True)
class ConfiguredModel:
    name: str
    spec: PartSpec
    assembly_pose: Location
    build_default: Callable[[], Shape]
    fields: tuple[PreviewField, ...]
    build: Callable[[dict[str, float]], Shape]


MODELS = {
    "base-servo": ConfiguredModel(
        "舵盘槽底盘", BASE_SERVO, BASE_POSE, build_base_for_horn,
        base_servo.FIELDS, base_servo.build_preview,
    ),
    "servo-horn-long": ConfiguredModel(
        LONG_SERVO_HORN.source_label, LONG_SERVO_HORN, horn_pose(HornProfile.LONG),
        partial(build_servo_horn, LONG_HORN_PARAMETERS), servo_horn.fields_for_horn(LONG_HORN_PARAMETERS),
        partial(servo_horn.build_preview, horn=LONG_HORN_PARAMETERS),
    ),
    "servo-horn": ConfiguredModel(
        SERVO_HORN.source_label, SERVO_HORN, horn_pose(HornProfile.EQUAL), partial(build_servo_horn, SERVO_HORN_PARAMETERS),
        servo_horn.FIELDS, servo_horn.build_preview,
    ),
    "servo-horn-single": ConfiguredModel(
        UPPER_HORN.source_label, UPPER_HORN, upper_horn_pose(), build_single_horn, single_preview.FIELDS,
        single_preview.build_preview,
    ),
    "sg90s": ConfiguredModel(
        SERVO.source_label, SERVO, Location(), partial(build_servo, sg90s.SG90S), sg90s.FIELDS, sg90s.build_preview,
    ),
    "base": ConfiguredModel(
        "底座", BASE, BASE_POSE, partial(build_base, BASE_PARAMETERS), base.FIELDS, base.build_preview,
    ),
    "bracket": ConfiguredModel(
        "支架", BRACKET, BRACKET_POSE, partial(build_bracket, BRACKET_PARAMETERS),
        bracket.FIELDS, bracket.build_preview,
    ),
    "bracket-print": ConfiguredModel(
        "打印支架", BRACKET_PRINT, BRACKET_POSE, partial(build_print_bracket, BRACKET_PARAMETERS),
        bracket.FIELDS, bracket_print.build_preview,
    ),
    "head": ConfiguredModel(
        "云台头", HEAD, HEAD_POSE, partial(build_head, HEAD_PARAMETERS), head.FIELDS, head.build_preview,
    ),
    "head-print": ConfiguredModel(
        "打印云台头", HEAD_PRINT, HEAD_POSE, partial(build_print_head, HEAD_PARAMETERS),
        head.FIELDS, head_print.build_preview,
    ),
}
