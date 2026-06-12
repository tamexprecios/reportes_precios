from src.data.conexion_sql import obtener_datos

def main():

    df = obtener_datos()

    print(df.head())

if __name__ == "__main__":
    main()