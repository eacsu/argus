"""Rebuild the three structural parts from the measured Argus STEP features."""

from dataclasses import dataclass

from build123d import Face, GeomType, Plane, Pos, Vertex, section

from argus.models.base import Counterbore, MountingHole, RingParameters, build_base_features
from argus.models.bracket import CUT_OVERLAP, BracketFeatures, build_bracket_features
from argus.models.common import FEATURE_EPSILON, X, Y, Z, Circle, Outline, Prism, RoundCut, cylinder
from argus.models.head import HeadParameters, build_head


DIMENSION_TOLERANCE = 0.05  # mm
VOLUME_TOLERANCE = 0.0005  # relative to the source volume


class FitError(ValueError):
    """The input geometry does not match the expected feature structure."""


@dataclass(frozen=True)
class FitDeviation:
    volume_ratio: float
    boundary_mm: float


def near(a, b):
    return abs(a - b) < FEATURE_EPSILON


def single(items, feature):
    matches = list(items)
    if len(matches) != 1:
        raise FitError(f"{feature}应匹配一处，实际匹配 {len(matches)} 处")
    return matches[0]


def flat_faces(shape, axis, sign=None):
    return [
        face for face in shape.faces()
        if face.geom_type == GeomType.PLANE
        and near(abs(face.normal_at().dot(axis)), 1)
        and (sign is None or face.normal_at().dot(axis) * sign > 0)
    ]


def cylinders(shape, axis):
    return [
        face for face in shape.faces()
        if face.geom_type == GeomType.CYLINDER
        and near(abs(face.axis_of_rotation.direction.dot(axis)), 1)
    ]


def measure_outline(wire):
    edges = wire.order_edges()
    if len(edges) == 1 and edges[0].geom_type == GeomType.CIRCLE and edges[0].is_closed:
        edge = edges[0]
        return Circle(
            edge.radius, tuple(edge.arc_center),
            tuple(edge.position_at(0) - edge.arc_center), tuple(edge.normal()),
        )
    vertices, arcs = [], []
    for index, edge in enumerate(edges):
        vertices.append(tuple(edge.position_at(0)))
        if edge.geom_type == GeomType.CIRCLE:
            arcs.append((index, tuple(edge.position_at(0.5))))
        elif edge.geom_type != GeomType.LINE:
            raise FitError(f"轮廓含有未支持的曲线 {edge.geom_type.name}")
    return Outline(tuple(vertices), tuple(arcs))


def measure_prism(face, direction, keep_holes=True):
    outer = measure_outline(face.outer_wire())
    holes = tuple(measure_outline(wire) for wire in face.inner_wires()) if keep_holes else ()
    return Prism(outer, tuple(direction), holes)


def polygon_prism(vertices, direction):
    return Prism(Outline(tuple(vertices)), tuple(direction))


def slice_face(shape, axis, depth, feature):
    return single(
        section(shape, section_by=Plane(origin=axis * depth, z_dir=axis)).faces(),
        feature,
    )


