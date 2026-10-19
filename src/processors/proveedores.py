import re
import pandas as pd
from termcolor import colored
from ..common.excel import load_data

def extract_data(data):
    if 1 not in data.columns or 13 not in data.columns:
        print("El archivo no tiene las columnas esperadas para el reporte de proveedores.")
        return pd.DataFrame()

    data_result = []
    nit_actual = None
    nit_pattern = re.compile(r'^\s*(\d{7,10}(?:-\d)?)\s*-\s+(.*)$')
    number_pattern = re.compile(r'^-?\d+(?:\.\d+)?$')
    tipos_validos = [
            '01-Factura de Compra',
            '03-N.Cre A Factura',
            '04-N.Deb A Factura'
        ]

    for _, row in data.iterrows():
        celda_a1 = ' '.join(str(row[1]).replace('\xa0', ' ').split()).strip()
        celda_N1 = ' '.join(str(row[13]).replace('\xa0', ' ').split()).strip()

        match_nit = nit_pattern.match(celda_a1)
        is_number = bool(number_pattern.match(celda_N1))

        if match_nit and is_number:
            nit_actual = match_nit.group(1)
            name = match_nit.group(2)
            #print(name)
        elif nit_actual and not celda_a1.upper().startswith('TOTAL') and not is_number:
            fila_glosa = [nit_actual] + [name] + row.tolist()
            data_result.append(fila_glosa)

    if not data_result:
        return pd.DataFrame()  # Devuelve DataFrame vacío si no hay resultados

    df_final = pd.DataFrame(data_result)
    df_final = df_final[df_final[5].isin(tipos_validos)] # Eliminat filas con tipos no válidos
    df_final.drop(columns=[6, 10, 11, 12], inplace=True, errors='ignore') #Eliminar columnas innecesarias
    return df_final

def process_dataframe(df_pagos):
    print("\t-Separando Prefijo y # de factura.")
    if 'PREFIJ. #FACTURA' in df_pagos.columns:
        # 1. Limpieza total
        col = df_pagos['PREFIJ. #FACTURA'].astype(str)
        col = col.str.replace(u'\u00A0', '', regex=False)     # NBSP
        col = col.str.replace(r'\s+', '', regex=True)         # todos los espacios
        col = col.str.replace(r'-+', '-', regex=True)         # guiones múltiples → uno

        # Actualizar columna limpia
        df_pagos['PREFIJ. #FACTURA'] = col

        # 2. Ahora sí extraer
        prefijo_num_split = col.str.extract(r'^([A-Za-z0-9]+-)?(\d+)$')

        if not prefijo_num_split.empty and prefijo_num_split.shape[1] == 2:
            df_pagos['PREFIJ'] = prefijo_num_split[0]

            df_pagos['#FACTURA'] = pd.to_numeric(prefijo_num_split[1], errors='coerce').astype(pd.Int64Dtype()).astype(str)
            df_pagos['#FACTURA'] = df_pagos['#FACTURA'].replace('<NA>', pd.NA)
        else:
            df_pagos['PREFIJ'] = pd.NA
            df_pagos['#FACTURA'] = pd.NA

    if 'PREFIJ' in df_pagos.columns:
        df_pagos['PREFIJ'] = df_pagos['PREFIJ'].str.replace('-', '', regex=False)

    print("\t-Formateando fechas.")
    if 'FECHA' in df_pagos.columns:
        df_pagos['FECHA'] = pd.to_datetime(df_pagos['FECHA'], format='%Y-%m-%d', errors='coerce').dt.date
        df_pagos['FECHA'] = df_pagos['FECHA'].replace({'NaT': pd.NA, 'None': pd.NA})

    return df_pagos

def fomplus(filepath):

    print(f"\tArchivo cargado: {colored(filepath.name, 'green')}")
    df = load_data(filepath, [])
    if df is None:
        return None

    df_final = extract_data(df)
    if df_final.empty:
        print("No se encontraron datos válidos en el archivo.")
        return pd.DataFrame()

    columns_base = ['NIT','PROVEEDOR','FECHA','DOCUMENTO', 'PREFIJ. #FACTURA', 'TIPOMOV', 'TC', 'DEBITO','CREDITO']
    df_pagos = df_final.copy()
    df_pagos.columns = columns_base
    df_pagos = process_dataframe(df_pagos)
    final_orden = ['NIT','FECHA','DOCUMENTO','PREFIJ. #FACTURA','PREFIJ','#FACTURA','TIPOMOV','TC','DEBITO','CREDITO']
    df_pagos = df_pagos.reindex(columns=final_orden)

    return df_pagos
