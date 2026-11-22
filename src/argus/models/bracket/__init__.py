"""Gimbal bracket with a mirrored frame and independent shaft interfaces."""

from dataclasses import dataclass

from build123d import Plane, Pos, Shape

from argus.models.common import X, Outline, Prism, RoundCut, cylinder


CUT_OVERLAP = 0.001  # mm
Point2D = tuple[float, float]


@dataclass(frozen=True)
class BracketParameters:
    """Dimensions and profiles of the parametric bracket in its local axes."""

    frame_half: tuple[Point2D, ...]
    frame_height: float
    window_width: float
    window_height: float
    arm_thickness: float
    arm: Outline
    arm_window: Outline
    tab: Prism
    tab_pitch: float
    front_round: RoundCut
    shoulder_round: RoundCut
    shoulder_trim: Outline
    chamfer: Outline
    chamfer_mask_half: tuple[Point2D, ...]
    shaft_axis: Point2D
    pin_radius: float
    pin_depth: float
    bearing_radius: float
    side_bore_center: Point2D
    side_bore_radius: float
    collar: Prism


@dataclass(frozen=True)
class BracketFeatures:
    """Resolved features shared by parametric construction and source calibration."""

    frame: Shape
    window: Shape
    tabs: tuple[Shape, ...]
    arms: tuple[Shape, ...]
    arm_cutouts: tuple[Shape, ...]
    pin: Shape
    collar: Shape
    rounds: tuple[Shape, ...]
    shoulder_trim: Shape | None
    chamfer: Shape
    chamfer_mask: Shape


def _symmetric_profile(left: tuple[Point2D, ...], z: float) -> Outline:
    return Outline(
        tuple((x, y, z) for x, y in left)
        + tuple((-x, y, z) for x, y in reversed(left)),
    )


def _x_prism(outline: Outline, x: float, depth: float) -> Shape:
    return Prism(outline, (depth, 0.0, 0.0)).build().moved(Pos(x, 0, 0))


def build_bracket(parameters: BracketParameters):
    return build_bracket_features(resolve_bracket_features(parameters))


def resolve_bracket_features(parameters: BracketParameters) -> BracketFeatures:
    left_x = min(x for x, _ in parameters.frame_half)
    right_x = -left_x
    frame_bottom = -parameters.frame_height
    mid_z = frame_bottom / 2
    frame_midplane = Plane((0, 0, mid_z))
    frame = Prism(
        _symmetric_profile(parameters.frame_half, frame_bottom),
        (0.0, 0.0, parameters.frame_height),
    ).build()

    front_y = min(y for _, y in parameters.frame_half) - CUT_OVERLAP
    rear_y = max(y for _, y in parameters.frame_half) + CUT_OVERLAP
    half_width = parameters.window_width / 2
    window_top = mid_z + parameters.window_height / 2
    window_bottom = mid_z - parameters.window_height / 2
    window = Prism(Outline((
        (-half_width, front_y, window_top), (-half_width, front_y, window_bottom),
        (half_width, front_y, window_bottom), (half_width, front_y, window_top),
    )), (0.0, rear_y - front_y, 0.0)).build()

    arm = _x_prism(parameters.arm, left_x, parameters.arm_thickness)
    cut_depth = parameters.arm_thickness + 2 * CUT_OVERLAP
    arm_window = _x_prism(parameters.arm_window, left_x - CUT_OVERLAP, cut_depth)
    right_cutter_x = right_x - parameters.arm_thickness - CUT_OVERLAP
    tab = parameters.tab.build()
    right_tab = tab.mirror(Plane.YZ)
    next_tab_row = Pos(0, 0, parameters.tab_pitch)
    front_round = parameters.front_round.build()
    shoulder_round = parameters.shoulder_round.build()

    chamfer_min_z = min(z for _, _, z in parameters.chamfer.vertices)
    chamfer_mask = Prism(
        _symmetric_profile(parameters.chamfer_mask_half, chamfer_min_z - 1),
        (0.0, 0.0, 2 - chamfer_min_z),
    ).build()

    return BracketFeatures(
        frame=frame,
        window=window,
        tabs=(tab, right_tab, tab.moved(next_tab_row), right_tab.moved(next_tab_row)),
        arms=(arm, arm.mirror(Plane.YZ)),
        arm_cutouts=(
            arm_window, arm_window.mirror(Plane.YZ),
            cylinder(parameters.bearing_radius, (right_cutter_x, *parameters.shaft_axis), X, cut_depth),
            cylinder(parameters.side_bore_radius, (right_cutter_x, *parameters.side_bore_center), X, cut_depth),
        ),
        pin=cylinder(
            parameters.pin_radius, (left_x - parameters.pin_depth, *parameters.shaft_axis),
            X, parameters.pin_depth + CUT_OVERLAP,
        ),
        collar=parameters.collar.build().moved(Pos(right_x, 0, 0)),
        rounds=(
            front_round, front_round.mirror(frame_midplane),
            shoulder_round, shoulder_round.mirror(Plane.YZ),
        ),
        shoulder_trim=_x_prism(parameters.shoulder_trim, left_x, right_x - left_x),
        chamfer=_x_prism(parameters.chamfer, left_x, right_x - left_x),
        chamfer_mask=chamfer_mask,
    )


def build_bracket_features(features: BracketFeatures):
    part = features.frame - features.window
    for feature in (*features.tabs, *features.arms):
        part += feature
    for opening in features.arm_cutouts:
        part -= opening
    part += features.pin
    part += features.collar
    for rounding in features.rounds:
        part -= rounding
    if features.shoulder_trim is not None:
        part -= features.shoulder_trim
    return part - (features.chamfer & features.chamfer_mask)