def measure_base(source) -> tuple[Prism, RingParameters, tuple[MountingHole, ...]]:
    bottom = max(flat_faces(source, Z, -1), key=lambda face: face.area)
    bottom_z = bottom.center().Z
    # The upper plate face reaches the same outside corners as the bottom.
    rim = bottom.bounding_box().size
    top = single(
        (face for face in flat_faces(source, Z, 1)
         if near(face.bounding_box().size.X, rim.X) and near(face.bounding_box().size.Y, rim.Y)),
        "底座板上表面",
    )
    top_z = top.center().Z
    plate = measure_prism(bottom, Z * (top_z - bottom_z), keep_holes=False)

    upright = cylinders(source, Z)
    ring_faces = [
        face for face in upright
        if face.bounding_box().max.Z > top_z + FEATURE_EPSILON
    ]
    outer = max(ring_faces, key=lambda face: face.radius)
    inner = min(ring_faces, key=lambda face: face.radius)
    center = outer.axis_of_rotation.position
    ring_center = (center.X, center.Y)
    ring_height = outer.bounding_box().max.Z - top_z
    blends = [face for face in source.faces() if face.geom_type == GeomType.TORUS]
    ring_root_fillet = blends[0].bounding_box().size.Z if blends else None

    slot_faces = cylinders(source, X)
    if len(slot_faces) != 2:
        raise FitError("底座圆底开槽应包含两侧圆柱面")
    slot = slot_faces[0]
    slot_center = slot.axis_of_rotation.position

    cones = [face for face in source.faces() if face.geom_type == GeomType.CONE]
    holes = []
    for wire in bottom.inner_wires():
        mouth = single(wire.edges(), "底座安装孔圆边")
        xy = mouth.arc_center
        coaxial = [
            face for face in upright
            if near(face.axis_of_rotation.position.X, xy.X)
            and near(face.axis_of_rotation.position.Y, xy.Y)
        ]
        bore = min(coaxial, key=lambda face: face.radius)
        counterbore = None
        if mouth.radius > bore.radius + FEATURE_EPSILON:
            cone = single(
                (face for face in cones if any(
                    edge.geom_type == GeomType.CIRCLE
                    and near(edge.arc_center.X, xy.X) and near(edge.arc_center.Y, xy.Y)
                    for edge in face.edges()
                )),
                "底座沉孔锥面",
            )
            rims = [edge for edge in cone.edges() if edge.geom_type == GeomType.CIRCLE]
            lower = min(rims, key=lambda edge: edge.arc_center.Z)
            upper = max(rims, key=lambda edge: edge.arc_center.Z)
            counterbore = Counterbore(
                mouth.radius, lower.arc_center.Z - bottom_z,
                upper.radius, upper.arc_center.Z - lower.arc_center.Z,
            )
        holes.append(MountingHole(xy.X, xy.Y, bore.radius, counterbore))
    ring = RingParameters(
        center=ring_center,
        outer_radius=outer.radius,
        inner_radius=inner.radius,
        height=ring_height,
        root_fillet=ring_root_fillet,
        slot_y_offset=slot_center.Y - center.Y,
        slot_height=slot_center.Z - top_z,
        slot_radius=slot.radius,
    )
    return plate, ring, tuple(holes)


def measure_round(surface) -> RoundCut:
    bounds = surface.bounding_box()
    return RoundCut(
        tuple(bounds.min), tuple(bounds.max),
        tuple(surface.axis_of_rotation.position), surface.radius,
    )


