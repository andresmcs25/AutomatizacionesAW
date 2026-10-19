import re
import pandas as pd
from datetime import datetime
from pathlib import Path
from termcolor import colored

from ..common.excel import load_data

def extract_invoice_data(data, invoice_prefixes=("FAC",)):
    """Extrae filas de factura asociadas al NIT anterior.

    ``invoice_prefixes`` permite que cada flujo defina qué tipos de fila debe
    procesar. Por defecto solo se incluyen FAC para conservar la depuración.
    """
    prefixes = tuple(str(prefix).strip().upper() for prefix in invoice_prefixes if str(prefix).strip())
    data_result = []
    nit_actual = None
    name = None

    for index, row in data.iterrows():
            celda_a1 = str(row[1]).replace('\xa0', ' ').strip()
            celda_a1 = ' '.join(celda_a1.split())
            if re.match(r'^(\d+-?\d+)\s*=>', celda_a1):
                match = re.match(r'^(\d+-?\d+)\s*=>\s*(.*)', celda_a1)
                if match:
                    nit_actual = match.group(1)
                    name = match.group(2)
                else:
                    nit_actual = None

            elif (nit_actual is not None
                  and any(celda_a1.upper().startswith(prefix) for prefix in prefixes)
                  and "=>" not in celda_a1):
                fila_factura = [nit_actual]  + [name] + row.tolist()
                data_result.append(fila_factura)

    return data_result

def process_dataframe(df_cartera):
    if 'NIT' in df_cartera.columns:
        nit_split = df_cartera['NIT'].str.split('-', expand=True)

        if nit_split.shape[1] >= 2:
            df_cartera['NIT_'] = nit_split[0]
            df_cartera['DV'] = nit_split[1]
        elif nit_split.shape[1] == 1:
            df_cartera['NIT_'] = nit_split[0]
            df_cartera['DV'] = pd.NA
        else:
            df_cartera['NIT_'] = pd.NA
            df_cartera['DV'] = pd.NA

    if 'Prefij. #Documento' in df_cartera.columns:
        prefijo_num_split = df_cartera['Prefij. #Documento'].astype(str).str.extract(r'^01-(.*?)-(\d+)$')

        if not prefijo_num_split.empty and prefijo_num_split.shape[1] == 2:
            df_cartera['Pref'] = prefijo_num_split[0]

            df_cartera['Numero'] = pd.to_numeric(prefijo_num_split[1], errors='coerce').astype(pd.Int64Dtype()).astype(str)
            df_cartera['Numero'] = df_cartera['Numero'].replace('<NA>', pd.NA)
        else:
            df_cartera['Pref'] = pd.NA
            df_cartera['Numero'] = pd.NA

    if 'Fecha_Fac' in df_cartera.columns:
        df_cartera['Fecha_Fac'] = pd.to_datetime(df_cartera['Fecha_Fac'], errors='coerce')
        df_cartera['Fecha_Fac'] = df_cartera['Fecha_Fac'].dt.strftime('%Y-%m-%d')
        df_cartera['Fecha_Fac'] = df_cartera['Fecha_Fac'].replace({'NaT': pd.NA, 'None': pd.NA})
    if 'Fecha_Ven' in df_cartera.columns:
        df_cartera['Fecha_Ven'] = pd.to_datetime(df_cartera['Fecha_Ven'], errors='coerce')
        df_cartera['Fecha_Ven'] = df_cartera['Fecha_Ven'].dt.strftime('%Y-%m-%d')
        df_cartera['Fecha_Ven'] = df_cartera['Fecha_Ven'].replace({'NaT': pd.NA, 'None': pd.NA})

    return df_cartera

