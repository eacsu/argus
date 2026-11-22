"""Parametric CAD reconstruction of the three gimbal components (mm)."""
from pathlib import Path

from build123d import (
    Align, Box, Cone, Cylinder, Edge, Face, Location, Mesher, Plane, Pos,
    RectangleRounded, Rot, Solid, Wire, export_step, extrude, import_step,
)

ROOT = Path(__file__).resolve().parents[1]
MIN = Align.MIN
CENTER = Align.CENTER


def block(x, y, z, dx, dy, dz):
    return Pos(x, y, z) * Box(dx, dy, dz, align=(MIN, MIN, MIN))


def cylinder(radius, length, origin, direction=(0, 0, 1)):
    return Solid.make_cylinder(radius, length, Plane(origin=origin, z_dir=direction))


def profile(points, direction, arcs=None):
    """Extrude a closed sketch. Arcs map a segment index to its midpoint."""
    arcs = arcs or {}
    edges = []
    for index, start in enumerate(points):
        end = points[(index + 1) % len(points)]
        if index in arcs:
            edges.append(Edge.make_three_point_arc(start, arcs[index], end))
        else:
            edges.append(Edge.make_line(start, end))
    return Solid.extrude(Face(Wire(edges)), direction)


def build_base(
    plate_width=33.0, plate_thickness=3.5, corner_radius=1.0,
    ring_radius=12.0, ring_wall=1.0, ring_height=9.0, ring_offset=-2.5,
    ring_gap=6.0, corner_hole_pitch=30.0, corner_hole_radius=1.25,
    inner_hole_pitch=9.0, inner_hole_radius=1.0,
):
    plate = extrude(RectangleRounded(plate_width, plate_width, corner_radius), plate_thickness)
    ring_origin = (0, ring_offset, plate_thickness - 0.1)
    ring = cylinder(ring_radius, ring_height + 0.1, ring_origin)
    ring -= cylinder(ring_radius - ring_wall, ring_height + 0.2, ring_origin)
    # Two open sides of the retaining ring.
    ring -= block(-ring_radius - 1, ring_offset - ring_gap / 2, plate_thickness - 0.05,
                  2 * ring_radius + 2, ring_gap, ring_height + 1)
    part = plate + ring
    half_pitch = corner_hole_pitch / 2
    for x in (-half_pitch, half_pitch):
        for y in (-half_pitch, half_pitch):
            part -= cylinder(corner_hole_radius, plate_thickness + 2, (x, y, -1))
    for x, y in [(inner_hole_pitch, 0), (-inner_hole_pitch, 0),
                 (0, inner_hole_pitch), (0, -inner_hole_pitch)]:
        center = (x, y + ring_offset, 0)
        part -= cylinder(inner_hole_radius, plate_thickness + 1, center)
        part -= cylinder(inner_hole_radius + 0.5, 0.6, center)
        part -= Pos(x, y + ring_offset, 0.6) * Cone(
            inner_hole_radius + 0.5, inner_hole_radius, 0.3, align=(CENTER, CENTER, MIN)
        )
    return part