def measure_bracket(source) -> BracketFeatures:
    sides = flat_faces(source, X)
    front = max(flat_faces(source, Y, -1), key=lambda face: face.area)
    rear = max(flat_faces(source, Y, 1), key=lambda face: face.area)
    front_y, rear_y = front.center().Y, rear.center().Y
    window = Face(single(front.inner_wires(), "支架安装窗口"))
    window_bounds = window.bounding_box()
    mounting_sides = [
        face for face in sides if near(face.bounding_box().min.Y, front_y)
        and face.bounding_box().min.Z < window_bounds.min.Z - FEATURE_EPSILON
        and face.bounding_box().max.Z > window_bounds.max.Z + FEATURE_EPSILON
    ]
    left_mount, right_mount = sorted(mounting_sides, key=lambda face: face.center().X)
    bottom_z, top_z = left_mount.bounding_box().min.Z, left_mount.bounding_box().max.Z
    left_arm = max((face for face in sides if face.normal_at().X < 0), key=lambda face: face.area)
    left_inner = max((face for face in sides if face.normal_at().X > 0 and face.center().X < left_mount.center().X),
                     key=lambda face: face.area)
    right_arm = max((face for face in sides if face.normal_at().X > 0 and face.center().X > right_mount.center().X),
                    key=lambda face: face.area)
    right_inner = max((face for face in sides if face.normal_at().X < 0 and face.center().X > right_mount.center().X),
                      key=lambda face: face.area)
    left_x, left_inside = left_arm.center().X, left_inner.center().X
    right_x, right_inside = right_arm.center().X, right_inner.center().X

    frame_slice = slice_face(source, Z, (top_z + window_bounds.max.Z) / 2, "支架安装框截面")
    points = [edge.position_at(0) for edge in frame_slice.outer_wire().order_edges()]
    shoulders = (left_x, left_inside, right_inside, right_x)
    # Remove the four vertices that continue along the arms, closing the frame at its shoulders.
    arm_ends = [max((p.Y for p in points if near(p.X, x))) for x in shoulders]
    contour = [
        (point.X, point.Y, bottom_z) for point in points
        if not any(near(point.X, x) and near(point.Y, y) for x, y in zip(shoulders, arm_ends))
    ]
    frame = polygon_prism(contour, Z * (top_z - bottom_z))
    window_cut = measure_prism(window, Y * (rear_y - front_y))

    # The four tabs each have a triangular end on the front slope.
    tabs = [
        face for face in flat_faces(source, Z)
        if len(face.outer_wire().edges()) == 3 and len(face.wires()) == 1
        and front_y < face.bounding_box().min.Y < face.bounding_box().max.Y < rear_y
    ]
    tab_features = []
    for tab in tabs:
        if tab.normal_at().Z > 0:
            cap = single(
                (face for face in tabs if face.normal_at().Z < 0
                 and near(face.center().X, tab.center().X)
                 and face.center().Z < tab.center().Z - FEATURE_EPSILON
                 and not any(other.normal_at().Z > 0 and near(other.center().X, tab.center().X)
                             and face.center().Z < other.center().Z < tab.center().Z - FEATURE_EPSILON
                             for other in tabs)),
                "支架缺口端面",
            )
            tab_features.append(measure_prism(tab, Z * (cap.center().Z - tab.center().Z)))

    # Internal cutouts come from separate mid-thickness sections.
    arms = (
        measure_prism(left_arm, X * (left_inside - left_x), keep_holes=False),
        measure_prism(right_arm, X * (right_inside - right_x), keep_holes=False),
    )

    cutouts = []
    for outer_x, inner_x in ((left_x, left_inside), (right_x, right_inside)):
        mid_x = (outer_x + inner_x) / 2
        arm = slice_face(source, X, mid_x, "支架臂截面")
        start, end = sorted((outer_x, inner_x))
        for hole in arm.inner_wires():
            cutter_profile = Face(hole).moved(Pos(start - mid_x - CUT_OVERLAP, 0, 0))
            cutouts.append(measure_prism(cutter_profile, X * (end - start + 2 * CUT_OVERLAP)))

    left_pin = single(
        (face for face in sides if face.center().X < left_x - FEATURE_EPSILON),
        "支架左侧轴端",
    )
    pin_depth = left_x - left_pin.center().X
    pin_rim = single(left_pin.outer_wire().edges(), "支架左侧轴端圆边")
    right_collar = single(
        (face for face in sides if face.center().X > right_x + FEATURE_EPSILON),
        "支架右侧轴套端面",
    )
    collar = measure_prism(right_collar, X * (right_x - right_collar.center().X))

    rounding = cylinders(source, X)
    rounds = []
    for face in rounding:
        bounds = face.bounding_box()
        if near(bounds.min.Y, front_y) and near(bounds.size.X, right_mount.center().X - left_mount.center().X):
            rounds.append(measure_round(face))

    rear_rounds = [
        face for face in rounding
        if near(face.bounding_box().max.Z, top_z) and face.bounding_box().min.Y > rear_y
    ]
    rounds.extend(measure_round(face) for face in rear_rounds)
    shoulder_trim = None
    if rear_rounds:
        tangent_y = rear_rounds[0].bounding_box().max.Y
        shoulder_y = max(y for _, y, _ in contour)
        if shoulder_y > tangent_y + FEATURE_EPSILON:
            slope = next(
                face for face in source.faces()
                if face.geom_type == GeomType.PLANE and near(face.normal_at().X, 0)
                and near(face.bounding_box().min.Y, tangent_y)
                and face.normal_at().Y > 0 and face.normal_at().Z > 0
            )
            normal, point = slope.normal_at(), slope.center()
            tangent_z = point.Z + (point.Y - tangent_y) * normal.Y / normal.Z
            shoulder_z = point.Z + (point.Y - shoulder_y) * normal.Y / normal.Z
            shoulder_trim = polygon_prism(
                [(left_x, tangent_y, top_z), (left_x, shoulder_y, top_z),
                 (left_x, shoulder_y, shoulder_z), (left_x, tangent_y, tangent_z)],
                X * (right_x - left_x),
            )

    chamfer = single(
        (face for face in source.faces()
         if face.geom_type == GeomType.PLANE and near(face.normal_at().X, 0)
         and face.normal_at().Y > FEATURE_EPSILON and face.normal_at().Z > FEATURE_EPSILON
         and near(face.bounding_box().max.Z, top_z) and near(face.bounding_box().max.Y, rear_y)),
        "支架安装框后沿倒角",
    )
    cb = chamfer.bounding_box()
    near_y, far_y = cb.min.Y, cb.max.Y
    wedge = polygon_prism(
        [(left_x, near_y, top_z), (left_x, far_y, top_z), (left_x, far_y, cb.min.Z)],
        X * (right_x - left_x),
    )
    # Constrain the chamfer to the cavity between its two sloping shoulders.
    mask = polygon_prism(
        [(cb.min.X + (far_y - near_y), near_y, cb.min.Z - 1),
         (cb.max.X - (far_y - near_y), near_y, cb.min.Z - 1),
         (cb.max.X, far_y, cb.min.Z - 1), (cb.min.X, far_y, cb.min.Z - 1)],
        Z * (cb.size.Z + 2),
    )
    return BracketFeatures(
        frame=frame.build(),
        window=window_cut.build(),
        tabs=tuple(feature.build() for feature in tab_features),
        arms=tuple(feature.build() for feature in arms),
        arm_cutouts=tuple(feature.build() for feature in cutouts),
        pin=cylinder(pin_rim.radius, pin_rim.arc_center, X, pin_depth + CUT_OVERLAP),
        collar=collar.build(),
        rounds=tuple(feature.build() for feature in rounds),
        shoulder_trim=shoulder_trim.build() if shoulder_trim is not None else None,
        chamfer=wedge.build(),
        chamfer_mask=mask.build(),
    )


