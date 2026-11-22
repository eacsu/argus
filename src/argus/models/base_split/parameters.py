"""Selectable horns and connections for the split base."""

from dataclasses import replace

from argus.models.base_servo.parameters import BASE_CONFIGURATIONS, DEFAULT_HORN_PROFILE, PROFILES, HornProfile
from argus.models.base_split import DEFAULT_BASE_CONNECTION, BaseConnection, BaseFasteners, SplitBaseParameters
from argus.models.preview import PreviewChoice, PreviewField, PreviewParameterError
from argus.models.servo_horn.parameters import LONG_HORN_PARAMETERS, SERVO_HORN_PARAMETERS


HORNS = {HornProfile.LONG: LONG_HORN_PARAMETERS, HornProfile.EQUAL: SERVO_HORN_PARAMETERS}
CONNECTIONS = {
    0: (BaseConnection.SNAP, "PETG 卡扣"),
    1: (BaseConnection.M3, "M3 热熔螺母"),
}
_CONNECTION_CODES = {connection: code for code, (connection, _) in CONNECTIONS.items()}


def default_base(
    profile: HornProfile = DEFAULT_HORN_PROFILE, connection: BaseConnection = DEFAULT_BASE_CONNECTION,
) -> SplitBaseParameters:
    base, horn = BASE_CONFIGURATIONS[profile]
    return SplitBaseParameters(
        center=base.ring.center,
        plate_side=base.plate_side,
        corner_radius=base.plate_corner_radius,
        corner_holes=base.corner_holes.holes(base.ring.center),
        lower_thickness=base.plate_thickness,
        cover_thickness=1.6,
        horn=horn.envelope,
        side_clearance=0.2,
        axial_clearance=0.15,
        tool_diameter=4.8,
        fasteners=BaseFasteners(),
        connection=connection,
    )


_DEFAULT = default_base()
_DEFAULT_CHOICE = next(value for value, (profile, _) in PROFILES.items() if profile == DEFAULT_HORN_PROFILE)
FIELDS = (
    PreviewField("horn_profile", "舵盘型号", "适配", _DEFAULT_CHOICE, min(PROFILES), max(PROFILES), unit="", choices=tuple(
        PreviewChoice(value, label, {"lower_thickness": default_base(profile).lower_thickness})
        for value, (profile, label) in PROFILES.items()
    )),
    PreviewField("side_clearance", "单边间隙", "适配", _DEFAULT.side_clearance, 0.05, 0.5),
    PreviewField("axial_clearance", "轴向留量", "适配", _DEFAULT.axial_clearance, 0.05, 0.3),
    PreviewField("plate_side", "底板边长", "底座", _DEFAULT.plate_side, 40, 55),
    PreviewField("lower_thickness", "下层板厚", "底座", _DEFAULT.lower_thickness, 5, 8),
    PreviewField("connection", "连接方式", "连接", _CONNECTION_CODES[DEFAULT_BASE_CONNECTION],
                 min(CONNECTIONS), max(CONNECTIONS), unit="", choices=tuple(
                     PreviewChoice(value, label) for value, (_, label) in CONNECTIONS.items()
                 )),
    PreviewField("snap_clearance", "卡扣单边间隙", "连接", _DEFAULT.snap_fit.clearance, 0.15, 0.4,
                 active_when=("connection", _CONNECTION_CODES[BaseConnection.SNAP])),
    PreviewField("bolt_length", "M3 螺栓长度", "连接", _DEFAULT.fasteners.bolt_length, 5, 10,
                 active_when=("connection", _CONNECTION_CODES[BaseConnection.M3])),
    PreviewField("pilot_diameter", "热熔底孔直径", "连接", _DEFAULT.fasteners.pilot_diameter, 3.7, 4.2,
                 active_when=("connection", _CONNECTION_CODES[BaseConnection.M3])),
)


def split_configuration(values: dict[str, float]) -> tuple[HornProfile, SplitBaseParameters]:
    profile, _ = PROFILES[values["horn_profile"]]
    connection, _ = CONNECTIONS[values["connection"]]
    base = default_base(profile, connection)
    fasteners = replace(base.fasteners, bolt_length=values["bolt_length"], pilot_diameter=values["pilot_diameter"])
    base = replace(
        base, fasteners=fasteners, lower_thickness=values["lower_thickness"], plate_side=values["plate_side"],
        side_clearance=values["side_clearance"], axial_clearance=values["axial_clearance"],
        snap_fit=replace(base.snap_fit, clearance=values["snap_clearance"]),
    )
    if connection == BaseConnection.M3:
        reach = fasteners.thread_reach(base.lower_thickness)
        if not fasteners.insert_length - 1e-6 <= reach <= fasteners.pilot_depth - 0.2 + 1e-6:
            raise PreviewParameterError({"bolt_length": "螺栓应伸入上层 3–4 mm。请调整螺栓长度或下层板厚。"})
    return profile, base
