"""Configured bracket dimensions in mm and assembly rotations in degrees."""

from build123d import Location

from argus.models.bracket import BracketParameters
from argus.models.bracket.horn_seat import HornSeat
from argus.models.common import Outline, Prism, RoundCut


BRACKET_POSE = Location((-1.7741354036, -15.5529077949, 22.9850159643), (0.0, -2.7780463009, 0.0))


def yz_profile(vertices, arcs=()) -> Outline:
    return Outline(
        tuple((0.0, y, z) for y, z in vertices),
        tuple((index, (0.0, y, z)) for index, (y, z) in arcs),
    )


BRACKET_PARAMETERS = BracketParameters(
    frame_half=(
        (-11.9644660941, 10.0),
        (-15.5, 13.5355339059),
        (-18.0, 12.5),
        (-13.0, 7.5),
        (-11.0, 7.5),
        (-11.0, 0.0),
    ),
    frame_height=36.0,
    window_width=14.0,
    window_height=23.0,
    arm_thickness=2.5,
    arm=yz_profile(
        vertices=(
            (12.5, -36.0),
            (12.5, -0.2679491924),
            (13.1, -0.8),
            (30.3646572069, -23.8195429426),
            (30.5917481222, -24.2060696564),
            (36.5371140398, -37.5595801415),
            (26.4665547236, -43.8650289489),
            (19.8427442237, -36.0),
        ),
        arcs=(
            (1, (12.8269399065, -0.5035941444)),
            (3, (30.4890668916, -24.0064233842)),
            (5, (34.2399551423, -45.0854123727)),
        ),
    ),
    arm_window=yz_profile(
        vertices=(
            (16.3, -15.0666666667),
            (14.5, -15.6666666667),
            (14.5, -29.0),
            (15.5, -30.0),
            (22.5, -30.0),
            (23.5, -29.0),
            (23.5, -25.0),
            (23.3, -24.4),
        ),
        arcs=(
            (0, (15.183772234, -14.7179833686)),
            (2, (14.7928932188, -29.7071067812)),
            (4, (23.2071067812, -29.7071067812)),
            (6, (23.4486832981, -24.683772234)),
        ),
    ),
    tab=Prism(
        outline=Outline(((-11.0, 7.5, -29.0), (-13.0, 7.5, -29.0), (-11.0, 5.5, -29.0))),
        direction=(0.0, 0.0, -1.0),
    ),
    tab_pitch=20.0,
    front_round=RoundCut(
        minimum=(-11.0, 0.0, -2.0),
        maximum=(11.0, 2.0, 0.0),
        axis_center=(0.0, 2.0, -2.0),
        radius=2.0,
    ),
    shoulder_round=RoundCut(
        minimum=(-18.0, 11.5, -0.8),
        maximum=(-13.4644660941, 13.1, 0.0),
        axis_center=(0.0, 11.5, -2.0),
        radius=2.0,
    ),
    shoulder_trim=yz_profile((
        (13.1, 0.0), (13.5355339059, 0.0), (13.5355339059, -1.3807118746), (13.1, -0.8),
    )),
    chamfer=yz_profile(((9.0, 0.0), (10.0, 0.0), (10.0, -1.0))),
    chamfer_mask_half=((-11.9644660941, 10.0), (-10.9644660941, 9.0)),
    shaft_axis=(31.0558412939, -40.0),
    pin_radius=2.0,
    pin_depth=2.0,
    horn_seat=HornSeat(),
)
