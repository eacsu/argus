"""Configured models and their shared preview and export metadata."""

from collections.abc import Callable
from dataclasses import dataclass, replace
from functools import partial

from build123d import Location, Shape

from argus.assembly import BASE, BRACKET, HEAD, PartSpec
from argus.models.base import build_base, preview as base
from argus.models.base.parameters import BASE_PARAMETERS, BASE_POSE
from argus.models.bracket import build_bracket, preview as bracket
from argus.models.bracket.parameters import BRACKET_PARAMETERS, BRACKET_POSE
from argus.models.bracket_print import build_print_bracket, preview as bracket_print
from argus.models.head import build_head, preview as head
from argus.models.head.parameters import HEAD_PARAMETERS, HEAD_POSE
from argus.models.head_print import build_print_head, preview as head_print
from argus.models.preview import PreviewField


BRACKET_PRINT = replace(BRACKET, output_stem="gimbal_bracket_print")
HEAD_PRINT = replace(HEAD, output_stem="gimbal_head_print")


@dataclass(frozen=True)
class ConfiguredModel:
    name: str
    spec: PartSpec
    assembly_pose: Location
    build_default: Callable[[], Shape]
    fields: tuple[PreviewField, ...]
    build: Callable[[dict[str, float]], Shape]


MODELS = {
    "base": ConfiguredModel(
        "底座", BASE, BASE_POSE, partial(build_base, BASE_PARAMETERS), base.FIELDS, base.build_preview,
    ),
    "bracket": ConfiguredModel(
        "支架", BRACKET, BRACKET_POSE, partial(build_bracket, BRACKET_PARAMETERS),
        bracket.FIELDS, bracket.build_preview,
    ),
    "bracket-print": ConfiguredModel(
        "打印支架", BRACKET_PRINT, BRACKET_POSE, partial(build_print_bracket, BRACKET_PARAMETERS),
        bracket.FIELDS, bracket_print.build_preview,
    ),
    "head": ConfiguredModel(
        "云台头", HEAD, HEAD_POSE, partial(build_head, HEAD_PARAMETERS), head.FIELDS, head.build_preview,
    ),
    "head-print": ConfiguredModel(
        "打印云台头", HEAD_PRINT, HEAD_POSE, partial(build_print_head, HEAD_PARAMETERS),
        head.FIELDS, head_print.build_preview,
    ),
}
