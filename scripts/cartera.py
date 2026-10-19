"""Flujo independiente para procesar un archivo de cartera (FAC y ANT)."""
from __future__ import annotations

import sys
from pathlib import Path

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.common.excel import load_file, out, save_excel
from src.processors.cartera import cartera


def run() -> int:
    selected = load_file(title="Seleccione el archivo de cartera")
    if not selected:
        print("No se seleccionó ningún archivo. Proceso cancelado.")
        return 0

    input_path = Path(selected).expanduser().resolve()
    result = cartera(input_path, invoice_prefixes=("FAC", "ANT"))
    if result is None:
        print("No se generó resultado. Verifique el archivo y sus filas FAC/ANT.")
        return 1

    dataframe, _ = result
    if dataframe is None or dataframe.empty:
        print("No se generó resultado porque no se encontraron registros de cartera.")
        return 1

    output_path = out(input_path, "Cartera")
    if not save_excel(output_path, {"Cartera": dataframe}):
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(run())
