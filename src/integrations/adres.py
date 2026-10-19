import pandas as pd
import re
import requests
from io import BytesIO
from bs4 import BeautifulSoup
from urllib.parse import urljoin, urlparse

def ips_habilitadas():
    pagina = "https://www.adres.gov.co/ips-y-proveedores/giro-directo/regimen-subsidiado"

    print("\t-Buscando el archivo más reciente de ADRES...")

    # Descargar página
    respuesta = requests.get(
        pagina,
        timeout=30,
        headers={
            "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/115.0.0.0 Safari/537.36"
        )})
    respuesta.raise_for_status()

    soup = BeautifulSoup(respuesta.text, "html.parser")

    archivos = []

    # Buscar todos los enlaces de la página
    for enlace in soup.find_all("a", href=True):

        href = enlace["href"]
        texto = enlace.get_text(" ", strip=True)

        url_archivo = urljoin(pagina, href)

        # Revisar si parece ser un Excel
        if ".xlsx" in url_archivo.lower() or ".xls" in url_archivo.lower():

            # Buscar año y mes
            texto_completo = f"{texto} {url_archivo}"
            meses = {
                "enero": 1,
                "febrero": 2,
                "marzo": 3,
                "abril": 4,
                "mayo": 5,
                "junio": 6,
                "julio": 7,
                "agosto": 8,
                "septiembre": 9,
                "octubre": 10,
                "noviembre": 11,
                "diciembre": 12
            }

            texto_minuscula = texto_completo.lower()

            año_encontrado = re.search(r"20\d{2}", texto_minuscula)

            if not año_encontrado:
                continue

            año = int(año_encontrado.group())

            mes = None

            for nombre_mes, numero_mes in meses.items():
                if nombre_mes in texto_minuscula:
                    mes = numero_mes
                    break

            if mes is not None:
                archivos.append({
                    "año": año,
                    "mes": mes,
                    "nombre": texto,
                    "url": url_archivo
                })

    if not archivos:
        raise Exception(
            "No se encontraron archivos Excel en la página de ADRES."
        )

    # Ordenar por año y mes
    archivos.sort(
        key=lambda x: (x["año"], x["mes"]),
        reverse=True
    )

    ultimo = archivos[0]

    print(f"\t-Archivo encontrado: {ultimo['nombre']}")
    print(f"\t-URL: {ultimo['url']}")

    # Descargar Excel
    respuesta_archivo = requests.get(
        ultimo["url"],
        timeout=60,
        headers={
            "User-Agent": (
                        "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                        "AppleWebKit/537.36 (KHTML, like Gecko) "
                        "Chrome/115.0.0.0 Safari/537.36"
            )
        }
    )

    respuesta_archivo.raise_for_status()

    # Convertir directamente a DataFrame
    df = pd.read_excel(BytesIO(respuesta_archivo.content))
    df.columns = df.iloc[4]
    df = df[5:].copy()
    df.reset_index(drop=True, inplace=True)

    print(f"\t-Archivo cargado correctamente: {len(df):,} registros")

    return df, ultimo