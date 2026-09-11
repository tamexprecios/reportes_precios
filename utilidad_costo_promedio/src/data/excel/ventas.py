from pathlib import Path
import pandas as pd
import json
from dotenv import load_dotenv
import os

load_dotenv()

RUTA_VENTAS = Path(os.getenv("VENTAS_EXCEL_PATH"))

RUTA_DATOS_PROCESADOS = Path("data/procesados")

RUTA_VENTAS_PARQUET = (
    RUTA_DATOS_PROCESADOS / "ventas_2026.parquet"
)

MESES_2026 = [
    "Enero",
    "Febrero",
    "Marzo",
    "Abril",
    "Mayo",
    "Junio",
    "Julio",
    "Agosto",
    "Septiembre",
]

def obtener_archivos_ventas():
    """
    Obtiene únicamente los reportes mensuales oficiales de ventas 2026.
    """

    archivos = []

    for mes in MESES_2026:

        nombre = f"Reporte ventas mensual {mes} 2026.xlsx"

        archivo = RUTA_VENTAS / nombre

        if archivo.exists():
            archivos.append(archivo)

    return archivos

def leer_archivo_ventas(ruta_archivo):
    """
    Lee únicamente las columnas necesarias de un archivo Excel de ventas.
    """

    columnas_necesarias = [
        "Estatus",
        "FechaEmision",
        "Almacen",
        "Articulo",
        "Categoria",
        "Linea",
        "Sucursal",
        "SubTotalMN",
        "ImporteCosto",
    ]

    return pd.read_excel(
        ruta_archivo,
        usecols=columnas_necesarias
    )

def guardar_parquet(df, ruta):
    """
    Guarda un DataFrame en formato Parquet.
    """

    ruta.parent.mkdir(
        parents=True,
        exist_ok=True
    )

    df.to_parquet(
        ruta,
        index=False
    )

def archivos_ventas_cambiaron(archivos, archivo_control):
    """
    Comprueba si alguno de los archivos Excel de ventas
    cambió desde la última carga.
    """

    estado_actual = {}

    for archivo in archivos:

        estado_actual[archivo.name] = {
            "tamano": archivo.stat().st_size,
            "modificado": archivo.stat().st_mtime
        }

    if not archivo_control.exists():

        return True, estado_actual

    try:

        with open(
            archivo_control,
            "r",
            encoding="utf-8"
        ) as f:

            estado_anterior = json.load(f)

    except (json.JSONDecodeError, OSError):

        return True, estado_actual

    if estado_actual != estado_anterior:

        return True, estado_actual

    return False, estado_actual


def cargar_ventas_2026():
    """
    Carga los reportes mensuales de ventas de 2026
    y conserva únicamente registros CONCLUIDOS.
    """
    
    import time

    RUTA_DATOS_PROCESADOS.mkdir(
        parents=True,
        exist_ok=True
    )

    archivo_cache = (
        RUTA_DATOS_PROCESADOS
        / "ventas_2026_cache.parquet"
    )

    archivo_control = (
        RUTA_DATOS_PROCESADOS
        / "ventas_2026_control.json"
    )

    archivos = obtener_archivos_ventas()

    hay_cambios, estado_actual = archivos_ventas_cambiaron(
        archivos,
        archivo_control
    )


    if archivo_cache.exists() and not hay_cambios:

        print("\n" + "=" * 60)
        print("CARGANDO VENTAS DESDE CACHÉ")
        print("=" * 60)

        inicio_cache = time.perf_counter()

        ventas = pd.read_parquet(
            archivo_cache
        )

        fin_cache = time.perf_counter()

        print(
            f"[OK] Caché cargada: "
            f"{fin_cache - inicio_cache:.2f} segundos"
        )

        print(
            f"Filas cargadas: {len(ventas):,}"
        )

        return ventas
   
    dataframes = []

    import time

    inicio_total = time.perf_counter()

    print("\n" + "=" * 60)
    print("DIAGNÓSTICO DE CARGA DE VENTAS")
    print("=" * 60)


    for archivo in obtener_archivos_ventas():

        inicio_archivo = time.perf_counter()

        print(f"\nLeyendo: {archivo.name}")

        df = leer_archivo_ventas(archivo)

        fin_lectura = time.perf_counter()

        print(
            f"  [OK] Lectura Excel: "
            f"{fin_lectura - inicio_archivo:.2f} segundos"
        )

        print(
            f"  Filas leídas: {len(df):,}"
        )

        df = df[
            df["Estatus"]
            .astype(str)
            .str.strip()
            .str.upper()
            == "CONCLUIDO"
        ].copy()

