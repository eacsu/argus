"""Parametric servo envelope, mounting lugs and output spline."""

from dataclasses import dataclass

from build123d import Face, Pos, Solid

from argus.models.common import Z, box_at, cylinder
from argus.models.servo_horn import SplineSocket


@dataclass(frozen=True)
class ServoParameters:
    body_length: float
    body_width: float
    body_height: float
    ear_span: float
    ear_pitch: float
    ear_height: float
    ear_thickness: float
    mounting_hole: float
    shaft_x: float
    cover_height: float
    output_height: float
    screw_hole: float
    spline: SplineSocket

    @property
    def shoulder_height(self) -> float:
        return self.body_height + self.cover_height

    @property
    def tip_height(self) -> float:
        return self.shoulder_height + self.output_height


def build_servo(parameters: ServoParameters):
    p = parameters
    half_x, half_y = p.body_length / 2, p.body_width / 2
    part = box_at((-half_x, -half_y, 0), (p.body_length, p.body_width, p.body_height))
    ears = box_at((-p.ear_span / 2, -half_y, p.ear_height), (p.ear_span, p.body_width, p.ear_thickness))
    for x in (-p.ear_pitch / 2, p.ear_pitch / 2):
        ears -= cylinder(p.mounting_hole / 2, (x, 0, p.ear_height - 1), Z, p.ear_thickness + 2)
    part += ears

    # The two lobes reproduce the gear-cover envelope and the output-axis datum.
    small_lobe = 2.5
    drive_x = p.shaft_x
    idler_x = 1.5
    part += cylinder(half_y, (drive_x, 0, p.body_height), Z, p.cover_height)
    part += box_at((drive_x, -small_lobe, p.body_height), (idler_x - drive_x, 2 * small_lobe, p.cover_height - 0.3))
    part += cylinder(small_lobe, (idler_x, 0, p.body_height), Z, p.cover_height - 0.3)

    shaft = Solid.extrude(Face(p.spline.outline(p.shoulder_height).wire()), (0, 0, p.output_height))
    part += Pos(drive_x, 0, 0) * shaft
    part -= cylinder(p.screw_hole / 2, (drive_x, 0, p.body_height + 2.05), Z, p.tip_height - p.body_height + 1)
    return part
