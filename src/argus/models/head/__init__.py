"""Gimbal head, including its plate, clips, lugs and stops."""

from dataclasses import dataclass

from argus.models.common import Prism, RoundCut


@dataclass(frozen=True)
class HeadParameters:
    plate: Prism
    rounds: tuple[RoundCut, ...]
    clips: tuple[Prism, ...]
    lugs: tuple[Prism, ...]
    stops: tuple[Prism, ...]


def build_head(parameters: HeadParameters):
    part = parameters.plate.build()
    for rounding in parameters.rounds:
        part -= rounding.build()
    for feature in (*parameters.clips, *parameters.lugs, *parameters.stops):
        part += feature.build()
    return part
