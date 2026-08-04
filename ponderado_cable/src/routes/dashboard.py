from flask import Blueprint, render_template, request, send_file
from database import ejecutar_sql_desde_archivo
from convertidores import cargar_convertidores
import os
import numpy as np
import pandas as pd
from io import BytesIO

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
    toneladas_total = 0
    importe_total = 0

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

        if df is not None and not df.empty:

            print("TOTAL REGISTROS SQL:", len(df))

            cantidad_sql = pd.to_numeric(
            df["Cantidad"],
            errors="coerce"
            ).fillna(0).sum()

            importe_sql = pd.to_numeric(
            df["ImporteVenta"],
            errors="coerce"
            ).fillna(0).sum()

            print("CANTIDAD TOTAL:", cantidad_sql)

            print("IMPORTE TOTAL:",
            "{:,.2f}".format(importe_sql))

        else:

                print("LA CONSULTA NO DEVOLVIÓ DATOS")

        print("==============================")


        marcas_disponibles = sorted(
        df["Categoria"].dropna().unique().tolist()
        )

        print("PARAMETROS ENVIADOS:", parametros)

        # =========================
        # AGREGAR CONVERTIDOR KG/M
        # =========================

        convertidores = cargar_convertidores()

        duplicados = convertidores[
            convertidores["ARTICULO"].duplicated(keep=False)
        ]

        print("TOTAL REGISTROS:", len(convertidores))
        print("ARTÍCULOS DUPLICADOS:", len(duplicados))

        if not duplicados.empty:
            print(duplicados.sort_values("ARTICULO"))

        print("==============================")


        df["Articulo"] = (
            df["Articulo"]
            .astype(str)
            .str.strip()
        )

        df = df.merge(
            convertidores,
            left_on="Articulo",
            right_on="ARTICULO",
            how="left"
        )

        df["KG/M"] = (
            pd.to_numeric(
                df["KG/M"],
                errors="coerce"
            )
            .fillna(0)
        )

        print(df[["Articulo","Cantidad","KG/M"]].head(10))
 
        marcas_disponibles = sorted(
        df["Categoria"].dropna().unique().tolist()
        )

        print("PARAMETROS ENVIADOS:", parametros)
        print("REGISTROS OBTENIDOS:", len(df))

        print(df.columns.tolist())
        print(df[["Articulo","Cantidad"]].head(10))

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

        for col in [
            "Cantidad",
            "ImporteVenta",
            "PBxCantidad",
            "PrecioBase",
            "KG/M"
        ]:
            df[col] = pd.to_numeric(
                df[col],
                errors="coerce"
            ).fillna(0)


        # =========================
        # TONELADAS
        # =========================

        df["Toneladas"] = (
            df["Cantidad"] *
            df["KG/M"]
        ) / 1000
        
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
        toneladas_total = df["Toneladas"].sum()
        importe_total = df["ImporteVenta"].sum()
       
        # =========================
        # AGRUPACIÓN
        # =========================
        df = df.groupby("Calibre", as_index=False).agg({
            "PrecioBase": "mean",
            "Cantidad": "sum",
            "Toneladas": "sum",
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

        print(df[[
        "Calibre",
        "Cantidad",
        "Toneladas"
        ]])
   
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
        toneladas_total=toneladas_total,
        importe_total=importe_total,
        color_tabla=color_tabla
    )

@dashboard.route("/thw_articulos", methods=["GET", "POST"])
def thw_articulos():
    
    print("ENTRANDO A THW ARTICULOS")


    datos = []

    fecha_inicio_sel = ""
    fecha_fin_sel = ""
    
    descuento_calibre_12 = 0
    descuento_ponderado = 0 
    precio_calibre_12 = 0

    color_tabla = "table-dark"

    cantidad_total = 0
    toneladas_total = 0
    importe_total = 0

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
        ruta_sql = os.path.join(BASE_DIR, "sql", "backup_sql", "THW_ARTICULOS.sql")

        df = ejecutar_sql_desde_archivo(ruta_sql, parametros)

        # =========================
        # AGREGAR CONVERTIDOR KG/M
        # =========================

        convertidores = cargar_convertidores()

        df["Articulo"] = (
            df["Articulo"]
            .astype(str)
            .str.strip()
        )

        df = df.merge(
            convertidores,
            left_on="Articulo",
            right_on="ARTICULO",
            how="left"
        )

        df["KG/M"] = (
            pd.to_numeric(
                df["KG/M"],
                errors="coerce"
            )
            .fillna(0)
        )

        marcas_disponibles = sorted(
        df["Categoria"].dropna().unique().tolist()
        )

        print("PARAMETROS ENVIADOS:", parametros)
        print("REGISTROS OBTENIDOS:", len(df))

        if df is None or df.empty:
            return render_template(
                "cable_thw_articulos.html",
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
        for col in ["Cantidad","ImporteVenta","PBxCantidad","PrecioBase"]:
            df[col] = pd.to_numeric(df[col],errors="coerce").fillna(0)

        # =========================
        # TONELADAS
        # =========================
                
        df["Toneladas"] = (
            df["Cantidad"]
            *
            df["KG/M"]
            ) / 1000
                
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
        # PRECIO CAL. 12
        # ANTES DE AGRUPAR ARTICULOS
        # =========================

        df_calibre_12 = df[df["Calibre"] == "12"]

        if not df_calibre_12.empty:

            precio_base_12 = (
                pd.to_numeric(
                    df_calibre_12["PrecioBase"],
                    errors="coerce"
            )
            .fillna(0)
            .mean()
            )

            precio_calibre_12 = (
                precio_base_12 *
                (1 - descuento_ponderado)
            )

        else:

            precio_calibre_12 = 0

        # =========================
        # TOTALES
        # =========================

        cantidad_total = df["Cantidad"].sum()
        importe_total = df["ImporteVenta"].sum()
       
        # =========================
        # AGRUPACIÓN
        # =========================
        df = df.groupby("Articulo",as_index=False).agg({

        "PrecioBase": "mean",
        "Cantidad": "sum",
        "Toneladas": "sum",
        "ImporteVenta": "sum",
        "PBxCantidad": "sum"

        })

        toneladas_total = df["Toneladas"].sum()
        
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

        df = df.sort_values("ImporteVenta",ascending=False)
        
        datos = df.to_dict(orient="records")

    return render_template(
        "cable_thw_articulos.html",
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
        toneladas_total=toneladas_total,
        importe_total=importe_total,
        color_tabla=color_tabla
    )


@dashboard.route("/desnudo", methods=["GET", "POST"])
def desnudo():
    
    print("ENTRANDO A DESNUDO")
    
    datos = []

    fecha_inicio_sel = ""
    fecha_fin_sel = ""
    
    precio_por_kg = 0
    precio_calibre_12 = 0

    color_tabla = "table-dark"

    cantidad_total = 0
    importe_total = 0
    pb_total = 0

    almacenes = []
    gerentes = []

    df = None  # 👈 IMPORTANTE evitar error UnboundLocal

    if request.method == "POST":

        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")

        fecha_inicio_sel = fecha_inicio
        fecha_fin_sel = fecha_fin

        almacen = request.form.get("almacen") or None
        gerente = request.form.get("gerente") or None


        parametros = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "almacen": almacen,
            "gerente": gerente
        }

        # limpiar vacíos
        for k, v in parametros.items():
            if v == "":
                parametros[k] = None

        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ruta_sql = os.path.join(BASE_DIR, "sql", "backup_sql", "DESNUDO.sql")

        print("ARCHIVO SQL UTILIZADO:")
        print(ruta_sql)

        df = ejecutar_sql_desde_archivo(ruta_sql, parametros)

        parametros_filtros = {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "almacen": None,
        "gerente": None
        }


        df_filtros = ejecutar_sql_desde_archivo(
        ruta_sql,
        parametros_filtros
        )

        print("PARAMETROS ENVIADOS:")
        print(parametros)
        print("TOTAL REGISTROS:", len(df))
        print(df["Linea"].value_counts())
        print(df["Calibre"].value_counts())

        if df is None or df.empty:
            return render_template(
            "cable_desnudo.html",
            datos=[],
            precio_por_kg=0,
            precio_calibre_12=0,
            fecha_inicio=fecha_inicio_sel,
            fecha_fin=fecha_fin_sel,
            almacenes=[],
            gerentes=[],
            cantidad_total=0,
            importe_total=0,
            pb_total=0
            )

        # =========================
        # FILTROS DINÁMICOS (ANTES DE AGRUPAR)
        # =========================

        almacenes = sorted(df_filtros["Almacen"].dropna().unique().tolist())
        gerentes = sorted(df_filtros["GerenteRegional"].dropna().unique().tolist())

        # =========================
        # FILTROS DINÁMICOS
        # =========================

        gerentes = sorted(
            df_filtros["GerenteRegional"]
            .dropna()
            .unique()
            .tolist()
        )

        if gerente:

            almacenes = sorted(
                df_filtros[
                df_filtros["GerenteRegional"] == gerente
                ]["Almacen"]
                .dropna()
                .unique()
                .tolist()
            )

        else:

            almacenes = sorted(
                df_filtros["Almacen"]
                .dropna()
                .unique()
                .tolist()
            )

        # =========================
        # NUMÉRICOS
        # =========================
        for col in ["Cantidad", "ImporteVenta", "PBxCantidad", "PrecioBase"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # =========================
        # TOTALES
        # =========================

        cantidad_total = df["Cantidad"].sum()
        importe_total = df["ImporteVenta"].sum()
        pb_total = df["PBxCantidad"].sum() 

        # =========================
        # AGRUPACIÓN CABLE DESNUDO
        # =========================

        df = df.groupby("Calibre", as_index=False).agg({

            "PrecioBase": "mean",
            "Cantidad": "sum",
            "ImporteVenta": "sum",
            "PBxCantidad": "sum",
            "Convertidor": "first",
            "CantidadEntreConvertidor": "sum"

        })
        
        # =========================
        # CÁLCULOS CABLE DESNUDO
        # =========================

        df["PrecioPromedio"] = df.apply(

            lambda x:
                x["ImporteVenta"] / x["Cantidad"]
                if x["Cantidad"] != 0
                else 0,

            axis=1

        )

        df["PrecioKg"] = df.apply(

            lambda x:
                x["ImporteVenta"] / x["CantidadEntreConvertidor"]
                if x["CantidadEntreConvertidor"] != 0
                else 0,

            axis=1

        )

        df = df.fillna(0)

        # =========================
        # KPI 1 - PRECIO POR KG
        # =========================

        cantidad_kg_total = df["CantidadEntreConvertidor"].sum()
        importe_total = df["ImporteVenta"].sum()

        if cantidad_kg_total != 0:
            precio_por_kg = importe_total / cantidad_kg_total
        else:
            precio_por_kg = 0
            
        print("==============================")
        print("TOTAL IMPORTE VENTA:", importe_total)
        print("TOTAL KG:", cantidad_kg_total)
        print("PRECIO KG:", precio_por_kg)
        print("==============================")

        # =========================
        # KPI 2 - PRECIO CAL. 12
        # =========================

        if precio_por_kg != 0:
            precio_calibre_12 = precio_por_kg / 33.33
        else:
            precio_calibre_12 = 0

        print("TOTAL KG:", cantidad_kg_total)
        print("PRECIO POR KG:", precio_por_kg)
        print("PRECIO CAL.12:", precio_calibre_12)

        df["Calibre"] = pd.Categorical(df["Calibre"],categories=ORDEN_CALIBRES,ordered=True)

        df = df.sort_values("Calibre")

        datos = df.to_dict(orient="records")

    return render_template(
        "cable_desnudo.html",
        datos=datos,
        precio_por_kg=precio_por_kg,
        precio_calibre_12=precio_calibre_12,
        fecha_inicio=fecha_inicio_sel,
        fecha_fin=fecha_fin_sel,
        almacenes=almacenes,
        gerentes=gerentes,
        cantidad_total=cantidad_total,
        importe_total=importe_total,
        pb_total=pb_total,
    )

@dashboard.route("/desnudo_articulos", methods=["GET", "POST"])
def desnudo_articulos():

    print("ENTRANDO A DESNUDO ARTICULOS")

    datos = []

    fecha_inicio_sel = ""
    fecha_fin_sel = ""
    
    precio_por_kg = 0
    precio_calibre_12 = 0

    color_tabla = "table-dark"

    cantidad_total = 0
    importe_total = 0
    pb_total = 0

    almacenes = []
    gerentes = []

    df = None  # 👈 IMPORTANTE evitar error UnboundLocal

    if request.method == "POST":

        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")

        fecha_inicio_sel = fecha_inicio
        fecha_fin_sel = fecha_fin

        almacen = request.form.get("almacen") or None
        gerente = request.form.get("gerente") or None

        parametros = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "almacen": almacen,
            "gerente": gerente
        }

        # limpiar vacíos
        for k, v in parametros.items():
            if v == "":
                parametros[k] = None

        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ruta_sql = os.path.join(BASE_DIR, "sql", "backup_sql", "DESNUDO.sql")

        print("ARCHIVO SQL UTILIZADO:")
        print(ruta_sql)

        df = ejecutar_sql_desde_archivo(ruta_sql, parametros)

        parametros_filtros = {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "almacen": None,
        "gerente": None
        }

        df_filtros = ejecutar_sql_desde_archivo(
        ruta_sql,
        parametros_filtros
        )

        print("PARAMETROS ENVIADOS:")
        print(parametros)
        print("TOTAL REGISTROS:", len(df))
        print(df["Linea"].value_counts())

        if df is None or df.empty:
            return render_template(
            "cable_desnudo_articulos.html",
            datos=[],
            precio_por_kg=0,
            precio_calibre_12=0,
            fecha_inicio=fecha_inicio_sel,
            fecha_fin=fecha_fin_sel,
            almacenes=[],
            gerentes=[],
            cantidad_total=0,
            importe_total=0,
            pb_total=0
            )

        # =========================
        # FILTROS DINÁMICOS (ANTES DE AGRUPAR)
        # =========================

        almacenes = sorted(df_filtros["Almacen"].dropna().unique().tolist())
        gerentes = sorted(df_filtros["GerenteRegional"].dropna().unique().tolist())

        # =========================
        # FILTROS DINÁMICOS
        # =========================

        gerentes = sorted(
            df_filtros["GerenteRegional"]
            .dropna()
            .unique()
            .tolist()
        )

        # Si hay gerente seleccionado,
        # mostrar solamente sus almacenes

        if gerente:

            almacenes = sorted(
                df_filtros[
                df_filtros["GerenteRegional"] == gerente
                ]["Almacen"]
                .dropna()
                .unique()
                .tolist()
            )

        else:

            almacenes = sorted(
                df_filtros["Almacen"]
                .dropna()
                .unique()
                .tolist()
            )

        # =========================
        # NUMÉRICOS
        # =========================
        for col in ["Cantidad", "ImporteVenta", "PBxCantidad", "PrecioBase"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # =========================
        # TOTALES
        # =========================

        cantidad_total = df["Cantidad"].sum()
        importe_total = df["ImporteVenta"].sum()
        pb_total = df["PBxCantidad"].sum() 

        # =========================
        # AGRUPACIÓN CABLE DESNUDO
        # =========================

        df = df.groupby("Articulo", as_index=False).agg({

            "PrecioBase": "mean",
            "Cantidad": "sum",
            "ImporteVenta": "sum",
            "PBxCantidad": "sum",
            "Convertidor": "first",
            "CantidadEntreConvertidor": "sum"

        })
        
        # =========================
        # CÁLCULOS CABLE DESNUDO
        # =========================

        df["PrecioPromedio"] = df.apply(

            lambda x:
                x["ImporteVenta"] / x["Cantidad"]
                if x["Cantidad"] != 0
                else 0,

            axis=1

        )

        df["PrecioKg"] = df.apply(

            lambda x:
                x["ImporteVenta"] / x["CantidadEntreConvertidor"]
                if x["CantidadEntreConvertidor"] != 0
                else 0,

            axis=1

        )

        df = df.fillna(0)

        # =========================
        # KPI 1 - PRECIO POR KG
        # =========================

        cantidad_kg_total = df["CantidadEntreConvertidor"].sum()
        importe_total = df["ImporteVenta"].sum()

        if cantidad_kg_total != 0:
            precio_por_kg = importe_total / cantidad_kg_total
        else:
            precio_por_kg = 0
            
        print("==============================")
        print("TOTAL IMPORTE VENTA:", importe_total)
        print("TOTAL KG:", cantidad_kg_total)
        print("PRECIO KG:", precio_por_kg)
        print("==============================")

        # =========================
        # KPI 2 - PRECIO CAL. 12
        # =========================

        if precio_por_kg != 0:
            precio_calibre_12 = precio_por_kg / 33.33
        else:
            precio_calibre_12 = 0

        print("TOTAL KG:", cantidad_kg_total)
        print("PRECIO POR KG:", precio_por_kg)
        print("PRECIO CAL.12:", precio_calibre_12)

        df = df.sort_values("ImporteVenta",ascending=False)

        datos = df.to_dict(orient="records")

    return render_template(
        "cable_desnudo_articulos.html",
        datos=datos,
        precio_por_kg=precio_por_kg,
        precio_calibre_12=precio_calibre_12,
        fecha_inicio=fecha_inicio_sel,
        fecha_fin=fecha_fin_sel,
        almacenes=almacenes,
        gerentes=gerentes,
        cantidad_total=cantidad_total,
        importe_total=importe_total,
        pb_total=pb_total,
    )

@dashboard.route("/serie8000", methods=["GET", "POST"])
def serie8000():
    
    print("ENTRANDO A SERIE8000")


    datos = []

    fecha_inicio_sel = ""
    fecha_fin_sel = ""
    
    descuento_ponderado = 0

    descuento_mc = 0
    descuento_xhhw = 0

    color_tabla = "table-dark"

    cantidad_total = 0
    toneladas_total = 0
    importe_total = 0
    pb_total = 0

    tipos = []
    almacenes = []
    gerentes = []

    df = None  # 👈 IMPORTANTE evitar error UnboundLocal

    if request.method == "POST":

        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")

        fecha_inicio_sel = fecha_inicio
        fecha_fin_sel = fecha_fin

        almacen = request.form.get("almacen") or None
        gerente = request.form.get("gerente") or None
        tipo = request.form.get("tipo") or None

        color_tabla = "table-dark"

        parametros = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "almacen": almacen,
            "tipo": tipo
        }

        # limpiar vacíos
        for k, v in parametros.items():
            if v == "":
                parametros[k] = None

        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ruta_sql = os.path.join(BASE_DIR, "sql", "backup_sql", "SERIE_8000.sql")

        extra_filters = ""

        if tipo:
            extra_filters += " AND Serie8000.Tipo = :tipo"

        if almacen:
            extra_filters += " AND Almacen = :almacen"

        parametros["extra_filters"] = extra_filters
        
        
        print("PARAMETROS ENVIADOS:") 
        print(parametros)

        df = ejecutar_sql_desde_archivo(ruta_sql, parametros)

        # =========================
        # AGREGAR CONVERTIDOR KG/M
        # =========================

        convertidores = cargar_convertidores()

        df["Articulo"] = (
            df["Articulo"]
            .astype(str)
            .str.strip()
        )

        df = df.merge(
            convertidores,
            left_on="Articulo",
            right_on="ARTICULO",
            how="left"
        )


        df["KG/M"] = (
            pd.to_numeric(
                df["KG/M"],
                errors="coerce"
            )
            .fillna(0)
        )

        # =========================
        # FILTRO GERENTE EN PANDAS
        # =========================

        if gerente:df = df[df["GerenteRegional"] == gerente]

        # =========================
        # DATA PARA LISTAS DE FILTROS
        # SIN FILTROS SELECCIONADOS
        # =========================

        parametros_filtros = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "almacen": None,
            "gerente": None,
            "tipo": None,
            "extra_filters": ""
        }


        df_filtros = ejecutar_sql_desde_archivo(ruta_sql,parametros_filtros)

        if df is not None and not df.empty:
            print(df[["Articulo", "Tipo"]].head(20))

        if df is None or df.empty:
            return render_template(
                "cable_serie8000.html",
                datos=[],
                fecha_inicio=fecha_inicio_sel,
                fecha_fin=fecha_fin_sel,
                almacenes=[],
                gerentes=[],
                cantidad_total=0,
                importe_total=0,
                pb_total=0
            )

    
        # =========================
        # FILTROS DINÁMICOS
        # =========================

        tipos = sorted(df_filtros["Tipo"].dropna().unique().tolist())

        gerentes = sorted(df_filtros["GerenteRegional"].dropna().unique().tolist())

        if gerente:

            almacenes = sorted(df_filtros[df_filtros["GerenteRegional"] == gerente]["Almacen"].dropna().unique().tolist())

        else:

            almacenes = sorted(df_filtros["Almacen"].dropna().unique().tolist()
            )

        # =========================
        # NUMÉRICOS
        # =========================
        for col in ["Cantidad", "ImporteVenta", "PBxCantidad", "PrecioBase"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # =========================
        # TONELADAS
        # =========================

        df["Toneladas"] = (
            df["Cantidad"]
            *
            df["KG/M"]
        ) / 1000
    
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
        toneladas_total = df["Toneladas"].sum()
        importe_total = df["ImporteVenta"].sum()
        pb_total = df["PBxCantidad"].sum() 

        # =========================
        # LIMPIEZA ARTICULO ANTES DE AGRUPAR
        # =========================

        df["Articulo"] = df["Articulo"].astype(str).str.strip()

        df["Tipo"] = df["Tipo"].astype(str).str.strip()

        # =========================
        # AGRUPACIÓN
        # =========================

        df = df.groupby(["Articulo", "Tipo"],as_index=False,dropna=False).agg({
            "PrecioBase": "mean",
            "Cantidad": "sum",
            "Toneladas": "sum",
            "ImporteVenta": "sum",
            "PBxCantidad": "sum"
        })

        toneladas_total = df["Toneladas"].sum()

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

        # ==========================
        # KPIs POR TIPO
        # ==========================

        df_mc = df[df["Tipo"] == "MC"]
        df_xhhw = df[df["Tipo"] == "XHHW"]


        def calcular_descuento(df_tipo):

            if df_tipo.empty: return 0

            importe = df_tipo["ImporteVenta"].sum()

            pb = df_tipo["PBxCantidad"].sum()

            if pb == 0: return 0

            return 1 - (importe / pb)



        descuento_mc = calcular_descuento(df_mc)

        descuento_xhhw = calcular_descuento(df_xhhw)

        # =========================
        # ORDENAR POR ARTÍCULO
        # =========================

        df = df.sort_values(by="ImporteVenta",ascending=False)

        print(df.columns.tolist())
        print(df.head(3).to_dict())

        datos = df.to_dict(orient="records")

    return render_template(
        "cable_serie8000.html",
        datos=datos,
        descuento_ponderado=descuento_ponderado,
        descuento_mc=descuento_mc,
        descuento_xhhw=descuento_xhhw,
        fecha_inicio=fecha_inicio_sel,
        fecha_fin=fecha_fin_sel,
        tipos=tipos,
        almacenes=almacenes,
        gerentes=gerentes,
        cantidad_total=cantidad_total,
        toneladas_total=toneladas_total,
        importe_total=importe_total,
        pb_total=pb_total,
        color_tabla=color_tabla
    )

@dashboard.route("/xlp", methods=["GET", "POST"])
def xlp():

    print("ENTRANDO A XLP")

    datos = []

    fecha_inicio_sel = ""
    fecha_fin_sel = ""

    descuento_ponderado = 0

    color_tabla = "table-dark"

    cantidad_total = 0
    importe_venta_total = 0
    precio_promedio = 0

    almacenes = []
    gerentes = []

    df = None


    if request.method == "POST":


        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")


        fecha_inicio_sel = fecha_inicio
        fecha_fin_sel = fecha_fin


        almacen = request.form.get("almacen") or None
        gerente = request.form.get("gerente") or None



        parametros = {

            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "almacen": almacen,
            "gerente": gerente,
            "extra_filters": ""

        }


        extra_filters = ""


        if almacen:

            extra_filters += " AND Almacen = :almacen"


        parametros["extra_filters"] = extra_filters



        BASE_DIR = os.path.abspath(
            os.path.join(
                os.path.dirname(__file__),
                "..",
                ".."
            )
        )


        ruta_sql = os.path.join(
            BASE_DIR,
            "sql",
            "backup_sql",
            "XLP.sql"
        )



        df = ejecutar_sql_desde_archivo(
            ruta_sql,
            parametros
        )

        print("REGISTROS XLP:", len(df))
        print(df.columns.tolist())
        
        if gerente:

            df = df[
                df["GerenteRegional"] == gerente
            ]



        if df is None or df.empty:

            return render_template(
                "cable_xlp.html",
                datos=[],
                fecha_inicio=fecha_inicio_sel,
                fecha_fin=fecha_fin_sel,
                almacenes=[],
                gerentes=[],
                cantidad_total=0,
                importe_costo_total=0,
                descuento_ponderado=0
            )

        # =========================
        # FILTROS DINÁMICOS
        # =========================

        almacenes = sorted(
            df["Almacen"]
            .dropna()
            .unique()
            .tolist()
        )


        gerentes = sorted(
            df["GerenteRegional"]
            .dropna()
            .unique()
            .tolist()
        )

        # =========================
        # NUMÉRICOS
        # =========================

        for col in [
            "Cantidad",
            "ImporteVenta",
            "PrecioBase"
        ]:

            df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)
            
        # =========================
        # DESC. PONDERADO
        # =========================

        total_costo = df["ImporteCosto"].sum()

        total_pb = (
            df["PrecioBase"]
            *
            df["Cantidad"]
        ).sum()


        if total_pb != 0:

            descuento_ponderado = (
                1 -
                (
                    total_costo /
                    total_pb
                )
            )

        else:

            descuento_ponderado = 0

        # =========================
        # TOTALES
        # =========================

        cantidad_total = (
            df["Cantidad"]
            .sum()
        )


        importe_venta_total = (
            df["ImporteVenta"]
            .sum()
        )

        # =========================
        # AGRUPACIÓN
        # =========================

        df = df.groupby(
            "Articulo",
            as_index=False
        ).agg({

            "Cantidad":"sum",

            "ImporteVenta":"sum",

            "PrecioBase":"mean"

        })

        df["PrecioPromedio"] = df.apply(
            lambda x:
            x["ImporteVenta"] / x["Cantidad"]
            if x["Cantidad"] != 0
            else 0,
            axis=1
        )

        # =========================
        # DESC. EQUIV SOBRE PL
        # =========================

        df["DescEquivPL"] = df.apply(

            lambda x:
           1 - (
                x["PrecioPromedio"] /
                x["PrecioBase"]
            )

            if x["Cantidad"] != 0
            else 0,

            axis=1

        )

        df = df.fillna(0)


        df = df.sort_values(
            "ImporteVenta",
            ascending=False
        )

        datos = df.to_dict(
            orient="records"
        )

    return render_template(
        "cable_xlp.html",

        datos=datos,
        descuento_ponderado=descuento_ponderado,
        fecha_inicio=fecha_inicio_sel,
        fecha_fin=fecha_fin_sel,
        almacenes=almacenes,
        gerentes=gerentes,
        cantidad_total=cantidad_total,
        importe_venta_total=importe_venta_total,
        color_tabla=color_tabla
        )

