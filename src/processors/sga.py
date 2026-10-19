import pandas as pd
import os

def process_sga_data(csv_paths, columns_to_keep):
    if not csv_paths:
        print("\t-No se recibieron rutas de archivos CSV.")
        return None

    sga_dfs = []

    for path in csv_paths:
        try:
            print(f"\tProcesando archivo: {os.path.basename(path)}")
            with open(path, "r", encoding="latin1", errors="ignore") as f:

                # Primera línea = encabezados
                header = f.readline().rstrip("\n\r").split("|")
                header = header[:50]
                rows = []

                for line in f:
                    if not line.strip():
                        continue

                    values = line.rstrip("\n\r").split("|")
                    values = values[:50]

                    if len(values) < 50:
                        values += [""] * (50 - len(values))

                    row = [values[i] for i in columns_to_keep]
                    rows.append(row)

            # Encabezados correspondientes a las columnas seleccionadas
            selected_columns = [header[i] for i in columns_to_keep]

            df_temp = pd.DataFrame(rows,columns=selected_columns)
            sga_dfs.append(df_temp)
            print(f"\t-✅ Cargado correctamente "f"({len(df_temp)} filas, {len(df_temp.columns)} columnas)")

        except Exception as e:
            print(f"\t-🚫 Error leyendo "f"{os.path.basename(path)}: {e}")

    if not sga_dfs:
        print("\t-No se pudo cargar ningún archivo SGA.")
        return None

    combined_sga = pd.concat(sga_dfs,ignore_index=True)
    combined_sga = clean_sga(combined_sga)
    print(f" 📊 Total registros combinados del SGA: "f"{len(combined_sga)}")

    return combined_sga

def clean_sga(df):
    if df is None:
        print("❌ El procesamiento de los datos SGA falló.")
        return None

    print("\tAjuste columnas de 'NUMEROFACTURA' para separar Prefijo y # de factura.")

    required = [
        'NIT', 'NUMEROFACTURA', 'NoContrato', 'VALORFACTURA', 'GLOSA', 'IDLOTE',
        'FECHARADICACION', 'FECHAFACTURA',
        'FECHA_INICIAL_PRESTACION_SERVICIO', 'FECHA_REGISTRO', 'ID_FACTURA',
    ]
    missing = [column for column in required if column not in df.columns]
    if missing:
        raise ValueError(
            "El archivo SGA no contiene las columnas requeridas: " + ", ".join(missing)
        )

    df['NoContrato'] = df['NoContrato'].astype(str).str.strip()
    df['NoContrato'] = df['NoContrato'].replace('','URGENCIA')
    df[['Pref(O)', '#Factura']] = df['NUMEROFACTURA'].astype(str).str.extract(r'^(.*?)(\d+)$')
    df['#Factura'] = pd.to_numeric(df['#Factura'], errors='coerce').astype(pd.Int64Dtype()).astype(str).replace('<NA>', pd.NA)
    df['NIT_Pref_Numero'] = df['NIT'] + ' ' + df['Pref(O)'] + ' ' + df['#Factura']
    df['NIT_Numero'] = df['NIT'] + ' ' + df['#Factura']
    print("\tAjuste realizado con Exito")

    numeric = ['VALORFACTURA','GLOSA','IDLOTE']
    df[numeric] = df[numeric].apply(pd.to_numeric, errors='coerce')
    date = ['FECHARADICACION','FECHAFACTURA','FECHA_INICIAL_PRESTACION_SERVICIO']
    df[date] = df[date].apply(lambda x: pd.to_datetime(x, format='%Y-%m-%d', errors='coerce').dt.date)
    df['FECHA_REGISTRO'] = pd.to_datetime(df['FECHA_REGISTRO'], format='%Y-%m-%d %H:%M:%S', errors='coerce')
    df = df.rename(columns={
        'FECHARADICACION':'FechaRad',
        'FECHAFACTURA':'FechaFac',
        'FECHA_INICIAL_PRESTACION_SERVICIO':'FechaPres',
        'ID_FACTURA':'ID',
        'IDLOTE':'Lote'
    })

    return df
