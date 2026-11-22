"""Choose a nominal horn and adapt the base's pocket to its mounting geometry."""

from dataclasses import replace

from argus.models.base_servo import build_servo_base
from argus.models.base_servo.parameters import BASE_CONFIGURATIONS, DEFAULT_HORN_PROFILE, PROFILES, HornProfile
from argus.models.preview import PreviewChoice, PreviewField, PreviewParameterError


def profile_defaults(profile: HornProfile) -> dict[str, float]:
    base, seat = BASE_CONFIGURATIONS[profile]
    envelope = seat.envelope
    return {
        "plate_thickness": base.plate_thickness,
        "span": envelope.main_arm.span,
        "tip_width": envelope.main_arm.tip_width,
        "hub_diameter": envelope.hub_diameter,
        "arm_thickness": envelope.arm_thickness,
        "overall_height": envelope.overall_height,
        "clearance": seat.clearance,
        "fastener_diameter": seat.fastener_diameter,
    }


_DEFAULT_CHOICE = next(value for value, (profile, _) in PROFILES.items() if profile == DEFAULT_HORN_PROFILE)
_DEFAULTS = profile_defaults(DEFAULT_HORN_PROFILE)
FIELDS = (
    PreviewField("horn_profile", "舵盘型号", "适配", _DEFAULT_CHOICE, min(PROFILES), max(PROFILES), unit="", choices=tuple(
        PreviewChoice(value, label, profile_defaults(profile)) for value, (profile, label) in PROFILES.items()
    )),
    PreviewField("plate_side", "底板边长", "底板", 42, 38, 55),
    PreviewField("plate_thickness", "板厚", "底板", _DEFAULTS["plate_thickness"], 5, 8),
    PreviewField("span", "舵盘长向总宽", "舵盘槽", _DEFAULTS["span"], 24, 38),
    PreviewField("tip_width", "主臂端宽度", "舵盘槽", _DEFAULTS["tip_width"], 3.5, 5.5),
    PreviewField("hub_diameter", "中凸台直径", "舵盘槽", _DEFAULTS["hub_diameter"], 6, 8),
    PreviewField("arm_thickness", "臂板厚度", "舵盘槽", _DEFAULTS["arm_thickness"], 1.5, 3),
    PreviewField("overall_height", "舵盘总厚", "舵盘槽", _DEFAULTS["overall_height"], 3.2, 5.4),
    PreviewField("clearance", "装配间隙", "舵盘槽", _DEFAULTS["clearance"], 0.05, 0.5),
    PreviewField("fastener_diameter", "固定孔直径", "固定孔", _DEFAULTS["fastener_diameter"], 1, 2.2),
)


def build_preview(values: dict[str, float]):
    profile, _ = PROFILES[values["horn_profile"]]
    base, seat = BASE_CONFIGURATIONS[profile]
    thickness, side, clearance = values["plate_thickness"], values["plate_side"], values["clearance"]
    envelope = replace(
        seat.envelope,
        main_arm=replace(seat.envelope.main_arm, span=values["span"], tip_width=values["tip_width"]),
        hub_diameter=values["hub_diameter"],
        arm_thickness=values["arm_thickness"],
        overall_height=values["overall_height"],
    )
    seat = replace(seat, envelope=envelope, clearance=clearance, fastener_diameter=values["fastener_diameter"])
    errors = {}
    if thickness < seat.hub_depth + 1.2:
        errors["plate_thickness"] = "中央凹槽下方至少需保留 1.2 mm 底厚。"
    if envelope.main_arm.span < 2 * (envelope.main_arm.hole_offsets[-1] + 0.75):
        errors["span"] = "槽长不足，无法容纳该舵盘的臂端孔。"
    if envelope.main_arm.span + 2 * clearance > side - 2:
        errors["plate_side"] = "凹槽两端至少需保留 1 mm 底板边距。"
    if errors:
        raise PreviewParameterError(errors)
    return build_servo_base(replace(
        base,
        plate_side=side,
        plate_thickness=thickness,
        ring=replace(base.ring, height=base.ring.height + base.plate_thickness - thickness),
    ), seat)
