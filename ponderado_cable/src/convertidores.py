import pandas as pd
import os


def cargar_convertidores():

    ruta_excel = os.path.join(
        os.path.dirname(__file__),
        "..",
        "convertidores",
        "CONVERTIDORES REPORTE PYTHON.xlsx"
    )


    df = pd.read_excel(
        ruta_excel,
        sheet_name="CONVERTIDORES",
        engine="openpyxl"
    )


    df["ARTICULO"] = (
        df["ARTICULO"]
        .astype(str)
        .str.strip()
    )


    return df[["ARTICULO", "KG/M"]]

if __name__ == "__main__":

    datos = cargar_convertidores()

    print(datos.head())

    print("TOTAL REGISTROS:", len(datos))