@dashboard.route("/resumen", methods=["GET", "POST"])
def resumen():

    from datetime import date, timedelta

    datos = []


    if request.method == "POST":

        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")

    else:

        fecha_inicio = date.today().replace(day=1).isoformat()
        fecha_fin = date.today().isoformat()



    BASE_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )


    def calcular_descuento(df):

        if df is None or df.empty:
            return 0


        importe = pd.to_numeric(
            df["ImporteVenta"],
            errors="coerce"
        ).fillna(0).sum()


        pb = pd.to_numeric(
            df["PBxCantidad"],
            errors="coerce"
        ).fillna(0).sum()


        if pb == 0:
            return 0


        return 1 - (importe / pb)

    def crear_fila_resumen(periodo):

        return {

            "fecha": periodo,

            "condumex": 0,
            "cal12_condumex": 0,

            "condulac": 0,
            "cal12_condulac": 0,

            "kobrex": 0,
            "cal12_kobrex": 0,

            "desnudo": 0,
            "cal12_desnudo": 0,

            "serie8000": 0

        }

    def procesar_thw(fila, fecha_inicio, fecha_fin):

        ruta_thw = os.path.join(
            BASE_DIR,
            "sql",
            "backup_sql",
            "THW.sql"
        )

        df_thw = ejecutar_sql_desde_archivo(
            ruta_thw,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "marca": None,
                "almacen": None,
                "gerente": None
            }
        )

        if df_thw is not None and not df_thw.empty:

            for marca, llave in [
                ("CONDUMEX", "condumex"),
                ("CONDULAC", "condulac"),
                ("KOBREX", "kobrex")
            ]:

                df_marca = df_thw[
                    df_thw["Categoria"] == marca
                ]

                fila[llave] = calcular_descuento(df_marca)

                calibre12 = df_marca[
                    df_marca["Calibre"] == "12"
                ]

                if not calibre12.empty:

                    precio_base_12 = (
                        calibre12["PrecioBase"]
                        .mean()
                    )

                    descuento = calcular_descuento(df_marca)

                    fila[f"cal12_{llave}"] = (
                        precio_base_12 *
                        (1 - descuento)
                    )

    def procesar_desnudo(fila, fecha_inicio, fecha_fin):

        ruta_desnudo = os.path.join(
            BASE_DIR,
            "sql",
            "backup_sql",
            "DESNUDO.sql"
        )


        df_desnudo = ejecutar_sql_desde_archivo(
            ruta_desnudo,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "almacen": None,
                "gerente": None
            }
        )


        if df_desnudo is not None and not df_desnudo.empty:


            kg = df_desnudo[
                "CantidadEntreConvertidor"
            ].sum()


            importe = df_desnudo[
                "ImporteVenta"
            ].sum()


            if kg != 0:

                fila["desnudo"] = importe / kg

                fila["cal12_desnudo"] = (
                    fila["desnudo"] / 33.33
            )

    def procesar_serie8000(fila, fecha_inicio, fecha_fin):

        ruta_serie = os.path.join(
            BASE_DIR,
            "sql",
            "backup_sql",
            "SERIE_8000.sql"
        )


        df_serie = ejecutar_sql_desde_archivo(
            ruta_serie,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "almacen": None,
                "tipo": None,
                "extra_filters": ""
            }
        )


        fila["serie8000"] = calcular_descuento(
            df_serie
        )

    fecha_actual = date.fromisoformat(fecha_inicio)

    fecha_final = date.fromisoformat(fecha_fin)

    # ============================
    # FECHAS MES ANTERIOR
    # ============================

    hoy = date.today()

    primer_dia_mes_actual = hoy.replace(day=1)

    ultimo_dia_mes_anterior = (
        primer_dia_mes_actual -
        timedelta(days=1)
    )

    primer_dia_mes_anterior = (
        ultimo_dia_mes_anterior.replace(day=1)
    )

    # ============================
    # RESUMEN MES ANTERIOR
    # ============================

    mes_anterior = crear_fila_resumen(
        "JULIO 2026"
    )

    # ============================
    # THW
    # ============================

    procesar_thw(
        mes_anterior,
        primer_dia_mes_anterior.isoformat(),
        ultimo_dia_mes_anterior.isoformat()
    )
    
    # ============================
    # DESNUDO
    # ============================

    procesar_desnudo(
        mes_anterior,
        primer_dia_mes_anterior.isoformat(),
        ultimo_dia_mes_anterior.isoformat()
    )

    # ============================
    # SERIE 8000
    # ============================
    
    procesar_serie8000(
        mes_anterior,
        primer_dia_mes_anterior.isoformat(),
        ultimo_dia_mes_anterior.isoformat()
    )

    while fecha_actual <= fecha_final:

        # ============================
        # OMITIR DOMINGOS
        # ============================

        if fecha_actual.weekday() == 6:
                fecha_actual += timedelta(days=1)
                continue

        fecha_dia = fecha_actual.isoformat()


        fila = {

            "fecha": fecha_dia,

            "condumex":0,
            "cal12_condumex":0,

            "condulac":0,
            "cal12_condulac":0,

            "kobrex":0,
            "cal12_kobrex":0,

            "desnudo":0,
            "cal12_desnudo":0,

            "serie8000":0
        }

        # ============================
        # THW
        # ============================

        procesar_thw(
            fila,
            fecha_dia,
            fecha_dia
        )
       
        # ============================
        # DESNUDO
        # ============================

        procesar_desnudo(
            fila,
            fecha_dia,
            fecha_dia
        )

        # ============================
        # SERIE 8000
        # ============================

        procesar_serie8000(
            fila,
            fecha_dia,
            fecha_dia
        )
        
        # GUARDAR EL DÍA COMPLETO

        datos.append(fila)


        # SIGUIENTE DÍA

        fecha_actual += timedelta(days=1)

    return render_template(
        "resumen.html",
        datos=datos,
        mes_anterior=mes_anterior
    )

