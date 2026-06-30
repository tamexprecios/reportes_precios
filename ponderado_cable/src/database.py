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