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

def ejecutar_sql_desde_archivo(ruta_sql, parametros=None):

    engine = obtener_conexion()

    with open(ruta_sql, "r", encoding="utf-8") as file:
        query = file.read()

    with engine.connect() as conexion:

        if parametros is None:
            parametros = {}

        df = pd.read_sql(
            text(query),
            conexion,
            params=parametros
        )

    return df