@dashboard.route("/descargar_thw", methods=["POST"])
def descargar_thw():

    fecha_inicio = request.form.get("fecha_inicio")
    fecha_fin = request.form.get("fecha_fin")

    marca = request.form.get("marca") or None
    almacen = request.form.get("almacen") or None
    gerente = request.form.get("gerente") or None


    parametros = {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "marca": marca,
        "almacen": almacen,
        "gerente": gerente
    }


    BASE_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )


    ruta_sql = os.path.join(
        BASE_DIR,
        "sql",
        "backup_sql",
        "THW.sql"
    )


    df = ejecutar_sql_desde_archivo(
        ruta_sql,
        parametros
    )

    # =========================
    # AGREGAR CONVERTIDOR KG/M
    # =========================

    convertidores = cargar_convertidores()

    df["Articulo"] = (
    df["Articulo"]
    .astype(str)
    .str.strip()
    )


    df = df.merge(
    convertidores,
    left_on="Articulo",
    right_on="ARTICULO",
    how="left"
    )


    df["KG/M"] = (
    pd.to_numeric(
        df["KG/M"],
        errors="coerce"
    )
    .fillna(0)
    )


    # =========================
    # NUMÉRICOS
    # =========================

    for col in [
    "Cantidad",
    "ImporteVenta",
    "PBxCantidad",
    "PrecioBase",
    "KG/M"
    ]:
        
        df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    ).fillna(0)

    # =========================
    # TONELADAS
    # =========================

    df["Toneladas"] = (
    df["Cantidad"] *
    df["KG/M"]
    ) / 1000


    # =========================
    # AGRUPACIÓN
    # =========================

    df = df.groupby(
    "Calibre",
    as_index=False
    ).agg({

    "PrecioBase":"mean",
    "Cantidad":"sum",
    "Toneladas":"sum",
    "ImporteVenta":"sum",
    "PBxCantidad":"sum"

    })


    # =========================
    # CÁLCULOS
    # =========================

    df["PrecioPromedio"] = df.apply(
    lambda x:
        x["ImporteVenta"] / x["Cantidad"]
        if x["Cantidad"] != 0
        else 0,
    axis=1
    )


    df["DescEquivPL"] = df.apply(
    lambda x:
        1 - (x["PrecioPromedio"]/x["PrecioBase"])
        if x["PrecioBase"] != 0
        else 0,
    axis=1
    )


    df = df.fillna(0)

    df_excel = df[
    [
        "Calibre",
        "PrecioBase",
        "Cantidad",
        "Toneladas",
        "ImporteVenta",
        "PrecioPromedio",
        "DescEquivPL"
    ]
    ]

    archivo = BytesIO()


    with pd.ExcelWriter(
        archivo,
        engine="openpyxl"
    ) as writer:

        df_excel.to_excel(
            writer,
            index=False,
            sheet_name="THW"
        )


    archivo.seek(0)


    return send_file(
        archivo,
        download_name="Reporte_THW.xlsx",
        as_attachment=True
    )

