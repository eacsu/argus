"""Nominal drawing dimensions and the repository's reference output spline."""

from dataclasses import replace

from argus.models.servo_horn import HornArm, HornEnvelope, ServoHornParameters, SplineSocket


HORN_ENVELOPE = HornEnvelope(
    main_arm=HornArm(span=26.25, tip_width=4.7, hole_offsets=tuple(5.8 + n * 2.5 for n in range(3))),
    hub_diameter=6.75,
    arm_thickness=1.95,
    overall_height=3.96,
)

SERVO_HORN_PARAMETERS = ServoHornParameters(
    envelope=HORN_ENVELOPE,
    socket=SplineSocket(
        teeth=20,
        major_diameter=4.8,
        minor_diameter=4.1,
        tip_angle=2.31,
        phase=13.3917,
        depth=2.8,
        clearance=0.05,
    ),
    arm_hole_diameter=1.2,
    center_hole_diameter=2.1,
)


# The drawing dimensions the outer pair pitch; interpolate the unmarked gaps.
LONG_FIRST_HOLE = 4.4
LONG_OUTER_PAIR_PITCH = 2.43
LONG_OUTERMOST_HOLE = 15.4
LONG_PENULTIMATE_HOLE = LONG_OUTERMOST_HOLE - LONG_OUTER_PAIR_PITCH
LONG_HOLE_OFFSETS = tuple(
    LONG_FIRST_HOLE + (LONG_PENULTIMATE_HOLE - LONG_FIRST_HOLE) * index / 5 for index in range(6)
) + (LONG_OUTERMOST_HOLE,)

LONG_HORN_PARAMETERS = ServoHornParameters(
    envelope=HornEnvelope(
        main_arm=HornArm(span=33.58, tip_width=4.65, hole_offsets=LONG_HOLE_OFFSETS),
        short_arm=HornArm(span=19.8, tip_width=4.2, hole_offsets=(5.3, 5.3 + LONG_OUTER_PAIR_PITCH)),
        hub_diameter=6.74,
        arm_thickness=2.25,
        overall_height=4.62,
    ),
    socket=replace(SERVO_HORN_PARAMETERS.socket, major_diameter=4.65, minor_diameter=3.95, depth=3.4),
    arm_hole_diameter=1.45,
    center_hole_diameter=2.36,
)
