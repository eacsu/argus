"""Geometry primitives shared by the gimbal models."""

from dataclasses import dataclass

from build123d import Align, Box, Edge, Face, Plane, Pos, Solid, Vector, Wire


Point = tuple[float, float, float]
X, Y, Z = Vector(1, 0, 0), Vector(0, 1, 0), Vector(0, 0, 1)
FEATURE_EPSILON = 1e-5


@dataclass(frozen=True)
class Outline:
    vertices: tuple[Point, ...]
    arcs: tuple[tuple[int, Point], ...] = ()

    def wire(self) -> Wire:
        midpoints = dict(self.arcs)
        edges = []
        for index, start in enumerate(self.vertices):
            end = self.vertices[(index + 1) % len(self.vertices)]
            if index in midpoints:
                edges.append(Edge.make_three_point_arc(start, midpoints[index], end))
            else:
                edges.append(Edge.make_line(start, end))
        return Wire(edges)


@dataclass(frozen=True)
class Circle:
    radius: float
    center: Point
    x_dir: Point
    normal: Point

    def wire(self) -> Wire:
        return Wire(Edge.make_circle(self.radius, Plane(self.center, x_dir=self.x_dir, z_dir=self.normal)))


@dataclass(frozen=True)
class Prism:
    outline: Outline | Circle
    direction: Point
    holes: tuple[Outline | Circle, ...] = ()

    def build(self) -> Solid:
        return Solid.extrude(Face(self.outline.wire(), [hole.wire() for hole in self.holes]), self.direction)


@dataclass(frozen=True)
class RoundCut:
    minimum: Point
    maximum: Point
    axis_center: Point
    radius: float

    def build(self):
        minimum, maximum = Vector(self.minimum), Vector(self.maximum)
        quadrant = box_at(minimum - X, maximum - minimum + X * 2)
        start_x = minimum.X - 1
        _, center_y, center_z = self.axis_center
        rounded = cylinder(self.radius, (start_x, center_y, center_z), X, maximum.X - start_x + 1)
        return quadrant - rounded


def cylinder(radius, origin, direction, height):
    return Solid.make_cylinder(radius, height, Plane(origin=origin, z_dir=direction))


def box_at(origin, size):
    return Pos(*origin) * Box(*size, align=(Align.MIN,) * 3)
