import os
from io import BytesIO

import pandas as pd

from database import ejecutar_sql_desde_archivo
from convertidores import cargar_convertidores

print("THW SERVICE CARGADO")

def generar_reporte_thw(
    fecha_inicio,
    fecha_fin,
    marca=None,
    almacen=None,
    gerente=None
):
    print("GENERANDO REPORTE THW")

    return None

def calcular_descuento(df):

    if df is None or df.empty:
        return 0

    importe = pd.to_numeric(
        df["ImporteVenta"],
        errors="coerce"
    ).fillna(0).sum()

    pb = pd.to_numeric(
        df["PBxCantidad"],
        errors="coerce"
    ).fillna(0).sum()

    if pb == 0:
        return 0

    return 1 - (importe / pb)
