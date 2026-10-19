"""Menú de consola para los procesos disponibles en el proyecto."""
from __future__ import annotations

import subprocess
import sys
import argparse
from dataclasses import dataclass
from pathlib import Path
from typing import Callable


def project_dir() -> Path:
    if getattr(sys, "frozen", False):
        return Path(sys.executable).resolve().parent
    return Path(__file__).resolve().parent


def run_pipeline_worker() -> None:
    from scripts.depuracion import run

    parser = argparse.ArgumentParser(description="Ejecutor del proceso de depuración")
    parser.add_argument("--cartera-dir", type=Path, required=True)
    parser.add_argument("--sga-dir", type=Path, required=True)
    args = parser.parse_args()
    run(args.cartera_dir, args.sga_dir)


def run_depuracion() -> int:
    base = project_dir()
    default_cartera = base / "folders" / "Cartera"
    default_sga = base / "folders" / "SGA"
    cartera = default_cartera
    sga = default_sga
    cartera.mkdir(parents=True, exist_ok=True)
    sga.mkdir(parents=True, exist_ok=True)
    print(f"\nCarpeta de cartera: {cartera}")
    print(f"Carpeta de SGA:     {sga}")
    print("\n" + "=" * 60)
    print("                 DEPURACIÓN DE CARTERA")
    print("=" * 60)

    required = [cartera / "Cartera.xlsx", cartera / "TC.Xlsx"]
    missing = [path for path in required if not path.is_file()]
    if missing:
        print("\nNo se encontraron los archivos requeridos:")
        for path in missing:
            print(f"  - {path}")
        return 1
    if not sga.is_dir() or not any(sga.glob("*.csv")):
        print(f"\nNo se encontraron archivos CSV de SGA en: {sga}")
        return 1

    args = ["--cartera-dir", str(cartera), "--sga-dir", str(sga)]
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--pipeline", *args]
    else:
        command = [sys.executable, str(base / "scripts" / "depuracion.py"), *args]
    print("\nIniciando Depuración de cartera en esta ventana...\n")
    return subprocess.run(command, cwd=str(base), check=False).returncode


def run_proveedores() -> int:
    base = project_dir()
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--proveedores"]
    else:
        command = [sys.executable, str(base / "scripts" / "proveedores.py")]
    return subprocess.run(command, cwd=str(base), check=False).returncode


def run_sga() -> int:
    base = project_dir()
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--sga"]
    else:
        command = [sys.executable, str(base / "scripts" / "sga.py")]
    return subprocess.run(command, cwd=str(base), check=False).returncode


def run_cartera() -> int:
    base = project_dir()
    if getattr(sys, "frozen", False):
        command = [sys.executable, "--cartera"]
    else:
        command = [sys.executable, str(base / "scripts" / "cartera.py")]
    return subprocess.run(command, cwd=str(base), check=False).returncode


def show_header() -> None:
    print("=" * 70)
    print("\t\t\tPROCESAMIENTO DE ARCHIVOS")
    print("=" * 70)
    print("\nProcesamiento local de cartera y archivos SGA.")
    print("\n" + "-" * 70)


@dataclass(frozen=True)
class ProcessOption:
    name: str
    action: Callable[[], int]
    workspace_folders: tuple[str, ...]


# Cada proceso registra aquí su acción y las carpetas que necesita.
PROCESSES: list[ProcessOption] = [
    ProcessOption("Depuración de cartera", run_depuracion, ("Cartera", "SGA")),
    ProcessOption("Procesar cartera (FAC y ANT)", run_cartera, ()),
    ProcessOption("Proveedores / Fomplus", run_proveedores, ()),
    ProcessOption("Consolidar archivos SGA", run_sga, ("SGA",)),
]


def main() -> int:
    workspace = project_dir() / "folders"
    for process in PROCESSES:
        for folder in process.workspace_folders:
            (workspace / folder).mkdir(parents=True, exist_ok=True)
    while True:
        show_header()
        print("Procesos disponibles:\n")
        for index, process in enumerate(PROCESSES, start=1):
            print(f"  {index}. {process.name}")
        print("  0. Salir")
        choice = input("\nSelecciona un proceso: ").strip()
        if choice == "0":
            print("Cerrando aplicación.")
            return 0
        if not choice.isdigit() or not 1 <= int(choice) <= len(PROCESSES):
            print("Opción no válida. Selecciona uno de los números del menú.")
            continue
        process = PROCESSES[int(choice) - 1]
        print(f"\nProceso seleccionado: {process.name}")
        result = process.action()
        if result == 0:
            print("\nProceso terminado.")
        else:
            print(f"\nEl proceso terminó con código {result}.")
        input("Presiona ENTER para volver al menú...")


if __name__ == "__main__":
    if "--pipeline" in sys.argv:
        sys.argv.remove("--pipeline")
        run_pipeline_worker()
        raise SystemExit(0)
    if "--proveedores" in sys.argv:
        sys.argv.remove("--proveedores")
        from scripts.proveedores import run

        raise SystemExit(run())
    if "--sga" in sys.argv:
        sys.argv.remove("--sga")
        from scripts.sga import run

        raise SystemExit(run(project_dir() / "folders" / "SGA"))
    if "--cartera" in sys.argv:
        sys.argv.remove("--cartera")
        from scripts.cartera import run

        raise SystemExit(run())
    raise SystemExit(main())
