"""Outboard horn pocket, locating bore and distal hole for the right bracket arm."""

from dataclasses import dataclass
from math import cos, radians, sin

from build123d import Face, Location, Plane, Pos, Solid

from argus.models.common import X, cylinder
from argus.models.servo_horn.single import SINGLE_HORN, SingleHornParameters, outline


@dataclass(frozen=True)
class HornSeat:
    horn: SingleHornParameters = SINGLE_HORN
    side_clearance: float = 0.2
    seat_offset: float = 0.2
    lip_height: float = 0.22
    rim: float = 1.0
    arm_angle: float = 20.0
    fastener_diameter: float = 1.65

    @property
    def pocket_depth(self) -> float:
        return self.horn.arm_thickness + self.lip_height

    def frame(self, x: float, axis: tuple[float, float]) -> Location:
        angle = radians(self.arm_angle)
        return Plane((x, *axis), x_dir=(0, -sin(angle), cos(angle)), z_dir=(-1, 0, 0)).location

    def horn_pose(self, outer_arm: float, axis: tuple[float, float]) -> Location:
        return self.frame(outer_arm + self.seat_offset + self.horn.arm_thickness, axis)

    def features(self, arm_face: float, thickness: float, axis: tuple[float, float]):
        top = arm_face + self.seat_offset + self.pocket_depth
        profile_frame = self.frame(top, axis)
        pad = Solid.extrude(Face(outline(self.horn, self.side_clearance + self.rim)), (0, 0, top - arm_face + 0.15))
        pocket = Solid.extrude(Face(outline(self.horn, self.side_clearance)).moved(Pos(0, 0, -1)), (0, 0, self.pocket_depth + 1))
        drill_start = arm_face - thickness - 1
        drill_depth = top + 1 - drill_start
        mounting = (self.frame(drill_start, axis) * Pos(self.horn.arm_holes()[-2], 0, 0)).position
        bores = (
            cylinder(self.horn.hub_diameter / 2 + self.side_clearance, (drill_start, *axis), X, drill_depth),
            cylinder(self.fastener_diameter / 2, mounting, X, drill_depth),
        )
        return pad.moved(profile_frame), (pocket.moved(profile_frame), *bores)
