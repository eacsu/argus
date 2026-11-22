"""Opposed in-plane snap arms and locating keys for the split base."""

from dataclasses import dataclass

from build123d import Pos, Rot

from argus.models.common import Outline, Prism, box_at


@dataclass(frozen=True)
class SnapFit:
    clearance: float = 0.25

    # Local X points out through a side of the base. Z=0 is the mating plane.
    stem_inner: float = -2.65
    stem_outer: float = -1.75
    hook_outer: float = -0.85
    hook_start: float = 3.25
    hook_end: float = 9.25
    shoulder_depth: float = 2.25
    tip_depth: float = 3.5
    shoulder_clearance: float = 0.15
    inward_travel: float = 1.50
    key_length: float = 8.0
    key_width: float = 2.4
    key_depth: float = 1.6
    key_inset: float = 3.2
    key_offset: float = 7.5

    def _placements(self, center: tuple[float, float], side: float, z: float):
        for angle in (0, 180):
            origin = Pos(*center, z) * Rot(0, 0, angle)
            yield origin * Pos(side / 2, 0, 0), origin * Pos(self.key_offset, side / 2 - self.key_inset, 0)

    def lower(self, plate, center: tuple[float, float], side: float, thickness: float):
        clearance = self.clearance
        x = self.stem_inner - self.inward_travel
        y = self.hook_start - clearance
        width = self.hook_end - self.hook_start + 2 * clearance
        # The upper wall of the side opening forms the ledge that retains the hook.
        release_z = -self.shoulder_depth + self.shoulder_clearance
        guides = box_at((x, y, -thickness - 1), (self.stem_outer + clearance - x, width, thickness + 2))
        opening = box_at((x, y, -thickness - 1), (1 - x, width, thickness + 1 + release_z))
        receiver = guides + opening
        socket = self._key(clearance, self.shoulder_clearance)
        for rim, key in self._placements(center, side, thickness):
            plate = plate - rim * receiver - key * socket
        return plate

    def upper(self, plate, center: tuple[float, float], side: float, thickness: float):
        slot = self._arm_relief(thickness)
        hook = self._hook()
        tongue = self._key()
        for rim, key in self._placements(center, side, 0):
            plate = plate - rim * slot + rim * hook + key * tongue
        return plate

    def _arm_relief(self, thickness: float):
        inner = self.stem_inner - self.inward_travel
        radius = self.inward_travel / 2
        root = -11.0
        end = self.hook_end + 0.5
        profile = Outline(
            ((inner, root, -1), (self.stem_inner, root, -1), (self.stem_inner, end, -1),
             (1, end, -1), (1, end + self.inward_travel, -1), (inner, end + self.inward_travel, -1)),
            ((0, (inner + radius, root - radius, -1)),),
        )
        return Prism(profile, (0, 0, thickness + 2)).build()

    def _hook(self):
        y = self.hook_start
        profile = Outline((
            (self.stem_inner, y, 0.3), (self.stem_outer, y, 0.3),
            (self.stem_outer, y, -self.shoulder_depth), (self.hook_outer, y, -self.shoulder_depth),
            (self.stem_outer, y, -self.tip_depth), (self.stem_inner, y, -self.tip_depth),
        ))
        return Prism(profile, (0, self.hook_end - y, 0)).build()

    def _key(self, clearance: float = 0, depth_clearance: float = 0):
        length = self.key_length + 2 * clearance
        width = self.key_width + 2 * clearance
        depth = self.key_depth + depth_clearance
        return box_at((-length / 2, -width / 2, -depth), (length, width, depth + 0.3))