def measure_head(source) -> HeadParameters:
    back = max(flat_faces(source, Y, -1), key=lambda face: face.area)
    front = max(flat_faces(source, Y, 1), key=lambda face: face.area)
    back_y, front_y = back.center().Y, front.center().Y
    middle_y = (back_y + front_y) / 2
    plate = slice_face(source, Y, middle_y, "云台头主板截面")
    plate_profile = measure_prism(plate.moved(Pos(0, back_y - middle_y, 0)), Y * (front_y - back_y))
    plate_top = plate.bounding_box().max.Z
    rounds = []
    for fillet in cylinders(source, X):
        bounds = fillet.bounding_box()
        if near(bounds.max.Y, front_y) and near(bounds.max.Z, plate_top):
            rounds.append(measure_round(fillet))

    sides = flat_faces(source, X)
    stops = [
        face for face in sides if face.normal_at().X < 0
        and near(face.bounding_box().min.Y, front_y)
        and any(edge.geom_type == GeomType.CIRCLE for edge in face.edges())
    ]
    steps = [
        face for face in flat_faces(source, Z)
        if near(face.bounding_box().min.Y, front_y) and face.bounding_box().max.Y > front_y
        and not any(near(face.bounding_box().min.X, stop.center().X)
                    and (near(face.center().Z, stop.bounding_box().min.Z)
                         or near(face.center().Z, stop.bounding_box().max.Z)) for stop in stops)
    ]
    clips = []
    for step in (face for face in steps if face.normal_at().Z < 0):
        bounds = step.bounding_box()
        cap = single(
            (face for face in steps if face.normal_at().Z > 0
             and face.center().Z > step.center().Z
             and near(face.bounding_box().min.X, bounds.min.X)
             and near(face.bounding_box().max.X, bounds.max.X)
             and near(face.bounding_box().max.Y, bounds.max.Y)),
            "云台头卡扣端面",
        )
        clips.append(measure_prism(step, Z * (cap.center().Z - step.center().Z)))

    bores = cylinders(source, X)
    lug_profiles = []
    for lug in (face for face in sides if face.normal_at().X < 0
                and face.bounding_box().min.Y < back_y - FEATURE_EPSILON
                and near(face.bounding_box().max.Y, back_y)):
        hole = single(lug.inner_wires(), "云台头耳座孔")
        hole_edge = single(hole.edges(), "云台头耳座圆孔")
        bore = single(
            (face for face in bores if near(face.radius, hole_edge.radius)
             and near(face.axis_of_rotation.position.Y, hole_edge.arc_center.Y)
             and near(face.axis_of_rotation.position.Z, hole_edge.arc_center.Z)),
            "云台头耳座圆柱面",
        )
        lug_profiles.append(measure_prism(lug, X * (bore.bounding_box().max.X - lug.center().X)))

    stop_profiles = []
    for stop in stops:
        bounds = stop.bounding_box()
        cap = single(
            (face for face in sides if face.normal_at().X > 0
             and face.center().X > stop.center().X
             and near(face.bounding_box().min.Y, bounds.min.Y)
             and near(face.bounding_box().max.Y, bounds.max.Y)
             and near(face.bounding_box().min.Z, bounds.min.Z)
             and near(face.bounding_box().max.Z, bounds.max.Z)),
            "云台头挡块端面",
        )
        stop_profiles.append(measure_prism(stop, X * (cap.center().X - stop.center().X)))
    return HeadParameters(plate_profile, tuple(rounds), tuple(clips), tuple(lug_profiles), tuple(stop_profiles))


