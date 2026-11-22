"""Configured gimbal base dimensions in mm and assembly rotations in degrees."""

from build123d import Location

from argus.models.base import BaseParameters, Counterbore, QuarterTurnHolePattern, RingParameters


BASE_POSE = Location((-1.6259296646, -34.7529077949, 7.7945294492), (-90.0, 0.0, 10.8302388056))


BASE_PARAMETERS = BaseParameters(
    ring=RingParameters(
        center=(0.0, -2.5),
        outer_radius=12.0,
        inner_radius=11.0,
        height=9.0000001,
        root_fillet=0.2000002,
        slot_y_offset=0.0,
        slot_height=3.0,
        slot_radius=3.0,
    ),
    plate_side=38.0,
    plate_thickness=3.5,
    plate_corner_radius=1.0,
    corner_holes=QuarterTurnHolePattern(offset=(15.0, 15.0), radius=1.25),
    inner_holes=QuarterTurnHolePattern(
        offset=(9.0, 0.0),
        radius=1.0,
        counterbore=Counterbore(radius=1.5, depth=0.6, taper_radius=1.0, taper_depth=0.3004303095),
    ),
)
