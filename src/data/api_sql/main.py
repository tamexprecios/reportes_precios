from fastapi import FastAPI
import pandas as pd
import pyodbc

app = FastAPI()

def get_connection():
    server = "192.168.11.239"
    database = "Tamex2"
    username = "analista03"
    password = "Pr3c2o25$sq."

    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
    )
    return conn
@app.get("/datos")
def obtener_datos():

    data = [
        {
            "ID": 1,
            "Cliente": "DEMO",
            "MargenPedidoPct": 12.5,
            "Estatus": "CONCLUIDO"
        },
        {
            "ID": 2,
            "Cliente": "PRUEBA",
            "MargenPedidoPct": 8.2,
            "Estatus": "CONCLUIDO"
        }
    ]

    return data