def fit_base(source):
    plate, ring, holes = measure_base(source)
    return build_base_features(plate, ring, holes)


def fit_bracket(source):
    return build_bracket_features(measure_bracket(source))


def fit_head(source):
    return build_head(measure_head(source))


def check_fit(source, candidate):
    if len(candidate.solids()) != 1 or not candidate.is_valid:
        raise FitError("重建结果应为单一有效实体")
    differences = [
        *source.cut(candidate).solids(),
        *candidate.cut(source).solids(),
    ]
    if any(not solid.is_valid for solid in differences):
        raise FitError("几何差集返回了无效实体")
    volume_ratio = sum(solid.volume for solid in differences) / source.volume
    if volume_ratio > VOLUME_TOLERANCE:
        raise FitError(f"双向差集占源件体积 {volume_ratio:.4%}，上限为 {VOLUME_TOLERANCE:.2%}")

    source_bounds, fitted_bounds = source.bounding_box(), candidate.bounding_box()
    boundary_mm = max(
        abs(a - b)
        for points in ((source_bounds.min, fitted_bounds.min), (source_bounds.max, fitted_bounds.max))
        for a, b in zip(*points)
    )
    # Sampling both contours catches local errors even when the net volumes agree.
    for measured, other in ((source, candidate), (candidate, source)):
        shell = single(other.shells(), "零件外壳")
        for edge in measured.edges():
            for parameter in (0, 0.25, 0.5, 0.75):
                distance = Vertex(edge.position_at(parameter)).distance_to(shell)
                boundary_mm = max(boundary_mm, distance)
        for direction in (X, Y, Z):
            other_surfaces = cylinders(other, direction)
            for face in cylinders(measured, direction):
                center = face.axis_of_rotation.position
                for match in other_surfaces:
                    offset = center - match.axis_of_rotation.position
                    if (
                        offset.cross(direction).length <= DIMENSION_TOLERANCE
                        and 2 * abs(face.radius - match.radius) <= DIMENSION_TOLERANCE
                    ):
                        break
                else:
                    raise FitError(f"圆柱轴线或直径偏差超过 {DIMENSION_TOLERANCE:.2f} mm：{center}")
    if boundary_mm > DIMENSION_TOLERANCE:
        raise FitError(f"边界采样最大偏差 {boundary_mm:.4f} mm，上限为 {DIMENSION_TOLERANCE:.2f} mm")
    return FitDeviation(volume_ratio, boundary_mm)
