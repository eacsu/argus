"""Argus command-line entry point."""

import logging
import sys
from pathlib import Path

import typer

from argus.assembly import AssemblyError
from argus.exporting import ExportError
from argus.fitting import FitError
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
    if (bracket_print or head_print) and source is not None:
        variant_option = "--bracket-print" if bracket_print else "--head-print"
        raise typer.BadParameter("打印版从 Python 参数生成，请与 --source 分开运行。", param_hint=variant_option)
    try:
        if source is None:
            build_and_export(output_dir, bracket_print=bracket_print, head_print=head_print)
        else:
            fit_and_export(source, output_dir)
    except (AssemblyError, FitError, ExportError, OSError) as exc:
        typer.echo(str(exc), err=True)
        raise typer.Exit(1) from exc


if __name__ == "__main__":
    app()
