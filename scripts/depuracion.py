import argparse
import sys
from pathlib import Path
import pandas as pd
from termcolor import colored

PROJECT_DIR = Path(__file__).resolve().parent.parent
if str(PROJECT_DIR) not in sys.path:
    sys.path.insert(0, str(PROJECT_DIR))

from src.common.excel import load_data, load_file, save_excel
from src.integrations.adres import ips_habilitadas
from src.processors.cartera import cartera
from src.processors.sga import process_sga_data
from src.processors.proveedores import fomplus


def run(input_dir: Path, sga_dir: Path) -> None:
    INPUT = Path(input_dir).resolve()
    SGA = Path(sga_dir).resolve()
    OUTPUT = INPUT
    INPUT.mkdir(parents=True, exist_ok=True)
    SGA.mkdir(parents=True, exist_ok=True)
    print("| 🔄 INICIANDO DEPURACIÓN |")
    print("Seleccionando archivo CARTERA")

    filepath = INPUT / 'Cartera.xlsx'
    result = cartera(filepath, output_dir=OUTPUT)

    if result is None:
        print("❌ No fue posible procesar la cartera. Finalizando proceso...")
        exit()

    df_result, out_path = result

    if 'Pref' in df_result.columns:
        df_result['Pref'] = df_result['Pref'].astype(str).str.strip()
        df_result['Pref'] = df_result['Pref'].replace(' ','')

    df_result.loc[df_result['NIT'] == '900589110','NIT'] = '900589110-5'
    df_result.loc[df_result['NIT'] == '900138649','NIT'] = '900138649-8'
    df_result.loc[df_result['NIT'] == '900959051','NIT'] = '900959051-7'
    df_result.loc[df_result['NIT'] == '900589110-5','DV'] = '5'
    df_result.loc[df_result['NIT'] == '900138649-8','DV'] = '8'
    df_result.loc[df_result['NIT'] == '900959051-7','DV'] = '7'

    if all(col in df_result.columns for col in ['NIT_', 'Pref', 'Numero']):
        df_result['NIT_Pref_Numero'] = df_result['NIT_'] + ' ' + df_result['Pref'] + ' ' + df_result['Numero']

    print("\nSeleccionado archivo TIPO CUENTA")
    filepath = INPUT / 'TC.Xlsx'
    print(f"\t-Archivo cargado: {colored(filepath.name, 'green')}")

    tipoCuenta = load_data(filepath,[])
    tipoCuenta = tipoCuenta[[6,19,20,25]]
    tipoCuenta.columns = tipoCuenta.iloc[0]
    tipoCuenta = tipoCuenta[4:]
    tipoCuenta.reset_index(drop=True, inplace=True)
    column_base = ['NIT','Pref', 'Numero','TC']
    tipoCuenta.columns = column_base

    # Duplicar la columna 'NIT'
    tipoCuenta['NIT_'] = tipoCuenta['NIT']
    # Separar el dígito de verificación del NIT
    nit_split = tipoCuenta['NIT_'].astype(str).str.split('-', expand=True)
    if nit_split.shape[1] >= 2:
        tipoCuenta['NIT_'] = nit_split[0]
        tipoCuenta['DV'] = nit_split[1]
    elif nit_split.shape[1] == 1:
        tipoCuenta['NIT_'] = nit_split[0]
        tipoCuenta['DV'] = pd.NA
    else:
        tipoCuenta['NIT_'] = pd.NA
        tipoCuenta['DV'] = pd.NA
    tipoCuenta['NIT_'] = tipoCuenta['NIT_'].astype(str).str.replace('-', '', regex=False)

    # Eliminar espacios en blanco de la columna 'Pref'
    tipoCuenta['Pref'] = (tipoCuenta['Pref'].fillna('').astype(str).str.strip().str.replace(' ', '', regex=False))
    tipoCuenta['Numero'] = pd.to_numeric(tipoCuenta['Numero'], errors='coerce').astype(pd.Int64Dtype()).astype(str).replace('<NA>', pd.NA)
    # Concatenar columnas NIT_, Pref, Numero
    tipoCuenta['Pref'] = tipoCuenta['Pref'].astype(str).replace('nan', '')
    tipoCuenta['NIT_Pref_Numero'] = tipoCuenta['NIT_'] + ' ' + tipoCuenta['Pref'] + ' ' + tipoCuenta['Numero']

    print("\n|  MERGE CARTERA vs TIPOcUENTA  |")
    if 'NIT_Pref_Numero' in df_result.columns and 'NIT_Pref_Numero' in tipoCuenta.columns:
        tipoCuenta_subset = tipoCuenta[['NIT_Pref_Numero', 'TC']].copy()
        df_result = pd.merge(df_result, tipoCuenta_subset, on='NIT_Pref_Numero', how='left')
        df_result.drop(columns=['NIT_Pref_Numero'], inplace=True)
        print("\t-✅ Merge realizado y columna 'TC' agregada con exito")
    else:
        print("\t-❌ Warning: No se pudo realizar el merge. Las columnas 'NIT_Pref_Numero' no existen en ambos DataFrames.")

    # SGA
    print("\nSeleccionando archivos de SGA")

    csv_paths = list((SGA).glob("*.csv"))

    columns_needed = [0,1,3,4,5,6,7,8,9,10,18,22,23,30,33,34,41,42,48]
    df_sga = process_sga_data(csv_paths,columns_needed)

    # Filtrado por años deseados o completo.
    df_result['FechaCau'] = pd.to_datetime(df_result['FechaCau'], errors='coerce')
    anios_disponibles = sorted(int(a) for a in df_result['FechaCau'].dropna().dt.year.unique())
    print(f"\nAños disponibles en los datos: {anios_disponibles}")

    request = input("\n¿Con qué años desea trabajar? (ejemplo: 2023,2024,2025 o deje vacío para todos): ").strip()

    # Convertir a lista de enteros si se escribió algo
    if request:
        try:
            anios_seleccionados = [int(a.strip()) for a in request.split(',') if a.strip().isdigit()]
            print(f"\nFiltrando registros por años: {anios_seleccionados}...")

            # Convertir a datetime y filtrar
            df_result['FechaCau'] = pd.to_datetime(df_result['FechaCau'], format='%Y-%m-%d', errors='coerce')
            df_result = df_result[df_result['FechaCau'].dt.year.isin(anios_seleccionados)]
            print(f"✅ Registros filtrados por años {anios_seleccionados}: {len(df_result)}")
        except Exception as e:
            print(f"⚠️ Error al procesar los años: {e}. Se usarán todos los datos.")
    else:
        print("\nNo se aplicó filtro por años; se usarán todos los registros.")

    df_result['FechaCau'] = pd.to_datetime(df_result['FechaCau'], format='%Y-%m-%d', errors='coerce').dt.date

    # Hacer el merge entre cartera y SGA
    df_result['NIT_'] = df_result['NIT_'].astype(str)
    df_sga['NIT'] = df_sga['NIT'].astype(str)

    # Identificar registros que no están en SGA
    df_adm = df_result[~df_result['NIT_'].isin(df_sga['NIT'])].copy()
    df_cartera = df_result[df_result['NIT_'].isin(df_sga['NIT'])].copy()

    print(f"\nResultados del cruce con SGA:")
    print(f"\t-Total registros en Cartera: {len(df_result)}")
    print(f"\t-Registros encontrados en SGA: {len(df_cartera)}")
    print(f"\t-Registros NO encontrados en SGA: {len(df_adm)}")

    df_cartera['NIT_Pref_Numero'] = df_cartera['NIT_'] + ' ' + df_cartera['Pref'] + ' ' + df_cartera['Numero']
    df_cartera['NIT_Numero'] = df_cartera['NIT_'] + ' ' + df_cartera['Numero']

    # MERGE
    print("\n|  MERGE CARTERA VS SGA  |")
    print("\nPrimer merge realizado con NIT_Pref_Numero")
    sga_subset = df_sga[['NIT_Pref_Numero', 'ID','Pref(O)','Lote','FechaRad','FechaFac','TIPO','NoContrato','VALORFACTURA','GLOSA','FechaPres','MUNICIPIO','REGIMEN','ESTADO','FECHA_REGISTRO']].copy()

    df_cartera = df_cartera.set_index("NIT_Pref_Numero")
    sga_subset = sga_subset.set_index("NIT_Pref_Numero")
    df_cartera = df_cartera.join(sga_subset, how="left")
    df_cartera.reset_index(inplace=True)

    print(f"Resultados primer merge:")
    print(f"\t-Registros con ID encontrado: {df_cartera['ID'].notna().sum()}")
    print(f"\t-Registros sin ID: {df_cartera['ID'].isna().sum()}")
    data = df_cartera['ID'].notna().sum()

    print("\nSegundo merge realizado con NIT_Numero")

    duplicados = df_sga[df_sga.duplicated(subset='NIT_Numero', keep=False)]
    sga_unique = df_sga[~df_sga['NIT_Numero'].isin(duplicados['NIT_Numero'])].copy()

    sga_subset = sga_unique[['NIT_Numero','ID','Pref(O)','Lote','FechaRad','FechaFac','TIPO','NoContrato','VALORFACTURA','GLOSA','FechaPres','MUNICIPIO','REGIMEN','ESTADO','FECHA_REGISTRO']].copy()

    df_cartera.set_index("NIT_Numero", inplace=True)
    sga_subset.set_index("NIT_Numero", inplace=True)
    df_cartera.update(sga_subset,overwrite=False)
    df_cartera.reset_index(inplace=True)

    data2 = df_cartera['ID'].notna().sum()
    resultado = data2 - data

    print(f"Resultados segundo merge:")
    print(f"\t-Registros adicionales encontrados por NIT_Numero: {resultado}")
    print(f"\t-Total registros con ID: {df_cartera['ID'].notna().sum()}")
    print(f"\t-Registros que siguen sin ID: {df_cartera['ID'].isna().sum()}")

    df_cartera.drop(columns=['NIT_Pref_Numero', 'NIT_Numero'], inplace=True, errors='ignore')

    registros_sin_id = df_cartera[df_cartera['ID'].isna()].copy()
    df_cartera = df_cartera[df_cartera['ID'].notna()].copy()

    if registros_sin_id.empty:
      print("\nTodos los registros tiene coincidencia despues de cruzar con SGA.")
    else:
      registros_sin_id.drop(columns=['ID','Pref(O)','Lote','FechaRad','FechaFac','TIPO','NoContrato','VALORFACTURA','GLOSA','FechaPres','MUNICIPIO','REGIMEN','ESTADO','FECHA_REGISTRO'], inplace=True)
      out = OUTPUT / "registros_sin_id.xlsx"
      if not save_excel(out, {'Registros sin ID': registros_sin_id}):
          raise SystemExit(1)
      print("⚠️ Revise y corrija manualmente los datos que puedan ayudar a encontrar coincidencias (NIT, prefijo, número, etc.).")

      # Pausa para que el usuario modifique el archivo
      input("\nUna vez haya terminado de hacer las correcciones en Excel, presione ENTER para continuar...")

      print("Seleccina el archivo corregido de 'registros_sin_id.xlsx'...")
      df_sin_id = load_file()

      if not df_sin_id:
        print("❌ No se seleccionó el archivo corregido. Finalizando proceso...")
      else:
        print(f"\tArchivo cargado: {colored(df_sin_id.name, 'green')}")
        df_sin_id = pd.read_excel(df_sin_id)

        df_sin_id['Pref'] = df_sin_id['Pref'].astype(str).replace('nan', '')
        df_sin_id[['NIT_','Pref','Numero','DV','TC']] = df_sin_id[['NIT_','Pref','Numero','DV','TC']].astype(str)
        df_sin_id['NIT_Pref_Numero'] = df_sin_id['NIT_'] + ' ' + df_sin_id['Pref'] + ' ' + df_sin_id['Numero']
        df_sin_id['FechaCau'] = pd.to_datetime(df_sin_id['FechaCau'], format='%Y-%m-%d', errors='coerce').dt.date

        print("\nReintentando merge entre CARTERA vs SGA")

        sga_subset = df_sga[['NIT_Pref_Numero', 'ID','Pref(O)','Lote','FechaRad','FechaFac','TIPO','NoContrato','VALORFACTURA','GLOSA','FechaPres','MUNICIPIO','REGIMEN','ESTADO','FECHA_REGISTRO']].copy()

        df_sin_id = df_sin_id.set_index("NIT_Pref_Numero")
        sga_subset = sga_subset.set_index("NIT_Pref_Numero")
        df_sin_id = df_sin_id.join(sga_subset, how="left")
        df_sin_id.reset_index(inplace=True)

        print(f"Resultados tercer merge:")
        print(f"\t-Registros con ID encontrado: {df_sin_id['ID'].notna().sum()}")
        print(f"\t-Registros siguen sin ID y van a adm: {df_sin_id['ID'].isna().sum()}")

        registros_sin_id = df_sin_id[df_sin_id['ID'].isna()].copy()
        df_sin_id = df_sin_id[df_sin_id['ID'].notna()].copy()
        df_cartera = pd.concat([df_cartera, df_sin_id], ignore_index=True)

        if registros_sin_id.empty:
          print("\nTodos los registros tiene coincidencia despues de cruzar con SGA.")
        else:
          print(f"\nQuedaron {len(registros_sin_id)} registros sin coincidencia después de todos los merges.")
          df_adm = pd.concat([df_adm, registros_sin_id], ignore_index=True)
          columns = ['NIT_Pref_Numero', 'ID','Pref(O)','Lote','FechaRad','FechaFac','TIPO','NoContrato','VALORFACTURA','GLOSA','FechaPres','MUNICIPIO','REGIMEN','ESTADO','FECHA_REGISTRO']
          df_adm.drop(columns=columns, inplace=True)

    df_cartera.drop(columns=['NIT_Pref_Numero'], inplace=True, errors='ignore')

    df_cartera = df_cartera.sort_values(
      by=['NIT_', 'FechaCau', 'Numero'],
      ascending=[True, True, True]
      ).reset_index(drop=True)

    request = input("\n¿Desea separar una hoja para las facturas que están en Tesorería? (s/n): ").strip().lower()

    if request == 's':
        #Filtro por Estado = Tesoreria y Pago, Tipo = (Que no sea Fome o CovidAdres) y tipoCuenta = (Que no sea 55 y 60)
        print("\nFiltrando registros para hoja Tesorería...")
        tesoreria = df_cartera[
            (df_cartera['ESTADO'].isin(['Tesoreria','Pago'])) &
            (~df_cartera['TIPO'].isin(['Fome', 'Covid_Adres'])) &
            (~df_cartera['TC'].isin(['55', '60']))
        ].copy()

        print("Obteniendo IPS habilitadas")
        df_habilitadas, info = ips_habilitadas()
        print("\nMarcando IPS habilitadas")
        df_habilitadas = set(df_habilitadas['NIT'].astype(str).str.strip())
        tesoreria['GD'] = (
            tesoreria['REGIMEN'].astype(str).str.strip().str.upper().eq('SUBSIDIADO') &
            tesoreria['NIT_'].astype(str).str.strip().isin(df_habilitadas) &
            ~tesoreria['TIPO'].astype(str).str.strip().str.upper().eq('PPTO.MAX')
        ).astype(int)
        print("\t-Completo.")

        print("Marcando Glosas causadas con Nota Crédito")
        file = INPUT / 'Fomplus.xlsx'
        df_fomplus = fomplus(file)
        df_fomplus = df_fomplus[df_fomplus['DOCUMENTO'].astype(str).str.startswith(('NCGC-', 'NCGL-'))].copy()
        # 1. Crear un set de claves únicas "NIT_FACTURA" desde df_fomplus
        fomplus_keys = set(df_fomplus['NIT'].astype(str).str.strip() + '_' +df_fomplus['#FACTURA'].astype(str).str.strip())

        # 2. Crear la clave equivalente en tesoreria
        tesoreria_keys = (tesoreria['NIT'].astype(str).str.strip() + '_' +tesoreria['Numero'].astype(str).str.strip())

        # 3. Asignar 1 si la clave existe en df_fomplus, 0 en caso contrario
        tesoreria['NC'] = tesoreria_keys.isin(fomplus_keys).astype(int)
        #save_excel(INPUT / "temp.xlsx",{'Fomplus': df_fomplus})
        print("\t-Completo.")

        print("Marcando Glosas que ya están en Tesorería")
        file = INPUT / 'Radicados Glosa.xlsx'
        df_glosas = pd.read_excel(file)
        lotes_set = set(df_glosas.iloc[:, 2].dropna())
        tesoreria['GL'] = (tesoreria['Lote'].isin(lotes_set)).astype(int)
        print("\t-Completo.")

        print("\nGuardando archivo final con las hojas necesarias (Adm / Completo / Tesorería):")
        if not save_excel(out_path, {'Admin': df_adm,'Completo': df_cartera, 'Tesoreria': tesoreria}):
            raise SystemExit(1)
    else:
        print(f"\nGuardando archivo final con las hojas necesarias (Adm / Completo): {out_path}")
        if not save_excel(out_path, {'Admin': df_adm,'Completo': df_cartera}):
            raise SystemExit(1)

    print("\n| 🏁 PROCESO FINALIZADO |")


def main() -> int:
    parser = argparse.ArgumentParser(description="Depuración de cartera")
    parser.add_argument("--cartera-dir", type=Path, default=PROJECT_DIR / "folders" / "Cartera")
    parser.add_argument("--sga-dir", type=Path, default=PROJECT_DIR / "folders" / "SGA")
    args = parser.parse_args()
    run(args.cartera_dir, args.sga_dir)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

