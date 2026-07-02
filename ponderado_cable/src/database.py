import pandas as pd
from sqlalchemy import create_engine, text
from config import (
    SERVIDOR,
    BASE_DATOS,
    USUARIO,
    PASSWORD,
    DRIVER
)


def obtener_conexion():

    conexion = (
        f"mssql+pyodbc://{USUARIO}:{PASSWORD}@"
        f"{SERVIDOR}/{BASE_DATOS}"
        f"?driver={DRIVER.replace(' ', '+')}"
    )

    engine = create_engine(conexion)

    return engine


def probar_conexion():

    engine = obtener_conexion()

    try:
        with engine.connect() as conexion:

            resultado = conexion.execute(
                text("SELECT 1")
            )

            print("Conexión exitosa")
            print(resultado.fetchone())


    except Exception as error:

        print("Error de conexión:")
        print(error)



if __name__ == "__main__":

    probar_conexion()

def ejecutar_sql_desde_archivo(ruta_sql):

    engine = obtener_conexion()

    # 1. Abrimos el archivo SQL
    with open(ruta_sql, "r", encoding="utf-8") as file:
        query = file.read()

    # 2. Ejecutamos en SQL Server
    with engine.connect() as conexion:
        df = pd.read_sql(text(query), conexion)

    # 3. Regresamos DataFrame
    return df
    