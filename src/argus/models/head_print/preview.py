"""Build previews with the standard gimbal-head bore dimensions."""

from argus.models.head.preview import preview_parameters
from argus.models.head_print import build_print_head


def build_preview(values: dict[str, float]):
    return build_print_head(preview_parameters(values))