def build_bracket(
    frame_length=36.0, mounting_width=22.0, plate_depth=10.0,
    window_width=14.0, window_length=23.0, arm_inner_x=15.5,
    arm_thickness=2.5, pivot_y=31.0558413, pivot_z=-40.0,
    pivot_radius=2.0, collar_radius=4.0, collar_height=2.0, collar_wall=0.2,
):
    half_width = mounting_width / 2
    root_y = 12.5
    shoulder = arm_inner_x + arm_thickness
    frame_outline = [
        (-half_width, 0), (half_width, 0), (half_width, 7.5),
        (shoulder - 5, 7.5), (shoulder, root_y),
        (arm_inner_x, 13.536), (11.964, plate_depth),
        (-11.964, plate_depth), (-arm_inner_x, 13.536),
        (-shoulder, root_y), (-shoulder + 5, 7.5), (-half_width, 7.5),
    ]
    frame = profile([(x, y, -frame_length) for x, y in frame_outline],
                    (0, 0, frame_length))
    # Round the two edges at the mounting face ends.
    front_edges = [e for e in frame.edges()
                   if abs(e.center().Y) < 1e-6 and abs(e.length - mounting_width) < 1e-6]
    frame = frame.fillet(2.0, front_edges)
    frame -= block(-window_width / 2, -1, -(frame_length + window_length) / 2,
                   window_width, plate_depth + 2, window_length)
    for x in (-shoulder, arm_inner_x):
        dy, dz = pivot_y - 31.0558413, pivot_z + 40
        outline = [(root_y, -frame_length), (root_y, -0.268), (13.1, -0.8),
                   (30.365 + dy, -23.82 + dz), (30.592 + dy, -24.206 + dz),
                   (36.537 + dy, -37.560 + dz), (26.467 + dy, -43.865 + dz),
                   (19.843, -frame_length)]
        arm = profile([(x, y, z) for y, z in outline], (arm_thickness, 0, 0), {
            1: (x, 12.827, -0.504), 3: (x, 30.489 + dy, -24.006 + dz),
            5: (x, 34.240 + dy, -45.085 + dz),
        })
        start = x - 0.1
        opening = [(14.5, -15.667), (16.3, -15.067), (23.3, -24.4),
                   (23.5, -25), (23.5, -29), (22.5, -30), (15.5, -30), (14.5, -29)]
        arm -= profile([(start, y, z) for y, z in opening], (arm_thickness + 0.2, 0, 0), {
            0: (start, 15.184, -14.718), 2: (start, 23.449, -24.684),
            4: (start, 23.207, -29.707), 6: (start, 14.793, -29.707),
        })
        if x < 0:
            arm += cylinder(pivot_radius, collar_height + 0.1, (x - collar_height, pivot_y, pivot_z), (1, 0, 0))
        else:
            arm -= cylinder(2.65, arm_thickness + 0.2, (start, pivot_y, pivot_z), (1, 0, 0))
            arm -= cylinder(1.0, arm_thickness + 0.2, (start, 25.960, -26), (1, 0, 0))
            outside = x + arm_thickness - 0.01
            def collar_profile(inset):
                points = [(34.597 - 0.885 * inset, -38.14 - 0.465 * inset),
                          (27.147 + 0.977 * inset, -40.851 + 0.213 * inset),
                          (24.006 + 0.977 * inset, -26.426 + 0.213 * inset),
                          (27.731 - 0.885 * inset, -25.070 - 0.465 * inset)]
                return profile(
                    [(outside, y + dy, z + dz) for y, z in points],
                    (collar_height + 0.01, 0, 0),
                    {0: (outside, pivot_y + 0.342 * (collar_radius - inset),
                         pivot_z - 0.940 * (collar_radius - inset)),
                     2: (outside, 25.276 + dy + 0.342 * inset, -24.121 + dz - 0.940 * inset)},
                )
            arm += collar_profile(0) - collar_profile(collar_wall)
        frame += arm
    for x in (-half_width - 2, half_width):
        for z in (-10, -30):
            frame += block(x, 5.5, z, 2, 2.01, 1)
    return frame


