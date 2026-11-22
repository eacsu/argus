"""Gimbal bracket with a flat underside below the frame and both arms."""

from dataclasses import replace

from build123d import Plane, Shape, Solid, section

from argus.models.bracket import (
    CUT_OVERLAP, BracketParameters, build_bracket_features, cut_horn_seat, resolve_bracket_features,
)
from argus.models.common import Outline, Prism


def _underside_fill(parameters: BracketParameters, frame: Shape) -> Shape:
    bed_y = min(y for _, y in parameters.frame_half)
    front_x = min(x for x, y in parameters.frame_half if y == bed_y)
    arm_x, arm_y = min(parameters.frame_half)
    # The strip widens out toward the arm at 1 mm per mm of build height.
    ramp_y = arm_y - (front_x - arm_x)

    tip = min(parameters.arm.wire().edges(), key=lambda edge: edge.bounding_box().min.Z)
    end_y = tip.arc_center.Y
    bottom = tip.bounding_box().min.Z
    # Extend just past the lower round so the fill joins the frame at the bed.
    top = -parameters.frame_height - parameters.front_round.axis_center[2] + CUT_OVERLAP
    edge = ((front_x, bed_y), (front_x, ramp_y), (arm_x, arm_y), (arm_x, end_y))
    profile = Outline(
        tuple((x, y, bottom) for x, y in edge)
        + tuple((x + parameters.arm_thickness, y, bottom) for x, y in reversed(edge)),
    )
    strip = Prism(profile, (0.0, 0.0, top - bottom)).build()
    footprint = section(frame, section_by=Plane((0, 0, top))).faces()[0]
    front_fill = Solid.extrude(footprint, (0.0, 0.0, bottom - top))
    return front_fill.fuse(strip, strip.mirror(Plane.YZ))


def build_print_bracket(parameters: BracketParameters):
    features = resolve_bracket_features(parameters)
    bracket = build_bracket_features(replace(features, horn_cutouts=()))
    fill = _underside_fill(parameters, features.frame).cut(features.window, *features.arm_cutouts)
    return cut_horn_seat(bracket.fuse(*fill.solids()), features.horn_cutouts)
