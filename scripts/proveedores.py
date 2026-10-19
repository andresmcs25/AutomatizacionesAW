"""Flujo de ejecución para procesar archivos de proveedores/Fomplus."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.common.excel import load_file, out, save_excel
from src.processors.proveedores import fomplus


def run() -> int:
    selected = load_file(title="Seleccione el reporte original de proveedores/Fomplus")
    if not selected:
        print("No se seleccionó ningún archivo. Proceso cancelado.")
        return 0

    input_path = Path(selected).resolve()
    result = fomplus(input_path)
    if result is None or result.empty:
        print("No se generó resultado porque el archivo no contiene registros válidos.")
        return 1

    output_path = out(input_path, "Fomplus")
    if not save_excel(output_path, {"Fomplus": result}):
        return 1

    return 0


if __name__ == "__main__":
    raise SystemExit(run())
