"""Available horn seats and their matching base dimensions."""

from dataclasses import replace
from enum import StrEnum

from argus.models.base.parameters import BASE_PARAMETERS
from argus.models.base_servo import HornParameters, build_servo_base
from argus.models.servo_horn.parameters import HORN_ENVELOPE, LONG_HORN_PARAMETERS


class HornProfile(StrEnum):
    LONG = "long"
    EQUAL = "equal"


DEFAULT_HORN_PROFILE = HornProfile.LONG
PROFILES = {
    1: (HornProfile.LONG, "长短臂舵盘"),
    0: (HornProfile.EQUAL, "等臂十字舵盘"),
}


HORN_PARAMETERS = HornParameters(
    envelope=HORN_ENVELOPE,
    mounting_hole_indices=(1, 1),
    fastener_diameter=1.4,
    center_hole_diameter=2.3,  # Drawing shows a 2.1 mm hole in the horn itself.
    clearance=0.2,
)

SERVO_BASE_PARAMETERS = replace(
    BASE_PARAMETERS,
    plate_side=42.0,
    plate_thickness=BASE_PARAMETERS.plate_thickness + HORN_PARAMETERS.arm_depth,
    ring=replace(BASE_PARAMETERS.ring, height=BASE_PARAMETERS.ring.height - HORN_PARAMETERS.arm_depth),
)

LONG_HORN_SEAT = HornParameters(
    envelope=LONG_HORN_PARAMETERS.envelope,
    mounting_hole_indices=(1, 5),
    fastener_diameter=1.6,
    center_hole_diameter=2.56,
    clearance=0.2,
)
LONG_SERVO_BASE_PARAMETERS = replace(
    SERVO_BASE_PARAMETERS,
    plate_thickness=6.2,
    ring=replace(BASE_PARAMETERS.ring, height=BASE_PARAMETERS.ring.height + BASE_PARAMETERS.plate_thickness - 6.2),
)

BASE_CONFIGURATIONS = {
    HornProfile.LONG: (LONG_SERVO_BASE_PARAMETERS, LONG_HORN_SEAT),
    HornProfile.EQUAL: (SERVO_BASE_PARAMETERS, HORN_PARAMETERS),
}


def build_base_for_horn(profile: HornProfile = DEFAULT_HORN_PROFILE):
    return build_servo_base(*BASE_CONFIGURATIONS[profile])