@dashboard.route("/descargar_thw_articulos", methods=["POST"])
def descargar_thw_articulos():

    fecha_inicio = request.form.get("fecha_inicio")
    fecha_fin = request.form.get("fecha_fin")

    marca = request.form.get("marca") or None
    almacen = request.form.get("almacen") or None
    gerente = request.form.get("gerente") or None


    parametros = {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "marca": marca,
        "almacen": almacen,
        "gerente": gerente
    }


    BASE_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )


    ruta_sql = os.path.join(
        BASE_DIR,
        "sql",
        "backup_sql",
        "THW_ARTICULOS.sql"
    )


    df = ejecutar_sql_desde_archivo(
        ruta_sql,
        parametros
    )

    convertidores = cargar_convertidores()


    df["Articulo"] = (
    df["Articulo"]
    .astype(str)
    .str.strip()
    )


    df = df.merge(
    convertidores,
    left_on="Articulo",
    right_on="ARTICULO",
    how="left"
    )


    df["KG/M"] = (
    pd.to_numeric(
        df["KG/M"],
        errors="coerce"
    )
    .fillna(0)
    )


    for col in [
    "Cantidad",
    "ImporteVenta",
    "PBxCantidad",
    "PrecioBase",
    "KG/M"
    ]:

        df[col] = pd.to_numeric(
        df[col],
        errors="coerce"
    ).fillna(0)



    df["Toneladas"] = (
        df["Cantidad"] *
        df["KG/M"]
    ) / 1000



    df = df.groupby(
    "Articulo",
    as_index=False
    ).agg({

    "PrecioBase":"mean",
    "Cantidad":"sum",
    "Toneladas":"sum",
    "ImporteVenta":"sum",
    "PBxCantidad":"sum"

    })


    df["PrecioPromedio"] = df.apply(
    lambda x:
        x["ImporteVenta"] / x["Cantidad"]
        if x["Cantidad"] != 0
        else 0,
    axis=1
    )


    df["DescEquivPL"] = df.apply(
    lambda x:
        1 - (x["PrecioPromedio"]/x["PrecioBase"])
        if x["PrecioBase"] != 0
        else 0,
    axis=1
    ) 


    df = df.fillna(0)
    
    df_excel = df[
    [
        "Articulo",
        "PrecioBase",
        "Cantidad",
        "Toneladas",
        "ImporteVenta",
        "PrecioPromedio",
        "DescEquivPL"
    ]
    ]

    archivo = BytesIO()
    
    with pd.ExcelWriter(
        archivo,
        engine="openpyxl"
    ) as writer:

        df_excel.to_excel(
            writer,
            index=False,
            sheet_name="THW_ARTICULOS"
        )


    archivo.seek(0)


    return send_file(
        archivo,
        download_name="Reporte_THW_Articulos.xlsx",
        as_attachment=True
    )

