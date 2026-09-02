from pathlib import Path

import pandas as pd
from dotenv import load_dotenv
import os


# Cargar variables del archivo .env
load_dotenv()


# Ruta donde se encuentran los reportes de ventas
RUTA_VENTAS = Path(os.getenv("VENTAS_EXCEL_PATH"))


def leer_archivo_ventas(ruta_archivo):
    """
    Lee un archivo Excel de ventas y devuelve un DataFrame.
    """

    return pd.read_excel(ruta_archivo)
