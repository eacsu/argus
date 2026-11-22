"""A base with a keyed seat for a four-arm servo horn."""

from dataclasses import dataclass

from build123d import Solid

from argus.models.base import (
    BaseParameters, Counterbore, MountingHole, build_base_features, rounded_square_plate,
)
from argus.models.common import Z, Prism, cylinder
from argus.models.servo_horn import ARM_DIRECTIONS, HornEnvelope, horn_outline


@dataclass(frozen=True)
class HornParameters:
    envelope: HornEnvelope
    mounting_hole_indices: tuple[int, int]
    fastener_diameter: float
    center_hole_diameter: float
    clearance: float

    @property
    def arm_depth(self) -> float:
        return self.envelope.arm_thickness + self.clearance

    @property
    def hub_depth(self) -> float:
        return self.envelope.overall_height + self.clearance

    def mounting_offsets(self) -> tuple[tuple[float, float], ...]:
        return tuple(
            (dx * arm.hole_offsets[index], dy * arm.hole_offsets[index])
            for arm, (dx, dy), index in zip(self.envelope.arms(), ARM_DIRECTIONS, self.mounting_hole_indices * 2)
        )


def build_servo_base(base: BaseParameters, horn: HornParameters) -> Solid:
    center = base.ring.center
    plate = rounded_square_plate(
        side=base.plate_side, thickness=base.plate_thickness,
        radius=base.plate_corner_radius, center=center,
    )
    screw_radius = horn.fastener_diameter / 2
    counterbore = Counterbore(radius=1.5, depth=0.6, taper_radius=screw_radius, taper_depth=0.3)
    screws = tuple(
        MountingHole(center[0] + x, center[1] + y, screw_radius, counterbore)
        for x, y in horn.mounting_offsets()
    )
    part = build_base_features(
        plate, base.ring, base.corner_holes.holes(center) + screws,
        ring_slot_turns=(0, 1),
    )

    top = base.plate_thickness
    arm_floor = top - horn.arm_depth
    hub_floor = top - horn.hub_depth
    arm_cut = Prism(
        horn_outline(horn.envelope, center, arm_floor, clearance=horn.clearance),
        (0, 0, horn.arm_depth + base.ring.height + 1),
    )
    part -= arm_cut.build()
    part -= cylinder(horn.envelope.hub_diameter / 2 + horn.clearance, (*center, hub_floor), Z, top - hub_floor + 1)
    part -= cylinder(horn.center_hole_diameter / 2, (*center, -1), Z, top + 1)
    return part
