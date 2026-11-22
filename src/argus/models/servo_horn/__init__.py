"""Parametric four-arm servo horn and its socket for the output shaft."""

from dataclasses import dataclass
from math import cos, radians, sin, sqrt

from build123d import Face, Solid

from argus.models.common import Z, Outline, Prism, cylinder


@dataclass(frozen=True)
class HornArm:
    span: float
    tip_width: float
    hole_offsets: tuple[float, ...]


@dataclass(frozen=True)
class HornEnvelope:
    main_arm: HornArm
    hub_diameter: float
    arm_thickness: float
    overall_height: float
    short_arm: HornArm | None = None

    def arms(self) -> tuple[HornArm, ...]:
        along_x = self.short_arm or self.main_arm
        return along_x, self.main_arm, along_x, self.main_arm


ARM_DIRECTIONS = ((1, 0), (0, 1), (-1, 0), (0, -1))


@dataclass(frozen=True)
class SplineSocket:
    teeth: int
    major_diameter: float
    minor_diameter: float
    tip_angle: float
    phase: float
    depth: float
    clearance: float

    def outline(self, z: float) -> Outline:
        """Repeat the measured profile of one output tooth around the axis."""
        pitch = 360 / self.teeth
        major_radius, minor_radius = self.major_diameter / 2, self.minor_diameter / 2
        half_tip = self.tip_angle / 2

        def point(radius: float, angle: float) -> tuple[float, float, float]:
            theta = radians(angle)
            return radius * cos(theta), radius * sin(theta), z

        vertices, arcs = [], []
        for index in range(self.teeth):
            angle = self.phase + index * pitch
            arcs.append((len(vertices) + 1, point(major_radius, angle)))
            vertices.extend((
                point(minor_radius, angle - pitch / 2),
                point(major_radius, angle - half_tip),
                point(major_radius, angle + half_tip),
            ))
        return Outline(tuple(vertices), tuple(arcs))

    def cutter(self, top: float) -> Solid:
        wire = self.outline(top - self.depth).wire()
        if self.clearance:
            wire = wire.offset_2d(self.clearance)
        return Solid.extrude(Face(wire), (0, 0, self.depth + 1))


@dataclass(frozen=True)
class ServoHornParameters:
    envelope: HornEnvelope
    socket: SplineSocket
    arm_hole_diameter: float
    center_hole_diameter: float


def horn_outline(
    horn: HornEnvelope, center: tuple[float, float], z: float, *, clearance: float = 0,
) -> Outline:
    """Draw the opposite pairs of arms around the same shaft and shoulder."""
    root = horn.hub_diameter / 2 + clearance
    blend = 1.0
    shoulder = root + blend
    arc_mid = shoulder - blend / sqrt(2)
    vertices, arcs = [], []
    for arm, (dx, dy) in zip(horn.arms(), ARM_DIRECTIONS):
        tip_x = (arm.span - arm.tip_width) / 2
        tip_radius = arm.tip_width / 2 + clearance
        points = (
            (tip_x, -tip_radius), (tip_x, tip_radius), (shoulder, root), (root, shoulder),
            (tip_x + tip_radius, 0.0), (arc_mid, arc_mid),
        )
        *corners, tip_arc, root_arc = [
            (center[0] + dx * x - dy * y, center[1] + dy * x + dx * y, z) for x, y in points
        ]
        start = len(vertices)
        vertices.extend(corners)
        arcs.extend(((start, tip_arc), (start + 2, root_arc)))
    return Outline(tuple(vertices), tuple(arcs))


def build_servo_horn(parameters: ServoHornParameters) -> Solid:
    horn = parameters.envelope
    arm_plate = Prism(horn_outline(horn, (0.0, 0.0), 0.0), (0, 0, horn.arm_thickness)).build()
    hub = cylinder(horn.hub_diameter / 2, (0, 0, 0), Z, horn.overall_height)
    part = arm_plate + hub
    for arm, (dx, dy) in zip(horn.arms(), ARM_DIRECTIONS):
        for offset in arm.hole_offsets:
            part -= cylinder(
                parameters.arm_hole_diameter / 2, (dx * offset, dy * offset, -1), Z, horn.arm_thickness + 2,
            )
    part -= parameters.socket.cutter(horn.overall_height)
    part -= cylinder(parameters.center_hole_diameter / 2, (0, 0, -1), Z, horn.overall_height + 2)
    return part
