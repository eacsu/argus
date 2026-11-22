"""Single-arm horn and the shared envelope used by its bracket seat."""

from dataclasses import dataclass, replace
from math import sqrt

from build123d import Face, Solid, Wire

from argus.models.common import Z, Outline, cylinder
from argus.models.servo_horn import SplineSocket
from argus.models.servo_horn.parameters import SERVO_HORN_PARAMETERS


@dataclass(frozen=True)
class SingleHornParameters:
    length: float
    hub_diameter: float
    overall_height: float
    arm_thickness: float
    tip_width: float
    arm_hole_diameter: float
    center_hole_diameter: float
    last_hole_pitch: float
    first_hole: float
    last_hole: float
    socket: SplineSocket

    @property
    def reach(self) -> float:
        return self.length - self.hub_diameter / 2

    def arm_holes(self) -> tuple[float, ...]:
        penultimate = self.last_hole - self.last_hole_pitch
        return tuple(self.first_hole + index * (penultimate - self.first_hole) / 5 for index in range(6)) + (self.last_hole,)


SINGLE_HORN = SingleHornParameters(
    length=21.3,
    hub_diameter=6.76,
    overall_height=4.82,
    arm_thickness=2.08,
    tip_width=4.0,
    arm_hole_diameter=1.45,
    center_hole_diameter=2.36,
    last_hole_pitch=2.43,
    first_hole=5.4,
    last_hole=16.2,
    socket=replace(SERVO_HORN_PARAMETERS.socket, major_diameter=4.54, minor_diameter=3.84, depth=3.45),
)


def outline(horn: SingleHornParameters, clearance: float = 0) -> Wire:
    hub = horn.hub_diameter / 2 + clearance
    tip_radius = horn.tip_width / 2 + clearance
    tip = horn.reach - horn.tip_width / 2
    normal_x = (hub - tip_radius) / tip
    normal_y = sqrt(1 - normal_x * normal_x)
    shoulder_x, shoulder_y = hub * normal_x, hub * normal_y
    tip_x, tip_y = tip + tip_radius * normal_x, tip_radius * normal_y
    return Outline(
        ((shoulder_x, -shoulder_y, 0), (tip_x, -tip_y, 0), (tip_x, tip_y, 0), (shoulder_x, shoulder_y, 0)),
        ((1, (horn.reach + clearance, 0, 0)), (3, (-hub, 0, 0))),
    ).wire()


def build_single_horn(horn: SingleHornParameters = SINGLE_HORN):
    arm = Solid.extrude(Face(outline(horn)), (0, 0, horn.arm_thickness))
    part = arm + cylinder(
        horn.hub_diameter / 2, (0, 0, horn.arm_thickness), Z, horn.overall_height - horn.arm_thickness,
    )
    for offset in horn.arm_holes():
        part -= cylinder(horn.arm_hole_diameter / 2, (offset, 0, -1), Z, horn.arm_thickness + 2)
    part -= horn.socket.cutter(horn.overall_height)
    part -= cylinder(horn.center_hole_diameter / 2, (0, 0, -1), Z, horn.overall_height + 2)
    return part
