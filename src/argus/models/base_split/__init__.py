"""Two-piece base that captures the horn at the mating plane."""

from dataclasses import dataclass
from enum import StrEnum

from build123d import Part, Plane, Solid

from argus.models.base import MountingHole, rounded_square_plate
from argus.models.base_split.snap import SnapFit
from argus.models.common import Z, Prism, cylinder
from argus.models.servo_horn import HornEnvelope, horn_outline


class BaseConnection(StrEnum):
    SNAP = "snap"
    M3 = "m3"


DEFAULT_BASE_CONNECTION = BaseConnection.SNAP


@dataclass(frozen=True)
class BaseFasteners:
    bolt_length: float = 6.0
    shank_diameter: float = 3.0
    clearance_diameter: float = 3.4
    head_diameter: float = 5.5
    head_height: float = 3.0
    recess_diameter: float = 6.3
    recess_depth: float = 3.3
    insert_diameter: float = 4.2
    insert_length: float = 3.0
    pilot_diameter: float = 4.0
    pilot_depth: float = 4.2
    boss_diameter: float = 7.2
    boss_height: float = 5.4

    def thread_reach(self, lower_thickness: float) -> float:
        return self.bolt_length + self.recess_depth - lower_thickness


@dataclass(frozen=True)
class SplitBaseParameters:
    center: tuple[float, float]
    plate_side: float
    corner_radius: float
    corner_holes: tuple[MountingHole, ...]
    lower_thickness: float
    cover_thickness: float
    horn: HornEnvelope
    side_clearance: float
    axial_clearance: float
    tool_diameter: float
    fasteners: BaseFasteners
    connection: BaseConnection = DEFAULT_BASE_CONNECTION
    snap_fit: SnapFit = SnapFit()

    @property
    def seat_height(self) -> float:
        return self.lower_thickness - self.horn.arm_thickness - self.axial_clearance

    def bolt_centers(self) -> tuple[tuple[float, float], ...]:
        x, y = self.center
        return tuple((x + dx, y + dy) for dx in (-15.5, 15.5) for dy in (-9.0, 9.0))


def build_lower(parameters: SplitBaseParameters) -> Part:
    thickness, bolts = parameters.lower_thickness, parameters.fasteners
    lower = rounded_square_plate(
        side=parameters.plate_side, thickness=thickness, radius=parameters.corner_radius, center=parameters.center,
    ).build()
    for hole in parameters.corner_holes:
        lower -= cylinder(hole.radius, (hole.x, hole.y, -1), Z, thickness + 2)
    if parameters.connection == BaseConnection.M3:
        for x, y in parameters.bolt_centers():
            lower -= cylinder(bolts.clearance_diameter / 2, (x, y, -1), Z, thickness + 2)
            lower -= cylinder(bolts.recess_diameter / 2, (x, y, -1), Z, bolts.recess_depth + 1)
    else:
        lower = parameters.snap_fit.lower(lower, parameters.center, parameters.plate_side, thickness)

    seat = parameters.seat_height
    lower -= Prism(
        horn_outline(parameters.horn, parameters.center, seat, clearance=parameters.side_clearance),
        (0, 0, thickness - seat + 1),
    ).build()
    lower -= cylinder(parameters.tool_diameter / 2, (*parameters.center, -1), Z, thickness + 2)
    return lower


def build_upper(parameters: SplitBaseParameters) -> Part:
    thickness, bolts = parameters.cover_thickness, parameters.fasteners
    upper = rounded_square_plate(
        side=parameters.plate_side, thickness=thickness, radius=parameters.corner_radius, center=parameters.center,
    ).build()
    if parameters.connection == BaseConnection.M3:
        for x, y in parameters.bolt_centers():
            upper += cylinder(bolts.boss_diameter / 2, (x, y, 0), Z, bolts.boss_height)
            upper -= cylinder(bolts.pilot_diameter / 2, (x, y, -1), Z, bolts.pilot_depth + 1)
            upper -= Solid.make_cone(bolts.insert_diameter / 2 + 0.1, bolts.pilot_diameter / 2, 0.35, Plane((x, y, 0)))
    else:
        upper = parameters.snap_fit.upper(upper, parameters.center, parameters.plate_side, thickness)
    for hole in parameters.corner_holes:
        upper -= cylinder(hole.radius, (hole.x, hole.y, -1), Z, thickness + 2)
    upper -= cylinder(parameters.horn.hub_diameter / 2 + parameters.side_clearance, (*parameters.center, -1), Z, thickness + 2)
    return upper


def build_bolt(parameters: BaseFasteners):
    head = cylinder(parameters.head_diameter / 2, (0, 0, 0), Z, parameters.head_height)
    shank = cylinder(parameters.shank_diameter / 2, (0, 0, parameters.head_height), Z, parameters.bolt_length)
    return head + shank


def build_insert(parameters: BaseFasteners):
    outer = cylinder(parameters.insert_diameter / 2, (0, 0, 0), Z, parameters.insert_length)
    return outer - cylinder(parameters.shank_diameter / 2, (0, 0, -1), Z, parameters.insert_length + 2)