def build_head(
    plate_thickness=2.0, half_width=20.0, lower_z=-19.3, lower_radius=6.0,
    clip_height=15.4, clip_reach=14.5, pivot_hole_radius=2.0,
    small_hole_radius=1.0,
):
    side = half_width
    tangent = side - lower_radius
    shoulder = lower_z + lower_radius
    diagonal = lower_radius / 2**0.5
    outline = [(side, 10.2), (15, 10.2), (15, 19.3), (12, 19.3),
               (12, 15), (7.4, 15), (7.4, 19.3), (-15, 19.3),
               (-15, 10.2), (-side, 10.2), (-side, shoulder),
               (-tangent, lower_z), (tangent, lower_z), (side, shoulder)]
    plate = profile([(x, 0, z) for x, z in outline], (0, plate_thickness, 0), {
        10: (-tangent - diagonal, 0, shoulder - diagonal),
        12: (tangent + diagonal, 0, shoulder - diagonal),
    })
    clip_z = -2 - clip_height / 2
    for shift, sign in ((18, 1), (-20, -1)):
        x_min = shift - 7 if sign > 0 else shift
        plate -= block(x_min, 0.6, clip_z, 7, plate_thickness, clip_height)
        plate -= block(11 if sign > 0 else -17, -0.1, clip_z, 4, 0.8, clip_height)
    for outline_xy in [
        [(15, 0), (18, 0), (18, plate_thickness), (17, 3), (17, clip_reach),
         (16.5, clip_reach), (14.5, clip_reach - 3), (15, clip_reach - 3)],
        [(-17, 0), (-20, 0), (-20, plate_thickness), (-19, 3), (-19, clip_reach),
         (-18.5, clip_reach), (-16.5, clip_reach - 3), (-17, clip_reach - 3)],
    ]:
        plate += profile([(x, y, clip_z) for x, y in outline_xy], (0, 0, clip_height))

    def lug(x, width, outline_yz, arcs, hole_y, hole_z, radius):
        body = profile([(x, y, z) for y, z in outline_yz], (width, 0, 0),
                       {i: (x, y, z) for i, (y, z) in arcs.items()})
        return body - cylinder(radius, width + 0.2, (x - 0.1, hole_y, hole_z), (1, 0, 0))

    plate += lug(side - 2, 2, [(0.1, 10.2), (-3.875, 12.59), (-9.125, 4.08), (0.1, -1.55)],
                 {1: (-10.755, 10.96)}, -6, 7.65, pivot_hole_radius)
    plate += lug(-4.9, 1.5, [(-9, 15.5), (-9, 19.5), (-1, 19.5), (0.1, 18.5),
                             (0.1, 14.5), (-8, 14.5)],
                 {2: (-0.293, 19.207), 5: (-8.707, 14.793)}, -6, 15.9, small_hole_radius)
    plate += lug(-5, 2, [(0.1, -16.3), (0.1, -9.3), (-6, -9.3), (-6.84, -12.692)],
                 {2: (-7.747, -10.667)}, -6, -11.1, small_hole_radius)
    plate += block(-7.5, plate_thickness - 0.1, -18.3, 15, 2.6, 2)
    plate += block(-8, plate_thickness - 0.1, 13.3, 6.5, 2.6, 2)
    # Mirrored spring catches beside the upper opening.
    catch_outline = [(4.9, 1.99), (7.4, 1.99), (7.918, 4.939),
                     (8.038, 5.089), (8.54, 5.3), (7.557, 5.966),
                     (7.444, 6), (6.444, 6), (5.46, 5.174)]
    catch_arcs = {2: (7.959, 5.029), 5: (7.503, 5.991), 7: (5.802, 5.766)}
    for reflected in (False, True):
        def catch_point(point):
            x, y = point
            return (19.4 - x if reflected else x, y + plate_thickness - 2, 15)

        plate += profile([catch_point(point) for point in catch_outline], (0, 0, 2),
                         {index: catch_point(point) for index, point in catch_arcs.items()})
    return plate


PARTS = (
    ("gimbal_bracket", build_bracket, (-1.7741354, -15.5529078, 22.985016),
     (0, -2.7780463, 0), (90, 0, 0)),
    ("gimbal_base", build_base, (-1.6259297, -34.7529078, 7.7945294),
     (-90, 0, 10.8302388), (0, 0, 0)),
    ("gimbal_head", build_head, (0.3733153, 24.2189281, -21.2703414),
     (101.7955913, 0.5683171, -177.2806619), (0, 90, 0)),
)


def export_parts():
    output = ROOT / "model-bin" / "parametric-parts"
    output.mkdir(parents=True, exist_ok=True)
    for name, build, position, rotation, print_rotation in PARTS:
        part = build()
        part.label = name
        if len(part.solids()) != 1 or not part.is_valid:
            raise RuntimeError(f"{name}: expected a single valid solid, got {len(part.solids())}")
        step_file = output / f"{name}.step"
        export_step(part.moved(Location(position, rotation)), step_file)
        reread = import_step(step_file)
        if not reread.is_valid or abs(reread.volume - part.volume) > 0.01:
            raise RuntimeError(f"{name}: STEP verification failed")
        printable = Rot(*print_rotation) * part
        bounds = printable.bounding_box()
        center = bounds.center()
        printable = Pos(-center.X, -center.Y, -bounds.min.Z) * printable
        mesher = Mesher()
        mesher.add_shape(printable, linear_deflection=0.01)
        path = output / f"{name}.3mf"
        mesher.write(path)
        meshes = Mesher().read(path)
        if len(meshes) != 1 or abs(meshes[0].bounding_box().min.Z) > 0.02:
            raise RuntimeError(f"{name}: 3MF verification failed")
        print(name, round(part.volume, 2), tuple(round(x, 3) for x in part.bounding_box().size))


if __name__ == "__main__":
    export_parts()


