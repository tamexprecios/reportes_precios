from flask import Blueprint, render_template, request
from database import ejecutar_sql_desde_archivo
import os
import numpy as np
import pandas as pd

ORDEN_CALIBRES = [
    "2","4","6","8","10","12","14","16","18","20",
    "250","300","350","400","500","600","750","1000",
    "1/0","2/0","3/0","4/0"
]

dashboard = Blueprint("dashboard", __name__)


@dashboard.route("/thw", methods=["GET", "POST"])
def thw():
    
    print("ENTRANDO A THW")

    datos = []

    fecha_inicio_sel = ""
    fecha_fin_sel = ""
    
    descuento_calibre_12 = 0
    descuento_ponderado = 0
    precio_calibre_12 = 0

    color_tabla = "table-dark"

    cantidad_total = 0
    importe_total = 0
    pb_total = 0

    marcas = []
    almacenes = []
    gerentes = []

    df = None  # 👈 IMPORTANTE evitar error UnboundLocal

    if request.method == "POST":

        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")

        fecha_inicio_sel = fecha_inicio
        fecha_fin_sel = fecha_fin

        marca = request.form.get("marca") or None
        almacen = request.form.get("almacen") or None
        gerente = request.form.get("gerente") or None

        if marca == "CONDUMEX":

            color_tabla = "tabla-condumex"


        elif marca == "CONDULAC":

            color_tabla = "tabla-condulac"


        elif marca == "KOBREX":

            color_tabla = "tabla-kobrex"


        else:

            color_tabla = "table-dark"

        print("MARCA:", marca)
        print("COLOR TABLA:", color_tabla)


        parametros = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "marca": marca,
            "almacen": almacen,
            "gerente": gerente
        }

        # limpiar vacíos
        for k, v in parametros.items():
            if v == "":
                parametros[k] = None

        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ruta_sql = os.path.join(BASE_DIR, "sql", "backup_sql", "THW.sql")

        df = ejecutar_sql_desde_archivo(ruta_sql, parametros)

        marcas_disponibles = sorted(
        df["Categoria"].dropna().unique().tolist()
        )

        print("PARAMETROS ENVIADOS:", parametros)
        print("REGISTROS OBTENIDOS:", len(df))

        if df is None or df.empty:
            return render_template(
                "cable_thw.html",
                datos=[],
                descuento_calibre_12=0,
                fecha_inicio=fecha_inicio_sel,
                fecha_fin=fecha_fin_sel,
                marcas=[],
                almacenes=[],
                gerentes=[],
                cantidad_total=0,
                importe_total=0,
                pb_total=0
            )

        # =========================
        # FILTROS DINÁMICOS (ANTES DE AGRUPAR)
        # =========================

        marcas =  ["CONDUMEX","CONDULAC","KOBREX"]
        almacenes = sorted(df["Almacen"].dropna().unique().tolist())
        gerentes = sorted(df["GerenteRegional"].dropna().unique().tolist())

        # =========================
        # NUMÉRICOS
        # =========================
        for col in ["Cantidad", "ImporteVenta", "PBxCantidad", "PrecioBase"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # =========================
        # KPI 1 - DESCUENTO PONDERADO DE VENTA
        # =========================

        total_importe = df["ImporteVenta"].sum()
        total_pb = df["PBxCantidad"].sum()

        if total_pb != 0:
            descuento_ponderado = 1 - (total_importe / total_pb)
        else:
            descuento_ponderado = 0 

        # =========================
        # TOTALES
        # =========================

        cantidad_total = df["Cantidad"].sum()
        importe_total = df["ImporteVenta"].sum()
        pb_total = df["PBxCantidad"].sum() 

        # =========================
        # AGRUPACIÓN
        # =========================
        df = df.groupby("Calibre", as_index=False).agg({
            "PrecioBase": "mean",
            "Cantidad": "sum",
            "ImporteVenta": "sum",
            "PBxCantidad": "sum"
        })

        # =========================
        # CÁLCULOS
        # =========================
        df["PrecioPromedio"] = df.apply(
            lambda x: x["ImporteVenta"] / x["Cantidad"] if x["Cantidad"] != 0 else 0,
            axis=1
        )

        df["DescEquivPL"] = df.apply(
            lambda x: 1 - (x["PrecioPromedio"] / x["PrecioBase"]) if x["PrecioBase"] != 0 else 0,
            axis=1
        )

        df = df.fillna(0)

        # =========================
        # DESC. PONDERADO DE VENTA
        # =========================

        total_importe = df["ImporteVenta"].sum()
        total_pb = df["PBxCantidad"].sum()

        if total_pb != 0:
            descuento_ponderado = -((total_importe / total_pb) - 1)
        else:
            descuento_ponderado = 0

        print("TOTAL IMPORTE:", total_importe)
        print("TOTAL PB:", total_pb)
        print("DESC PONDERADO:", descuento_ponderado)

        # =========================
        # PRECIO CAL. 12
        # =========================

        calibre_12 = df[df["Calibre"] == "12"]

        if not calibre_12.empty:

            precio_base_12 = calibre_12.iloc[0]["PrecioBase"]

            precio_calibre_12 = precio_base_12 * (1 - descuento_ponderado)

        else:

            precio_calibre_12 = 0

        df["Calibre"] = pd.Categorical(df["Calibre"], categories=ORDEN_CALIBRES, ordered=True)
        df = df.sort_values("Calibre")

        datos = df.to_dict(orient="records")

    return render_template(
        "cable_thw.html",
        datos=datos,
        descuento_calibre_12=descuento_calibre_12,
        descuento_ponderado=descuento_ponderado,
        precio_calibre_12=precio_calibre_12,
        fecha_inicio=fecha_inicio_sel,
        fecha_fin=fecha_fin_sel,
        marcas=marcas,
        almacenes=almacenes,
        gerentes=gerentes,
        cantidad_total=cantidad_total,
        importe_total=importe_total,
        pb_total=pb_total,
        color_tabla=color_tabla
    )