@dashboard.route("/descargar_desnudo", methods=["POST"])
def descargar_desnudo():

    fecha_inicio = request.form.get("fecha_inicio")
    fecha_fin = request.form.get("fecha_fin")

    almacen = request.form.get("almacen") or None
    gerente = request.form.get("gerente") or None


    parametros = {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "almacen": almacen,
        "gerente": gerente
    }


    BASE_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )


    ruta_sql = os.path.join(
        BASE_DIR,
        "sql",
        "backup_sql",
        "DESNUDO.sql"
    )


    df = ejecutar_sql_desde_archivo(ruta_sql,parametros)

    # =========================
    # PROCESAR REPORTE CALIBRE
    # =========================

    for col in ["Cantidad", "ImporteVenta", "PBxCantidad", "PrecioBase"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)


    df = df.groupby("Calibre", as_index=False).agg({

        "PrecioBase": "mean",
        "Cantidad": "sum",
        "ImporteVenta": "sum",
        "PBxCantidad": "sum",
        "Convertidor": "first",
        "CantidadEntreConvertidor": "sum"

    })


    df["PrecioPromedio"] = df.apply(

        lambda x:
            x["ImporteVenta"] / x["Cantidad"]
            if x["Cantidad"] != 0
            else 0,

        axis=1

    )


    df["PrecioKg"] = df.apply(

        lambda x:
            x["ImporteVenta"] / x["CantidadEntreConvertidor"]
            if x["CantidadEntreConvertidor"] != 0
            else 0,

        axis=1

    )


    # COLUMNAS QUE SE EXPORTARÁN

    df = df[[
        "Calibre",
        "Cantidad",
        "ImporteVenta",
        "PrecioPromedio",
        "PrecioKg"
    ]]

    archivo = BytesIO()


    with pd.ExcelWriter(
        archivo,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="DESNUDO"
        )


    archivo.seek(0)


    return send_file(
        archivo,
        download_name="Reporte_Desnudo.xlsx",
        as_attachment=True
    )

