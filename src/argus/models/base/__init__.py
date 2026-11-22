"""Gimbal base, including its plate and symmetric hole patterns."""

from dataclasses import dataclass
from math import sqrt

from build123d import GeomType, Plane, Solid

from argus.models.common import FEATURE_EPSILON, X, Z, Outline, Prism, box_at, cylinder


Point2D = tuple[float, float]


@dataclass(frozen=True)
class Counterbore:
    radius: float
    depth: float
    taper_radius: float
    taper_depth: float


@dataclass(frozen=True)
class MountingHole:
    x: float
    y: float
    radius: float
    counterbore: Counterbore | None = None


@dataclass(frozen=True)
class QuarterTurnHolePattern:
    offset: Point2D
    radius: float
    counterbore: Counterbore | None = None

    def holes(self, center: Point2D) -> tuple[MountingHole, ...]:
        center_x, center_y = center
        dx, dy = self.offset
        return tuple(
            MountingHole(center_x + x, center_y + y, self.radius, self.counterbore)
            for x, y in ((dx, dy), (-dy, dx), (-dx, -dy), (dy, -dx))
        )


@dataclass(frozen=True)
class RingParameters:
    center: Point2D
    outer_radius: float
    inner_radius: float
    height: float
    root_fillet: float | None
    slot_y_offset: float
    slot_height: float
    slot_radius: float


@dataclass(frozen=True)
class BaseParameters:
    ring: RingParameters
    plate_side: float
    plate_thickness: float
    plate_corner_radius: float
    corner_holes: QuarterTurnHolePattern
    inner_holes: QuarterTurnHolePattern


def rounded_square_plate(
    *, side: float, thickness: float, radius: float, center: Point2D,
) -> Prism:
    center_x, center_y = center
    half_side = side / 2
    left, right = center_x - half_side, center_x + half_side
    low, high = center_y - half_side, center_y + half_side
    inset = radius * (1 - 1 / sqrt(2))
    return Prism(
        outline=Outline(
            vertices=(
                (right - radius, low, 0), (left + radius, low, 0),
                (left, low + radius, 0), (left, high - radius, 0),
                (left + radius, high, 0), (right - radius, high, 0),
                (right, high - radius, 0), (right, low + radius, 0),
            ),
            arcs=(
                (1, (left + inset, low + inset, 0)),
                (3, (left + inset, high - inset, 0)),
                (5, (right - inset, high - inset, 0)),
                (7, (right - inset, low + inset, 0)),
            ),
        ),
        direction=(0, 0, thickness),
    )


def build_base(parameters: BaseParameters):
    center = parameters.ring.center
    plate = rounded_square_plate(
        side=parameters.plate_side, thickness=parameters.plate_thickness,
        radius=parameters.plate_corner_radius, center=center,
    )
    holes = parameters.corner_holes.holes(center) + parameters.inner_holes.holes(center)
    return build_base_features(plate, parameters.ring, holes)


def build_base_features(plate_profile: Prism, ring: RingParameters, holes: tuple[MountingHole, ...]):
    """Build a base from its resolved plate profile, ring and individual holes."""
    plate = plate_profile.build()
    thickness = plate_profile.direction[2]
    plate_top = plate.bounding_box().max.Z
    plate_bottom = plate_top - thickness
    ring_x, ring_y = ring.center
    ring_origin = (ring_x, ring_y, plate_top)
    ring_wall = cylinder(ring.outer_radius, ring_origin, Z, ring.height)
    ring_wall -= cylinder(ring.inner_radius, ring_origin, Z, ring.height)
    part = plate + ring_wall
    if ring.root_fillet is not None:
        edges = [
            edge for edge in part.edges()
            if edge.geom_type == GeomType.CIRCLE
            and abs(edge.radius - ring.outer_radius) < FEATURE_EPSILON
            and abs(edge.center().Z - plate_top) < FEATURE_EPSILON
        ]
        part = part.fillet(ring.root_fillet, edges)

    bounds = part.bounding_box()
    x0, width = bounds.min.X - 1, bounds.size.X + 2
    y = ring_y + ring.slot_y_offset
    z = plate_top + ring.slot_height
    radius = ring.slot_radius
    rounded = cylinder(radius, (x0, y, z), X, width)
    opening = box_at((x0, y - radius, z), (width, 2 * radius, bounds.max.Z - z + 1))
    part -= rounded + opening

    for hole in holes:
        start = (hole.x, hole.y, plate_bottom - 1)
        part -= cylinder(hole.radius, start, Z, thickness + 2)
        if hole.counterbore is not None:
            cb = hole.counterbore
            part -= cylinder(cb.radius, start, Z, cb.depth + 1)
            part -= Solid.make_cone(
                cb.radius, cb.taper_radius, cb.taper_depth,
                Plane((hole.x, hole.y, plate_bottom + cb.depth)),
            )
    return part
