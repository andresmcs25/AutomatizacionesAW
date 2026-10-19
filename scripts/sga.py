"""Combina y normaliza los CSV que se encuentran en folders/SGA."""
from __future__ import annotations

import sys
from pathlib import Path
import pandas as pd

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.common.excel import out, save_excel
from src.processors.sga import process_sga_data


def run(sga_dir: Path | None = None) -> int:
    source_dir = Path(sga_dir or PROJECT_DIR / "folders" / "SGA").expanduser().resolve()
    source_dir.mkdir(parents=True, exist_ok=True)
    csv_paths = sorted(path for path in source_dir.glob("*.csv") if path.is_file())
    if not csv_paths:
        print(f"No se encontraron archivos CSV de SGA en: {source_dir}")
        return 1

    print(f"\nSe encontraron {len(csv_paths)} archivos CSV en: {source_dir}")
    columns_needed = [0, 1, 3, 4, 5, 6, 7, 8, 9, 10, 13, 15, 18, 22, 23, 24, 30, 33, 34, 41, 42, 48]
    df_sga = process_sga_data(csv_paths, columns_needed)
    if df_sga is None or df_sga.empty:
        print("No se generó el archivo porque no se pudieron procesar los CSV.")
        return 1

    columns_numeric = ["ID", "Lote", "VALORFACTURA", "GLOSA", "#Factura", "CUOTA_MODERADORA", "COPAGO"]
    missing_columns = [column for column in columns_numeric if column not in df_sga.columns]
    if missing_columns:
        print(f"Faltan columnas esperadas en SGA: {missing_columns}")
        return 1
    df_sga[columns_numeric] = df_sga[columns_numeric].apply(pd.to_numeric, errors="coerce")

    output_path = out(csv_paths[0], "SGA_Procesado")
    print("\nGuardando archivo procesado de SGA...")
    return 0 if save_excel(output_path, {"SGA_Procesado": df_sga}) else 1


if __name__ == "__main__":
    raise SystemExit(run())