@dashboard.route("/descargar_desnudo_articulos", methods=["POST"])
def descargar_desnudo_articulos():

    fecha_inicio = request.form.get("fecha_inicio")
    fecha_fin = request.form.get("fecha_fin")

    almacen = request.form.get("almacen") or None
    gerente = request.form.get("gerente") or None


    parametros = {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "almacen": almacen,
        "gerente": gerente
    }


    BASE_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )


    ruta_sql = os.path.join(
        BASE_DIR,
        "sql",
        "backup_sql",
        "DESNUDO_ARTICULOS.sql"
    )


    df = ejecutar_sql_desde_archivo(ruta_sql,parametros)

    # =========================
    # PROCESAR REPORTE ARTICULOS
    # =========================

    for col in ["Cantidad", "ImporteVenta", "PBxCantidad", "PrecioBase"]:
        df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)


    df = df.groupby("Articulo", as_index=False).agg({

        "PrecioBase": "mean",
        "Cantidad": "sum",
        "ImporteVenta": "sum",
        "PBxCantidad": "sum",
        "Convertidor": "first",
        "CantidadEntreConvertidor": "sum"

    })


    df["PrecioPromedio"] = df.apply(

        lambda x:
            x["ImporteVenta"] / x["Cantidad"]
            if x["Cantidad"] != 0
            else 0,
        axis=1
    )


    df["PrecioKg"] = df.apply(

        lambda x:
            x["ImporteVenta"] / x["CantidadEntreConvertidor"]
            if x["CantidadEntreConvertidor"] != 0
            else 0,
        axis=1
    )


    # COLUMNAS QUE SE EXPORTARÁN

    df = df[[ 
        "Articulo",
        "Cantidad",
        "ImporteVenta",
        "PrecioPromedio",
        "PrecioKg"
    ]]

    archivo = BytesIO()


    with pd.ExcelWriter(
        archivo,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
            writer,
            index=False,
            sheet_name="DESNUDO_ARTICULOS"
        )


    archivo.seek(0)


    return send_file(
        archivo,
        download_name="Reporte_Desnudo_Articulos.xlsx",
        as_attachment=True
    )

