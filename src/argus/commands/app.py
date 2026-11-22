"""Argus command-line entry point."""

import logging
import sys
from pathlib import Path

import typer

from argus.assembly import AssemblyError
from argus.exporting import ExportError
from argus.fitting import FitError
from argus.models.base_servo.parameters import DEFAULT_HORN_PROFILE, HornProfile
from argus.models.base_split import DEFAULT_BASE_CONNECTION, BaseConnection
from argus.workflow import build_and_export, fit_and_export


app = typer.Typer(add_completion=False)


@app.command()
def main(
    source: Path | None = typer.Option(
        None, "--source",
        envvar="ARGUS_SOURCE", help="用指定装配 STEP 重新量测和拟合。",
    ),
    output_dir: Path = typer.Option(
        Path("model-bin/parametric-parts"), "--output-dir", "-o",
        envvar="ARGUS_OUTPUT_DIR", help="STEP 和 3MF 输出目录。",
    ),
    base_servo: bool = typer.Option(
        False, "--base-servo", help="导出适配十字舵盘的开槽底盘。",
    ),
    split_base: bool = typer.Option(False, "--split-base", help="导出分体底座的上盖和下座。"),
    sg90s: bool = typer.Option(False, "--sg90s", help="导出参数化 SG90S 参考舵机。"),
    assembly: bool = typer.Option(False, "--assembly", help="导出保留零件位姿的整机 STEP。"),
    single_horn: bool = typer.Option(False, "--single-horn", help="导出适配支架外侧的单臂舵盘。"),
    servo_horn: bool = typer.Option(
        False, "--servo-horn", help="导出所选型号的舵盘。",
    ),
    horn_profile: HornProfile | None = typer.Option(
        None, "--horn-profile", help="底座和舵盘的配合型号，默认 long（长短臂）。",
    ),
    base_connection: BaseConnection | None = typer.Option(
        None, "--base-connection", envvar="ARGUS_BASE_CONNECTION",
        help="分体底座连接方式，默认 snap（PETG 卡扣），可选 m3（热熔螺母）。",
    ),
    bracket_print: bool = typer.Option(
        False, "--bracket-print", help="导出底部补平的打印支架。",
    ),
    head_print: bool = typer.Option(
        False, "--head-print", help="导出卡扣下方补平的打印云台头。",
    ),
) -> None:
    """从 Python 参数生成结构件并导出 STEP 和 3MF。"""
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.__stderr__)
    logging.getLogger("build123d").setLevel(logging.WARNING)
    if source is not None:
        variants = (
            (base_servo, "--base-servo"), (servo_horn, "--servo-horn"),
            (split_base, "--split-base"), (sg90s, "--sg90s"), (assembly, "--assembly"),
            (single_horn, "--single-horn"),
            (bracket_print, "--bracket-print"), (head_print, "--head-print"),
            (horn_profile is not None, "--horn-profile"),
            (base_connection is not None, "--base-connection"),
        )
        for selected, option in variants:
            if selected:
                raise typer.BadParameter("变体从 Python 参数生成，请与 --source 分开运行。", param_hint=option)
    try:
        if source is None:
            build_and_export(
                output_dir, base_servo=base_servo, servo_horn=servo_horn,
                bracket_print=bracket_print, head_print=head_print,
                horn_profile=horn_profile or DEFAULT_HORN_PROFILE,
                split_base=split_base, sg90s=sg90s, assembly=assembly,
                single_horn=single_horn,
                base_connection=base_connection or DEFAULT_BASE_CONNECTION,
            )
        else:
            fit_and_export(source, output_dir)
    except (AssemblyError, FitError, ExportError, OSError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    app()
