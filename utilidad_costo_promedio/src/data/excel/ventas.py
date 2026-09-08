from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
import os


load_dotenv()


RUTA_VENTAS = Path(os.getenv("VENTAS_EXCEL_PATH"))


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
    Lee un archivo Excel de ventas.
    """

    return pd.read_excel(ruta_archivo)


def cargar_ventas_2026():
    """
    Carga los reportes mensuales de ventas de 2026
    y conserva únicamente registros CONCLUIDOS.
    """

    dataframes = []

    for archivo in obtener_archivos_ventas():

        df = leer_archivo_ventas(archivo)

        df = df[df["Estatus"] == "CONCLUIDO"].copy()

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

