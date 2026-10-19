import pandas as pd
from datetime import datetime
from pathlib import Path
from tkinter import Tk, filedialog
import os
import tempfile

def load_file(title="Seleccione el archivo corregido"):
    root = Tk()
    root.withdraw()
    filepath = filedialog.askopenfilename(title=title, filetypes=[("Archivos Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")])
    root.destroy()
    return filepath


def load_files(title="Seleccione los archivos de entrada"):
    """Abre un selector para que el usuario entregue varios archivos Excel."""
    root = Tk()
    root.withdraw()
    paths = filedialog.askopenfilenames(
        title=title,
        filetypes=[("Archivos Excel", "*.xlsx *.xls"), ("Todos los archivos", "*.*")],
    )
    root.destroy()
    return tuple(paths)

def load_data(filepath, cols_drop):
    try:
        all_sheets = pd.read_excel(filepath, sheet_name=None, header=None)
        data = pd.concat(all_sheets.values(), ignore_index=True)
        return clean_table(data, cols_drop)
    except Exception as e:
        print(f"Ocurrió un error al procesar el archivo {filepath}: {e}")
        return None


def load_excel_sheets(filepaths, sheet_names):
    """Combina por nombre las hojas disponibles en varios libros Excel."""
    result = {}
    for sheet_name in sheet_names:
        frames = []
        for filepath in filepaths:
            try:
                with pd.ExcelFile(filepath) as workbook:
                    if sheet_name in workbook.sheet_names:
                        frames.append(pd.read_excel(workbook, sheet_name=sheet_name))
            except Exception as exc:
                print(f"❌ Error leyendo {sheet_name} en {filepath}: {exc}")
        if frames:
            result[sheet_name] = pd.concat(frames, ignore_index=True)
    return result

def clean_table(dataframe, cols_drop):
    dataframe.dropna(how='all', inplace=True)
    existing_columns = [column for column in cols_drop if column in dataframe.columns]
    dataframe.drop(existing_columns, axis=1, inplace=True)
    dataframe.reset_index(drop=True, inplace=True)
    dataframe.dropna(axis=1, how='all', inplace=True)
    return dataframe

def save_excel(path, sheets_dict):
    path = Path(path).expanduser().resolve()
    temporary_path = None
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        file_descriptor, temporary_name = tempfile.mkstemp(
            prefix=f".{path.stem}_", suffix=path.suffix, dir=path.parent
        )
        os.close(file_descriptor)
        temporary_path = Path(temporary_name)
        with pd.ExcelWriter(temporary_path, engine='openpyxl') as writer:
            for sheet, df in sheets_dict.items():
                if df is None:
                    continue
                if hasattr(df, 'empty') and df.empty:
                    continue
                df.to_excel(writer, sheet_name=sheet, index=False)
        # Reemplazar al final conserva el resultado anterior si el guardado
        # falla, por ejemplo porque el destino está abierto en Excel.
        os.replace(temporary_path, path)
        print(f"-✅Archivo generado: {path}")
        return True
    except PermissionError:
        print(f"-❌No se pudo guardar {path}: el archivo está abierto o no hay permisos. Ciérrelo e intente de nuevo.")
        return False
    except Exception as e:
        print(f"-❌No se pudo guardar el archivo: {e}")
        return False
    finally:
        if temporary_path is not None and temporary_path.exists():
            try:
                temporary_path.unlink()
            except OSError:
                pass
    
def out(source_path, filename, extension=".xlsx", *, output_dir=None, add_date=True):
    """Construye una ruta de salida estable junto al archivo de entrada.

    `filename` es el nombre base deseado. La fecha se añade por defecto. La ruta
    puede existir: `save_excel` reemplaza el resultado anterior al guardarlo.
    """
    source = Path(source_path).expanduser().resolve()
    destination = Path(output_dir).expanduser().resolve() if output_dir else source.parent
    destination.mkdir(parents=True, exist_ok=True)

    name = Path(filename).stem.strip()
    if not name:
        raise ValueError("El nombre base del archivo de salida no puede estar vacío.")
    suffix = extension if extension.startswith(".") else f".{extension}"
    if add_date:
        name = f"{name}_{datetime.now():%d.%m.%y}"

    return destination / f"{name}{suffix}"


def legacy_out(source_path):
    """Compatibilidad para reportes antiguos que generan un archivo ``_OK``."""
    source = Path(source_path).expanduser().resolve()
    return out(source, f"{source.stem}_OK", add_date=False)
