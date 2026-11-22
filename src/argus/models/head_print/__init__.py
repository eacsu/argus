"""Gimbal head with a square plate bottom and extended side clips and stop."""

from dataclasses import replace

from argus.models.common import FEATURE_EPSILON, Outline, Prism, box_at
from argus.models.head import HeadParameters, build_head


def _square_plate_bottom(plate: Prism, bottom: float) -> Prism:
    outline = plate.outline
    assert isinstance(outline, Outline)
    midpoints = dict(outline.arcs)
    vertices, arcs = [], []
    for index, start in enumerate(outline.vertices):
        vertices.append(start)
        if index not in midpoints:
            continue
        end = outline.vertices[(index + 1) % len(outline.vertices)]
        if abs(start[2] - bottom) < FEATURE_EPSILON:
            vertices.append((end[0], end[1], bottom))
        elif abs(end[2] - bottom) < FEATURE_EPSILON:
            vertices.append((start[0], start[1], bottom))
        else:
            arcs.append((len(vertices) - 1, midpoints[index]))
    return replace(plate, outline=Outline(tuple(vertices), tuple(arcs)))


def build_print_head(parameters: HeadParameters):
    bottom = parameters.plate.outline.wire().bounding_box().min.Z
    head = build_head(replace(parameters, plate=_square_plate_bottom(parameters.plate, bottom)))

    # The two side clips share a lower starting plane than the short top clips.
    clips = tuple((clip, clip.outline.wire().bounding_box().min.Z) for clip in parameters.clips)
    side_clip_z = min(z for _, z in clips)
    side_extensions = [
        replace(clip, direction=(0.0, 0.0, bottom - z)).build()
        for clip, z in clips if abs(z - side_clip_z) < FEATURE_EPSILON
    ]
    stop = min((feature.build().bounding_box() for feature in parameters.stops), key=lambda bounds: bounds.min.Z)
    stop_extension = box_at((stop.min.X, stop.min.Y, bottom), (stop.size.X, stop.size.Y, stop.min.Z - bottom))
    return head.fuse(stop_extension, *side_extensions)