# ============================================================
# EXCLUIR ALMACENES DE REFERENCIA Y PROVISIONALES
# ============================================================

        df = df[
            ~(
                df["Almacen"]
                .astype(str)
                .str.strip()
                .str.upper()
                .str.startswith(("REF", "ENTDIRECT"))
            )
        ].copy()

        fin_filtro = time.perf_counter()

        print(
            f"  [OK] Filtrado: "
            f"{fin_filtro - fin_lectura:.2f} segundos"
        )

        print(
            f"  Filas después del filtro: {len(df):,}"
        )


        dataframes.append(df)

    if not dataframes:
        return pd.DataFrame()

    ventas = pd.concat(dataframes, ignore_index=True)

    ppp = cargar_ppp()

    ventas = ventas.merge(
        ppp,
        on="Articulo",
        how="left"
    )

    ventas["PPP"] = ventas["PPP"].fillna(0)

    ventas["ImporteCostoPPP"] = (
    ventas["ImporteCosto"] * (1 - ventas["PPP"])
    )

    print("\nGuardando caché de ventas...")

    inicio_cache = time.perf_counter() 

    ventas.to_parquet(
        archivo_cache,
        index=False
    )

    fin_cache = time.perf_counter()

    print(
        f"[OK] Caché guardada: "
        f"{fin_cache - inicio_cache:.2f} segundos"
    )

    fin_total = time.perf_counter()


    print("\n" + "=" * 60)
    print(
        f"TIEMPO TOTAL cargar_ventas_2026: "
        f"{fin_total - inicio_total:.2f} segundos"
    )
    print("=" * 60)

    with open(
        archivo_control,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            estado_actual,
            f,
            indent=4
        )

    print("[OK] Control de archivos actualizado")

    return ventas

def cargar_ppp():
    """
    Lee el archivo PPP y devuelve únicamente
    los campos necesarios para relacionarlo con ventas.
    """

    archivo = RUTA_VENTAS / "PPP.xlsx"

    return pd.read_excel(
        archivo,
        usecols=["Articulo", "PPP"]
    )

def calcular_resumen_ventas(df):
    """
    Calcula los principales indicadores de utilidad
    utilizando el costo promedio con PPP.
    """

    importe_venta = df["SubTotalMN"].sum()

    importe_costo_ppp = df["ImporteCostoPPP"].sum()

    utilidad_bruta = importe_venta - importe_costo_ppp

    margen_utilidad = (
        utilidad_bruta / importe_venta
        if importe_venta != 0
        else 0
    )

    return {
        "importe_venta": importe_venta,
        "importe_costo_ppp": importe_costo_ppp,
        "utilidad_bruta": utilidad_bruta,
        "margen_utilidad": margen_utilidad,
    }

if __name__ == "__main__":
    archivos = obtener_archivos_ventas()

    if archivos:
        archivo = archivos[0]

        df = leer_archivo_ventas(archivo)

        print("\nARCHIVO:")
        print(archivo.name)

        print("\nCOLUMNAS:")
        print(df.columns.tolist())

        print("\nPRIMERAS 5 FILAS:")
        print(df.head(5).to_string(index=False))

    else:
        print("NO SE ENCONTRARON ARCHIVOS DE VENTAS.")

