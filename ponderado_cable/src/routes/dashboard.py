print("ENTRÓ A THW")

import time
import pandas as pd
from flask import Blueprint, render_template, request
from database import ejecutar_sql_desde_archivo

dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/thw", methods=["GET", "POST"])
def thw():

    print("INICIO THW")

    # =========================
    # Filtros del formulario
    # =========================
    if request.method == "POST":
        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")
        marca = request.form.get("marca")
        almacen = request.form.get("almacen")
        gerente = request.form.get("gerente")
    else:
        fecha_inicio = None
        fecha_fin = None
        marca = None
        almacen = None
        gerente = None

    # =========================
    # Valores por defecto de fechas
    # =========================
    if not fecha_inicio:
        fecha_inicio = "1900-01-01"

    if not fecha_fin:
        fecha_fin = "2100-01-01"

    # =========================
    # CONSULTA SQL (MEDIDA DE TIEMPO)
    # =========================
    start = time.time()

    df = ejecutar_sql_desde_archivo(
        "../sql/backup_sql/THW.sql",
        {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "marca": marca,
            "almacen": almacen,
            "gerente": gerente,
        }
    )

    print("SQL TERMINÓ EN:", round(time.time() - start, 2), "segundos")

    # =========================
    # LIMPIEZA DE DATOS
    # =========================
    df["Cantidad"] = df["Cantidad"].fillna(0)
    df["ImporteVenta"] = df["ImporteVenta"].fillna(0)
    df["PBxCantidad"] = df["PBxCantidad"].fillna(0)
    df["PrecioBase"] = df["PrecioBase"].fillna(0)

    # =========================
    # CÁLCULOS
    # =========================
    df["PrecioPromedio"] = df["ImporteVenta"] / df["Cantidad"].replace(0, 1)

    df["DescEquivPL"] = -(
        df["ImporteVenta"] / df["PBxCantidad"].replace(0, 1) - 1
    )

    # =========================
    # AGRUPAR POR CALIBRE
    # =========================
    tabla = df.groupby("Calibre", as_index=False).agg({
        "PrecioBase": "mean",
        "Cantidad": "sum",
        "ImporteVenta": "sum",
        "PBxCantidad": "sum"
    })

    tabla["PrecioPromedio"] = tabla["ImporteVenta"] / tabla["Cantidad"].replace(0, 1)

    tabla["DescEquivPL"] = -(
        tabla["ImporteVenta"] / tabla["PBxCantidad"].replace(0, 1) - 1
    )

    # =========================
    # ORDEN DE CALIBRES
    # =========================
    orden_calibres = [
        "2","4","6","8","10","12","14","16","18","20",
        "250","300","350","400","500","600","750","1000",
        "1/0","2/0","3/0","4/0"
    ]

    tabla["Calibre"] = pd.Categorical(tabla["Calibre"], categories=orden_calibres, ordered=True)
    tabla = tabla.sort_values("Calibre")

    # =========================
    # KPI CALIBRE 12
    # =========================
    base_12 = tabla.loc[tabla["Calibre"] == "12", "PrecioBase"].values
    desc_12 = tabla.loc[tabla["Calibre"] == "12", "DescEquivPL"].values

    base_12 = base_12[0] if len(base_12) else 0
    desc_12 = desc_12[0] if len(desc_12) else 0

    descuento_ponderado_12 = base_12 * (1 - desc_12)

    # =========================
    # RENDER A HTML
    # =========================
    return render_template(
        "cable_thw.html",
        datos=tabla.to_dict(orient="records"),
        descuento_calibre_12=descuento_ponderado_12
    )