from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
import os

# Cargar variables del archivo .env
load_dotenv()

# Ruta donde se encuentran los reportes de ventas
RUTA_VENTAS = Path(os.getenv("VENTAS_EXCEL_PATH"))

def leer_archivo_sucursales(ruta_archivo):
    """
    Lee el archivo Excel de sucursales y devuelve un DataFrame.
    """

    return pd.read_excel(
        ruta_archivo,
        sheet_name="Hoja1"
    )
