"""Build previews with the same editable dimensions as the regular bracket."""

from argus.models.bracket.preview import preview_parameters
from argus.models.bracket_print import build_print_bracket


def build_preview(values: dict[str, float]):
    return build_print_bracket(preview_parameters(values))