@dashboard.route("/descargar_serie8000", methods=["POST"])
def descargar_serie8000():

    fecha_inicio = request.form.get("fecha_inicio")
    fecha_fin = request.form.get("fecha_fin")

    almacen = request.form.get("almacen") or None
    gerente = request.form.get("gerente") or None
    tipo = request.form.get("tipo") or None

    
    extra_filters = ""

    if tipo:
        extra_filters = " AND Serie8000.Tipo = :tipo"


    parametros = {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "almacen": almacen,
        "gerente": gerente,
        "tipo": tipo,
        "extra_filters": extra_filters
    }


    BASE_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )


    ruta_sql = os.path.join(
        BASE_DIR,
        "sql",
        "backup_sql",
        "SERIE_8000.sql"
    )


    df = ejecutar_sql_desde_archivo(
        ruta_sql,
        parametros
    )

    if df is None or df.empty:

        archivo = BytesIO()

        return send_file(
            archivo,
            download_name="Reporte_Serie8000.xlsx",
            as_attachment=True
        )

    # =========================
    # AGREGAR KG/M
    # =========================

    convertidores = cargar_convertidores()


    df["Articulo"] = (
        df["Articulo"]
        .astype(str)
        .str.strip()
    )


    df = df.merge(
        convertidores,
        left_on="Articulo",
        right_on="ARTICULO",
        how="left"
    )


    df["KG/M"] = (
        pd.to_numeric(
            df["KG/M"],
            errors="coerce"
        )
        .fillna(0)
    )

    # =========================
    # FILTRO GERENTE
    # =========================

    if gerente:

        df = df[
            df["GerenteRegional"] == gerente
        ]



    # =========================
    # NUMÉRICOS
    # =========================

    for col in [
        "Cantidad",
        "ImporteVenta",
        "PBxCantidad",
        "PrecioBase"
    ]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    df["Toneladas"] = (
        df["Cantidad"] *
        df["KG/M"]
    ) / 1000

    # =========================
    # AGRUPACIÓN IGUAL A TABLA
    # =========================

    df["Articulo"] = (
        df["Articulo"]
        .astype(str)
        .str.strip()
    )


    df["Tipo"] = (
        df["Tipo"]
        .astype(str)
        .str.strip()
    )


    df = df.groupby(
        [
            "Articulo",
            "Tipo"
        ],
        as_index=False
    ).agg({

        "Cantidad":"sum",

        "Toneladas":"sum",

        "ImporteVenta":"sum",

        "PrecioBase":"mean",

        "PBxCantidad":"sum"

    })

    df["PrecioPromedio"] = df.apply(

        lambda x:
            x["ImporteVenta"] / x["Cantidad"]
            if x["Cantidad"] != 0
            else 0,

        axis=1
    )

    df["DescEquivPL"] = df.apply(

    lambda x:
        1 -
        (
            x["PrecioPromedio"] /
            x["PrecioBase"]
        )

        if x["PrecioBase"] != 0
        else 0,

    axis=1
    )

    df = df.fillna(0)


    df_excel = df[
    [
        "Articulo",
        "Tipo",
        "Cantidad",
        "Toneladas",
        "ImporteVenta",
        "PrecioPromedio",
        "DescEquivPL"
    ]
    ]

    archivo = BytesIO()

    with pd.ExcelWriter(
        archivo,
        engine="openpyxl"
    ) as writer:

        df_excel.to_excel(
            writer,
            index=False,
            sheet_name="SERIE8000"
        )


    archivo.seek(0)


    return send_file(
        archivo,
        download_name="Reporte_Serie8000.xlsx",
        as_attachment=True
    )