def validate_and_drop_columns(df_cartera):
    columns_venc = ['Por Vencer', '1-30 Dias', '31 - 60 Dias', '61 - 90 Dias', 'Mas 90 Dias']
    column_total = 'Valor Total'
    drop_columns_flag = False

    required_validation_columns = columns_venc + [column_total]
    if all(col in df_cartera.columns for col in required_validation_columns):
        for col in required_validation_columns:
            df_cartera[col] = pd.to_numeric(df_cartera[col], errors='coerce')

        grand_total_aging = df_cartera[columns_venc].sum().sum()
        grand_total_valor = df_cartera[column_total].sum()
        overall_difference = grand_total_aging - grand_total_valor
        tolerance = 0.001

        print("\t📢 Validacion de Totales.")
        print(f"\t-Total columnas carteras: {grand_total_aging:.2f}")
        print(f"\t-Valor Total: {grand_total_valor:.2f}")
        print(f"\t-Diferencia: {overall_difference:.2f}")

        if abs(overall_difference) < tolerance:
            print("\t✅ Validacion: CORRECTO (Totales coinciden).")
            drop_columns_flag = True
        else:
            print("\t🚫 Validacion: FALLIDO (Totales no coinciden).")
    else:
        missing_cols = [col for col in required_validation_columns if col not in df_cartera.columns]
        print(f"\n❌ Warning: Saltando validacion no existen columnas: {missing_cols}")

    if drop_columns_flag:
        cols_to_drop_actual = [col for col in columns_venc if col in df_cartera.columns]
        if cols_to_drop_actual:
            df_cartera.drop(columns=cols_to_drop_actual, inplace=True)
    return df_cartera

def reorder_columns(df_cartera, final_column_order):
    final_column_order_existing = [col for col in final_column_order if col in df_cartera.columns]
    df_cartera = df_cartera[final_column_order_existing]

    return df_cartera

def cartera(filepath, output_dir=None, invoice_prefixes=("FAC",)):
    """Carga la cartera desde `filepath`, aplica limpieza y guarda el resultado en Excel.

    Args:
        filepath (str): Ruta al archivo de entrada Excel.
        cols_drop (list|None): Lista de columnas (por etiqueta o índice) a eliminar.
    """
    filepath = Path(filepath)
    output_dir = Path(output_dir) if output_dir is not None else filepath.parent
    print(f"\t-Archivo cargado: {colored(filepath.name, 'green')}")
    data = load_data(filepath,[0,2,15,17])
    if data is None:
        return

    data_result = extract_invoice_data(data, invoice_prefixes=invoice_prefixes)
    if not data_result:
        print("❌ No se encontraron datos de factura para procesar")
        return

    columns_base = ['Tipo', 'Prefij. #Documento', 'Fecha_Fac', 'Fecha_Ven', 'Por Vencer',
                    '1-30 Dias', '31 - 60 Dias', '61 - 90 Dias', 'Mas 90 Dias', 'Valor Total']
    columns_for_df_creation = ['NIT', 'Proveedor'] + columns_base

    max_cols_in_data = max(len(row) for row in data_result)
    if max_cols_in_data > len(columns_for_df_creation):
        columns_for_df_creation += [f'col_{i}' for i in range(len(columns_for_df_creation), max_cols_in_data)]

    df_cartera = pd.DataFrame(data_result, columns=columns_for_df_creation[:max_cols_in_data])

    df_cartera = process_dataframe(df_cartera)
    df_cartera = validate_and_drop_columns(df_cartera)
    final_column_order = ['NIT','NIT_', 'DV', 'Proveedor','Prefij. #Documento', 'Pref', 'Numero','Fecha_Fac','Valor Total']
    df_cartera = reorder_columns(df_cartera, final_column_order)
    df_cartera = df_cartera.rename(columns={'Prefij. #Documento':'Factura','Valor Total':'ValorCartera','Fecha_Fac':'FechaCau'})

    fecha_actual = datetime.now().strftime("%d.%m.%y")
    name = f"Depuracion_{fecha_actual}.xlsx"

    out = output_dir / name

    return df_cartera, out
