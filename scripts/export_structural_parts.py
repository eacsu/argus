"""从参考装配导出三个结构件。"""

import logging
import sys
from pathlib import Path

from argus.assembly import AssemblyError
from argus.exporting import ExportError
from argus.workflow import export_reference_parts


ROOT = Path(__file__).resolve().parents[1]
SOURCE = ROOT / "data-bin" / "舵机云台总装.step"
OUTPUT = ROOT / "model-bin" / "structural-parts"


def main():
    logging.basicConfig(level=logging.INFO, format="%(message)s", stream=sys.stdout)
    logging.getLogger("build123d").setLevel(logging.WARNING)
    try:
        export_reference_parts(SOURCE, OUTPUT)
    except (AssemblyError, ExportError, OSError) as exc:
        raise SystemExit(str(exc)) from exc


if __name__ == "__main__":
    main()