@dashboard.route("/descargar_xlp", methods=["POST"])
def descargar_xlp():

    fecha_inicio = request.form.get("fecha_inicio")
    fecha_fin = request.form.get("fecha_fin")

    almacen = request.form.get("almacen") or None
    gerente = request.form.get("gerente") or None


    parametros = {

        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "almacen": almacen,
        "gerente": gerente,
        "extra_filters": ""

    }


    extra_filters = ""


    if almacen:

        extra_filters += " AND Almacen = :almacen"


    parametros["extra_filters"] = extra_filters


    BASE_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )


    ruta_sql = os.path.join(
        BASE_DIR,
        "sql",
        "backup_sql",
        "XLP.sql"
    )


    df = ejecutar_sql_desde_archivo(
        ruta_sql,
        parametros
    )


    if gerente:

        df = df[
            df["GerenteRegional"] == gerente
        ]


    if df is None or df.empty:

        return "Sin datos para exportar"



    # =========================
    # NUMÉRICOS
    # =========================

    for col in [
        "Cantidad",
        "ImporteVenta",
        "PrecioBase"
    ]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)



    # =========================
    # AGRUPACIÓN IGUAL QUE TABLA
    # =========================

    df = df.groupby(
        "Articulo",
        as_index=False
    ).agg({

        "Cantidad":"sum",

        "ImporteVenta":"sum",

        "PrecioBase":"mean"

    })



    # =========================
    # PRECIO PROMEDIO
    # =========================

    df["PrecioPromedio"] = df.apply(

        lambda x:

        x["ImporteVenta"] / x["Cantidad"]

        if x["Cantidad"] != 0

        else 0,

        axis=1

    )



    # =========================
    # DESC. EQUIV SOBRE PL
    # =========================

    df["DescEquivPL"] = df.apply(

        lambda x:

        1 -
        (
            x["PrecioPromedio"]
            /
            x["PrecioBase"]
        )

        if x["PrecioBase"] != 0

        else 0,

        axis=1

    )



    df = df.fillna(0)



    # =========================
    # COLUMNAS DEL EXCEL
    # IGUALES A LA TABLA
    # =========================

    df_excel = df[
        [
            "Articulo",
            "Cantidad",
            "ImporteVenta",
            "PrecioPromedio",
            "DescEquivPL"
        ]
    ]



    archivo = BytesIO()



    with pd.ExcelWriter(
        archivo,
        engine="openpyxl"
    ) as writer:


        df_excel.to_excel(

            writer,

            index=False,

            sheet_name="XLP"

        )



    archivo.seek(0)



    return send_file(

        archivo,

        download_name="Reporte_XLP.xlsx",

        as_attachment=True

    )