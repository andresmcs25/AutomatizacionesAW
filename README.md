# Proyecto de procesamiento

Aplicación local para reunir y ejecutar scripts de procesamiento de archivos. El flujo existente de depuración de cartera es el primer proceso integrado; la estructura permite añadir otros procesos sin mezclar sus reglas con el punto de entrada.

## Carpetas de trabajo

```text
folders/
├── Cartera/   # Cartera.xlsx, TC.Xlsx y auxiliares del proceso
└── SGA/       # Exportaciones CSV de SGA (pueden ser varias)
scripts/       # Flujos ejecutables por proceso
  depuracion.py # Flujo de cartera
  cartera.py # Procesa una cartera independiente (FAC y ANT)
  proveedores.py # Flujo de proveedores/Fomplus
  sga.py # Consolida exportaciones CSV de SGA
app.py         # Menú principal de consola
src/
├── common/       # Funciones compartidas (carga, selección y guardado de Excel)
├── integrations/ # Fuentes externas como ADRES
└── processors/   # Funciones reutilizables y flujos por fuente
    ├── cartera.py
    ├── proveedores.py
    └── sga.py
```

El proceso lee `Cartera.xlsx` y `TC.Xlsx` desde `folders/Cartera`, y combina todos los CSV de `folders/SGA`. Si se activa la hoja de Tesorería, también busca `Fomplus_31.08.26.xlsx` y `Radicados Glosa.xlsx` en `folders/Cartera`. El Excel de resultado y `registros_sin_id.xlsx` se guardan en `folders/Cartera`, al lado de los archivos usados.

## Ejecución de la aplicación

Instala las dependencias y abre el menú en la ventana de comandos:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python app.py
```

«Procesar cartera (FAC y ANT)» abre un selector para elegir el Excel. Procesa las filas que empiezan por `FAC` o `ANT` y guarda `Cartera_Procesada_DD.MM.AA.xlsx` junto al archivo seleccionado. Si el resultado del mismo día ya existe, lo reemplaza. Este flujo reutiliza el procesador de cartera; la depuración conserva el valor predeterminado, que procesa solamente filas `FAC`.

El proceso Proveedores / Fomplus abre un selector para elegir el Excel de entrada y guarda `Fomplus_DD.MM.AA.xlsx` en la misma carpeta del archivo elegido. Así el resultado queda junto a su fuente y no requiere una carpeta fija adicional.

El proceso Consolidar archivos SGA combina todos los CSV de `folders/SGA`, aplica la normalización de `src/processors/sga.py` y guarda `SGA_Procesado_DD.MM.AA.xlsx` allí. Si el resultado del mismo día ya existe, lo reemplaza.

La función genérica `out(source_path, filename, extension=".xlsx", output_dir=None, add_date=True)` de `src/common/excel.py` construye rutas de salida. Por defecto usa la carpeta del archivo de entrada y añade la fecha. Al guardar, reemplaza un resultado existente con el mismo nombre. `save_excel` escribe primero un archivo temporal y luego reemplaza el destino; si el destino está abierto o bloqueado, muestra un error para cerrar el archivo e intentar de nuevo. Ejemplo: `out(csv_paths[0], "SGA_Procesado")`.

Para ejecutar directamente el proceso sin pasar por el menú:

```powershell
python scripts/depuracion.py
```

## Preparar una carpeta portable para Windows

En Windows, instala primero las dependencias desde un entorno virtual y ejecuta:

```powershell
.venv\Scripts\Activate.ps1
.\build_windows.ps1
```

La salida estará en `dist/ProcesadorArchivos/`. El proceso de empaquetado prepara las carpetas `folders/Cartera` y `folders/SGA`. Copia esa carpeta completa al otro computador; no tienes que crear las carpetas manualmente. Esta distribución es para Windows; para macOS o Linux hay que construir el paquete en ese sistema.

## Cómo agregar procesos

1. Revisa primero `src/common/`; reutiliza esas funciones o agrega allí una función compartida que necesite más de un proceso.
2. Pon las transformaciones reutilizables en un módulo de `src/processors/` y haz que reciban una ruta o un DataFrame y devuelvan el resultado.
3. Crea un flujo en `scripts/` que solicite o encuentre la entrada, llame al procesador y guarde el resultado. Si el usuario selecciona el archivo, usa su carpeta para la salida, como en `scripts/proveedores.py`.
4. En `app.py`, crea una función `run_<proceso>()` y añade un `ProcessOption` con nombre, función y carpetas fijas de trabajo. Para procesos empaquetados, agrega también su modo worker en el bloque `if __name__ == "__main__"`.
5. Documenta los archivos y pasos interactivos aquí.

Cada proceso debe tener sus propias carpetas de trabajo si usa fuentes distintas. No combines carpetas de entrada de procesos solo porque ambos consuman Excel.

## Estado conocido

Los archivos de `scripts/` contienen los flujos de ejecución y coordinan las funciones reutilizables de `src/`: lectura y escritura de Excel, transformaciones de cartera y SGA, procesamiento de proveedores e integración con ADRES. Para sumar un proceso, crea su flujo de ejecución en `scripts/`, agrega o reutiliza funciones en `src/`, e incorpora una entrada en `PROCESSES` con su función de ejecución y carpetas fijas de trabajo (si las necesita). Cuando el proceso pide un archivo al usuario, guarda el resultado en la carpeta de ese archivo de entrada.
