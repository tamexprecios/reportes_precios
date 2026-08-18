from flask import Blueprint, render_template, request, send_file, jsonify
from database import ejecutar_sql_desde_archivo
from convertidores import cargar_convertidores
import os
import numpy as np
import pandas as pd
from io import BytesIO
from datetime import date

ORDEN_CALIBRES = ["2","4","6","8","10","12","14","16","18","20","250","300","350",
                  "400","500","600","750","1000","1/0","2/0","3/0","4/0"
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

    color_tabla = "tabla-thw-default"

    cantidad_total = 0
    toneladas_total = 0
    importe_total = 0

    marcas = []
    almacenes = []
    gerentes = []

    df = None  # 

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
            color_tabla = "tabla-thw-default"

        parametros = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "marca": marca,
            "almacen": almacen,
            "gerente": gerente
        }

        # limpiar vacíos #
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

        # AGREGAR CONVERTIDOR KG/M #
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

        # FILTROS DINÁMICOS (ANTES DE AGRUPAR) #
        marcas =  ["CONDUMEX","CONDULAC","KOBREX"]
        almacenes = sorted(df["Almacen"].dropna().unique().tolist())
        gerentes = sorted(df["GerenteRegional"].dropna().unique().tolist())

        # NUMÉRICOS #
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

        # TONELADAS # 
        df["Toneladas"] = (
            df["Cantidad"] *
            df["KG/M"]
        ) / 1000
        
        # KPI 1 - DESCUENTO PONDERADO DE VENTA #
        total_importe = df["ImporteVenta"].sum()
        total_pb = df["PBxCantidad"].sum()

        if total_pb != 0:
            descuento_ponderado = 1 - (total_importe / total_pb)
        else:
            descuento_ponderado = 0 

        # TOTALES #
        cantidad_total = df["Cantidad"].sum()
        toneladas_total = df["Toneladas"].sum()
        importe_total = df["ImporteVenta"].sum()
       
        # AGRUPACIÓN #
        df = df.groupby("Calibre", as_index=False).agg({
            "PrecioBase": "mean",
            "Cantidad": "sum",
            "Toneladas": "sum",
            "ImporteVenta": "sum",
            "PBxCantidad": "sum"
        })

        # CÁLCULOS #
        df["PrecioPromedio"] = df.apply(
            lambda x: x["ImporteVenta"] / x["Cantidad"] if x["Cantidad"] != 0 else 0,
            axis=1
        )

        df["DescEquivPL"] = df.apply(
            lambda x: 1 - (x["PrecioPromedio"] / x["PrecioBase"]) if x["PrecioBase"] != 0 else 0,
            axis=1
        )

        df = df.fillna(0)

        
        # DESC. PONDERADO DE VENTA #
        total_importe = df["ImporteVenta"].sum()
        total_pb = df["PBxCantidad"].sum()

        if total_pb != 0:
            descuento_ponderado = -((total_importe / total_pb) - 1)
        else:
            descuento_ponderado = 0

        # PRECIO CAL. 12 #
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

    color_tabla = "tabla-thw-default"

    cantidad_total = 0
    toneladas_total = 0
    importe_total = 0

    marcas = []
    almacenes = []
    gerentes = []

    df = None  # 👈 IMPORTANTE evitar error UnboundLocal #

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
            color_tabla = "tabla-thw-default"

        parametros = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "marca": marca,
            "almacen": almacen,
            "gerente": gerente
        }

        # limpiar vacíos #
        for k, v in parametros.items():
            if v == "":
                parametros[k] = None

        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ruta_sql = os.path.join(BASE_DIR, "sql", "backup_sql", "THW_ARTICULOS.sql")

        df = ejecutar_sql_desde_archivo(ruta_sql, parametros)

        # AGREGAR CONVERTIDOR KG/M #
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

        # FILTROS DINÁMICOS (ANTES DE AGRUPAR) #
        marcas =  ["CONDUMEX","CONDULAC","KOBREX"]
        almacenes = sorted(df["Almacen"].dropna().unique().tolist())
        gerentes = sorted(df["GerenteRegional"].dropna().unique().tolist())

        # NUMÉRICOS #
        for col in ["Cantidad","ImporteVenta","PBxCantidad","PrecioBase"]:
            df[col] = pd.to_numeric(df[col],errors="coerce").fillna(0)

        # TONELADAS #         
        df["Toneladas"] = (
            df["Cantidad"]
            *
            df["KG/M"]
            ) / 1000
                
        # KPI 1 - DESCUENTO PONDERADO DE VENTA #
        total_importe = df["ImporteVenta"].sum()
        total_pb = df["PBxCantidad"].sum()

        if total_pb != 0:
            descuento_ponderado = 1 - (total_importe / total_pb)
        else:
            descuento_ponderado = 0 

        # PRECIO CAL. 12 ANTES DE AGRUPAR ARTICULOS #
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

        # TOTALES #
        cantidad_total = df["Cantidad"].sum()
        importe_total = df["ImporteVenta"].sum()
       
        # AGRUPACIÓN #
        df = df.groupby("Articulo",as_index=False).agg({

        "PrecioBase": "mean",
        "Cantidad": "sum",
        "Toneladas": "sum",
        "ImporteVenta": "sum",
        "PBxCantidad": "sum"

        })

        toneladas_total = df["Toneladas"].sum()
        
        # CÁLCULOS #
        df["PrecioPromedio"] = df.apply(
            lambda x: x["ImporteVenta"] / x["Cantidad"] if x["Cantidad"] != 0 else 0,
            axis=1
        )

        df["DescEquivPL"] = df.apply(
            lambda x: 1 - (x["PrecioPromedio"] / x["PrecioBase"]) if x["PrecioBase"] != 0 else 0,
            axis=1
        )

        df = df.fillna(0)

        # DESC. PONDERADO DE VENTA #
        total_importe = df["ImporteVenta"].sum()
        total_pb = df["PBxCantidad"].sum()

        if total_pb != 0:
            descuento_ponderado = -((total_importe / total_pb) - 1)
        else:
            descuento_ponderado = 0

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

    color_tabla = "tabla-thw-default"

    cantidad_total = 0
    importe_total = 0
    pb_total = 0

    almacenes = []
    gerentes = []

    df = None  # 👈 IMPORTANTE evitar error UnboundLocal #

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

        # limpiar vacíos #
        for k, v in parametros.items():
            if v == "":
                parametros[k] = None

        BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", ".."))
        ruta_sql = os.path.join(BASE_DIR, "sql", "backup_sql", "DESNUDO.sql")

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

        # FILTROS DINÁMICOS (ANTES DE AGRUPAR)#
        almacenes = sorted(df_filtros["Almacen"].dropna().unique().tolist())
        gerentes = sorted(df_filtros["GerenteRegional"].dropna().unique().tolist())

        # FILTROS DINÁMICOS #
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

        # NUMÉRICOS #
        for col in ["Cantidad", "ImporteVenta", "PBxCantidad", "PrecioBase"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # TOTALES #
        cantidad_total = df["Cantidad"].sum()
        importe_total = df["ImporteVenta"].sum()
        pb_total = df["PBxCantidad"].sum() 

        # AGRUPACIÓN CABLE DESNUDO #   
        df = df.groupby("Calibre", as_index=False).agg({

            "PrecioBase": "mean",
            "Cantidad": "sum",
            "ImporteVenta": "sum",
            "PBxCantidad": "sum",
            "Convertidor": "first",
            "CantidadEntreConvertidor": "sum"

        })
        
        # CÁLCULOS CABLE DESNUDO #
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

        # KPI 1 - PRECIO POR KG # 
        cantidad_kg_total = df["CantidadEntreConvertidor"].sum()
        importe_total = df["ImporteVenta"].sum()

        if cantidad_kg_total != 0:
            precio_por_kg = importe_total / cantidad_kg_total
        else:
            precio_por_kg = 0
            
        # KPI 2 - PRECIO CAL. 12 #
        if precio_por_kg != 0:
            precio_calibre_12 = precio_por_kg / 33.33
        else:
            precio_calibre_12 = 0

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

    color_tabla = "tabla-thw-default"

    cantidad_total = 0
    importe_total = 0
    pb_total = 0

    almacenes = []
    gerentes = []

    df = None  # 👈 IMPORTANTE evitar error UnboundLocal #

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

        # limpiar vacíos #
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

        # FILTROS DINÁMICOS (ANTES DE AGRUPAR) #
        almacenes = sorted(df_filtros["Almacen"].dropna().unique().tolist())
        gerentes = sorted(df_filtros["GerenteRegional"].dropna().unique().tolist())

        # FILTROS DINÁMICOS #
        gerentes = sorted(
            df_filtros["GerenteRegional"]
            .dropna()
            .unique()
            .tolist()
        )

        # Si hay gerente seleccionado, mostrar solamente sus almacenes #
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

        # NUMÉRICOS #
        for col in ["Cantidad", "ImporteVenta", "PBxCantidad", "PrecioBase"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # TOTALES #
        cantidad_total = df["Cantidad"].sum()
        importe_total = df["ImporteVenta"].sum()
        pb_total = df["PBxCantidad"].sum() 

        # AGRUPACIÓN CABLE DESNUDO #
        df = df.groupby("Articulo", as_index=False).agg({

            "PrecioBase": "mean",
            "Cantidad": "sum",
            "ImporteVenta": "sum",
            "PBxCantidad": "sum",
            "Convertidor": "first",
            "CantidadEntreConvertidor": "sum"

        })
        
        # CÁLCULOS CABLE DESNUDO #
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

        # KPI 1 - PRECIO POR KG #
        cantidad_kg_total = df["CantidadEntreConvertidor"].sum()
        importe_total = df["ImporteVenta"].sum()

        if cantidad_kg_total != 0:
            precio_por_kg = importe_total / cantidad_kg_total
        else:
            precio_por_kg = 0
        
        # KPI 2 - PRECIO CAL. 12 #
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

    color_tabla = "tabla-thw-default"

    cantidad_total = 0
    toneladas_total = 0
    importe_total = 0
    pb_total = 0

    tipos = []
    almacenes = []
    gerentes = []

    df = None  # 👈 IMPORTANTE evitar error UnboundLocal #

    if request.method == "POST":

        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")

        fecha_inicio_sel = fecha_inicio
        fecha_fin_sel = fecha_fin

        almacen = request.form.get("almacen") or None
        gerente = request.form.get("gerente") or None
        tipo = request.form.get("tipo") or None

        color_tabla = "tabla-thw-default"

        parametros = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "almacen": almacen,
            "tipo": tipo
        }

        # limpiar vacíos #
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

        df = ejecutar_sql_desde_archivo(ruta_sql, parametros)

        # AGREGAR CONVERTIDOR KG/M #
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

        # FILTRO GERENTE EN PANDAS #
        if gerente:df = df[df["GerenteRegional"] == gerente]

        # DATA PARA LISTAS DE FILTROS SIN FILTROS SELECCIONADOS #
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
   
        # FILTROS DINÁMICOS #
        tipos = sorted(df_filtros["Tipo"].dropna().unique().tolist())

        gerentes = sorted(df_filtros["GerenteRegional"].dropna().unique().tolist())

        if gerente:
            almacenes = sorted(df_filtros[df_filtros["GerenteRegional"] == gerente]["Almacen"].dropna().unique().tolist())

        else:
            almacenes = sorted(df_filtros["Almacen"].dropna().unique().tolist())

        # NUMÉRICOS #
        for col in ["Cantidad", "ImporteVenta", "PBxCantidad", "PrecioBase"]:
            df[col] = pd.to_numeric(df[col], errors="coerce").fillna(0)

        # TONELADAS #
        df["Toneladas"] = (
            df["Cantidad"]
            *
            df["KG/M"]
        ) / 1000
    
        # KPI 1 - DESCUENTO PONDERADO DE VENTA #
        total_importe = df["ImporteVenta"].sum()
        total_pb = df["PBxCantidad"].sum()

        if total_pb != 0:
            descuento_ponderado = 1 - (total_importe / total_pb)
        else:
            descuento_ponderado = 0 

        # TOTALES # 
        cantidad_total = df["Cantidad"].sum()
        toneladas_total = df["Toneladas"].sum()
        importe_total = df["ImporteVenta"].sum()
        pb_total = df["PBxCantidad"].sum() 

        # LIMPIEZA ARTICULO ANTES DE AGRUPAR #
        df["Articulo"] = df["Articulo"].astype(str).str.strip()

        df["Tipo"] = df["Tipo"].astype(str).str.strip()

        # AGRUPACIÓN #
        df = df.groupby(["Articulo", "Tipo"],as_index=False,dropna=False).agg({
            "PrecioBase": "mean",
            "Cantidad": "sum",
            "Toneladas": "sum",
            "ImporteVenta": "sum",
            "PBxCantidad": "sum"
        })

        toneladas_total = df["Toneladas"].sum()

        # CÁLCULOS #
        df["PrecioPromedio"] = df.apply(
            lambda x: x["ImporteVenta"] / x["Cantidad"] if x["Cantidad"] != 0 else 0,
            axis=1
        )

        df["DescEquivPL"] = df.apply(
            lambda x: 1 - (x["PrecioPromedio"] / x["PrecioBase"]) if x["PrecioBase"] != 0 else 0,
            axis=1
        )

        df = df.fillna(0)

        # DESC. PONDERADO DE VENTA #
        total_importe = df["ImporteVenta"].sum()
        total_pb = df["PBxCantidad"].sum()

        if total_pb != 0:
            descuento_ponderado = -((total_importe / total_pb) - 1)
        else:
            descuento_ponderado = 0

        # KPIs POR TIPO #
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

        # ORDENAR POR ARTÍCULO # 
        df = df.sort_values(by="ImporteVenta",ascending=False)

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

    mensaje = ""

    # HISTÓRICO XLP #
    historico_xlp = []
    mes_historico = []
    meses_tabla_historico = []
    meses_disponibles = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"]
    hoy = date.today()

    meses_historico = ["TODOS"] + meses_disponibles[:hoy.month - 1]

    color_tabla = "tabla-thw-default"

    cantidad_total = 0
    importe_venta_total = 0
    precio_promedio = 0

    almacenes = []
    gerentes = []

    df = None

    if request.method == "POST":

        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")

        mes_historico = request.form.getlist("mes_historico")
        print("MES SELECCIONADO:", mes_historico)
        
        fecha_inicio_sel = fecha_inicio
        fecha_fin_sel = fecha_fin

        hoy = date.today()

        fecha_inicio_historico = date(
            hoy.year,
            1,
            1
        ).isoformat()
 
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

        # CARGAR DATOS HISTÓRICOS XLP #
        parametros_historico = parametros.copy()

        parametros_historico["fecha_inicio"] = fecha_inicio_historico
        parametros_historico["fecha_fin"] = fecha_fin
 
        df_xlp_historico = ejecutar_sql_desde_archivo(
            ruta_sql,
            parametros_historico
        )
        if not mes_historico:

            df_xlp_historico = df_xlp_historico.iloc[0:0]
       
        # PREPARAR HISTÓRICO XLP #
        if not df_xlp_historico.empty:
            df_xlp_historico["FechaEmision"] = pd.to_datetime(
                df_xlp_historico["FechaEmision"]
            )

            if "TODOS" not in mes_historico:

                numeros_mes = [
                    meses_disponibles.index(mes) + 1
                    for mes in mes_historico
                ]

                df_xlp_historico = df_xlp_historico[
                    df_xlp_historico["FechaEmision"].dt.month.isin(numeros_mes)
                ]
    
        df_xlp_historico["FechaEmision"] = df_xlp_historico["FechaEmision"].dt.date
    
        # TABLA HISTÓRICO XLP #

        if not df_xlp_historico.empty:

            for col in [
                "Cantidad",
                "ImporteVenta",
                "PrecioBase"
        ]:

                df_xlp_historico[col] = pd.to_numeric(
                    df_xlp_historico[col],
                    errors="coerce"
                ).fillna(0)

            df_xlp_historico["Mes"] = df_xlp_historico["FechaEmision"].apply(
                lambda x: meses_disponibles[x.month - 1]
            )
            
            historico_xlp_df = df_xlp_historico.groupby(
                ["Articulo","Mes"],
                as_index=False
            ).agg({

                "Cantidad":"sum",
                "ImporteVenta":"sum",
                "PrecioBase":"mean"

        })
 
            historico_xlp_df["PrecioPromedio"] = (
            historico_xlp_df["ImporteVenta"] /
            historico_xlp_df["Cantidad"]
        ).replace(
            [float("inf"), -float("inf")],
            0
        )

            historico_xlp_df["DescEquivPL"] = (
                1 -
                (
                    historico_xlp_df["PrecioPromedio"] /
                    historico_xlp_df["PrecioBase"]
                )
            ).replace(
                [float("inf"), -float("inf")],
                0
            )

            historico_tabla = {}

            for _, fila in historico_xlp_df.iterrows():

                articulo = fila["Articulo"]
                mes = fila["Mes"]

                if articulo not in historico_tabla:
                    historico_tabla[articulo] = {
                        "Articulo": articulo
                    }

                historico_tabla[articulo][
                    f"{mes}_Cantidad"
                ] = fila["Cantidad"]
                
                historico_tabla[articulo][
                    f"{mes}_Precio"
                ] = fila["PrecioPromedio"]

                historico_tabla[articulo][
                    f"{mes}_Desc"
                ] = fila["DescEquivPL"]

            historico_xlp = list(
                historico_tabla.values()
            )
         
        if gerente:

            df = df[
                df["GerenteRegional"] == gerente
            ]


        if df is None or df.empty:

            mensaje = (
                "Aún no existen facturas registradas "
                "para el rango de fechas seleccionado."
            )

            return render_template(
                "cable_xlp.html",
                datos=[],
                historico_xlp=[],
                fecha_inicio=fecha_inicio_sel,
                fecha_fin=fecha_fin_sel,
                almacenes=[],
                gerentes=[],
                cantidad_total=0,
                importe_venta_total=0,
                descuento_ponderado=0,
                color_tabla=color_tabla,
                mensaje=mensaje,
                meses_historico=meses_historico
            )

        # FILTROS DINÁMICOS #
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

        # NUMÉRICOS #
        for col in [
            "Cantidad",
            "ImporteVenta",
            "PrecioBase"
        ]:

            df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)
            
        # DESC. PONDERADO #
        total_venta = df["ImporteVenta"].sum()
        total_pb = (
            df["PrecioBase"] *
            df["Cantidad"]
        ).sum()

        if total_pb != 0:
            descuento_ponderado = (
                1 -
                (total_venta / total_pb)
            )

        else:
            descuento_ponderado = 0


        # TOTALES #
        cantidad_total = (
            df["Cantidad"]
            .sum()
        )

        importe_venta_total = (
            df["ImporteVenta"]
            .sum()
        )

        # AGRUPACIÓN #
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

        # DESC. EQUIV SOBRE PL #
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

        # Meses que se mostrarán en la tabla histórica #
        if "TODOS" in mes_historico:
            meses_tabla_historico = meses_historico[1:]
        else:
            meses_tabla_historico = mes_historico
            
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
        color_tabla=color_tabla,
        mensaje=mensaje,
        meses_historico=meses_historico,
        mes_historico=mes_historico,
        meses_tabla_historico=meses_tabla_historico,
        historico_xlp=historico_xlp
    )

@dashboard.route("/tuberia", methods=["GET", "POST"])
def tuberia():

    print("ENTRANDO A TUBERIA")

    datos = []

    fecha_inicio_sel = ""
    fecha_fin_sel = ""

    descuento_ponderado = 0

    # HISTÓRICO TUBERÍA #
    historico_tuberia = []
    mes_historico = []
    meses_tabla_historico = []

    meses_disponibles = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"]

    hoy = date.today()

    meses_historico = [
        "TODOS"
    ] + meses_disponibles[:hoy.month - 1]

    color_tabla = "tabla-thw-default"

    cantidad_total = 0
    importe_total = 0

    marcas = []
    lineas = []
    almacenes = []
    gerentes = []

    df = None

    if request.method == "POST":

        fecha_inicio = request.form.get("fecha_inicio")
        fecha_fin = request.form.get("fecha_fin")

        mes_historico = request.form.getlist("mes_historico")
        print("MESES HISTÓRICO SELECCIONADOS:", mes_historico)
        
        fecha_inicio_sel = fecha_inicio
        fecha_fin_sel = fecha_fin

        hoy = date.today()

        fecha_inicio_historico = date(
            hoy.year,
            1,
            1
            ).isoformat()

        marca = request.form.get("marca") or None
        linea = request.form.get("linea") or None
        almacen = request.form.get("almacen") or None
        gerente = request.form.get("gerente") or None

        print("MARCA SELECCIONADA:", marca)
        print("LINEA SELECCIONADA:", linea)


        parametros = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "marca": marca,
            "linea": linea,
            "almacen": almacen,
            "gerente": gerente
        }

        for k, v in parametros.items():
            if v == "":
                parametros[k] = None

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
            "TUBERIA.sql"
        )

        df = ejecutar_sql_desde_archivo(
            ruta_sql,
            parametros
        )

        # CARGAR DATOS HISTÓRICOS TUBERÍA #
        parametros_historico = parametros.copy()

        parametros_historico["fecha_inicio"] = fecha_inicio_historico
        parametros_historico["fecha_fin"] = fecha_fin

        # La marca SÍ debe afectar el histórico. La línea seleccionada NO debe limitar el histórico #
        parametros_historico["linea"] = None

        df_tuberia_historico = ejecutar_sql_desde_archivo(
            ruta_sql,
            parametros_historico
        )

        # Si no se seleccionaron meses, no mostrar información histórica #
        if not mes_historico:
            df_tuberia_historico = df_tuberia_historico.iloc[0:0]

        # PREPARAR HISTÓRICO TUBERÍA #
        if not df_tuberia_historico.empty:

            df_tuberia_historico["FechaEmision"] = pd.to_datetime(
                df_tuberia_historico["FechaEmision"]
            )

            # Filtrar meses seleccionados #
            if "TODOS" not in mes_historico:
                numeros_mes = [
                    meses_disponibles.index(mes) + 1
                    for mes in mes_historico
                ]

                df_tuberia_historico = df_tuberia_historico[
                    df_tuberia_historico["FechaEmision"].dt.month.isin(
                        numeros_mes
                    )
                ]


            # Convertir columnas numéricas #
            for col in [
                "Cantidad",
                "ImporteVenta",
                "PrecioBase"
            ]:

                df_tuberia_historico[col] = pd.to_numeric(
                    df_tuberia_historico[col],
                    errors="coerce"
                ).fillna(0)

            # Obtener nombre del mes #
            df_tuberia_historico["Mes"] = (
                df_tuberia_historico["FechaEmision"].apply(
                    lambda x:
                    meses_disponibles[x.month - 1]
                )
            )

            # AGRUPAR POR LÍNEA Y MES #
            historico_tuberia_df = (
                df_tuberia_historico
                .groupby(
                    ["Linea", "Mes"],
                    as_index=False
                )
                .agg({

                    "Cantidad": "sum",
                    "ImporteVenta": "sum",
                    "PrecioBase": "mean"
                })
            )

            # PRECIO PROMEDIO #
            historico_tuberia_df["PrecioPromedio"] = (

                historico_tuberia_df["ImporteVenta"] /
                historico_tuberia_df["Cantidad"]

            ).replace(
                [float("inf"), -float("inf")],
                0
            )

            # DESCUENTO EQUIVALENTE SOBRE PL #
            historico_tuberia_df["DescEquivPL"] = (

                1 -
                (
                    historico_tuberia_df["PrecioPromedio"] /
                    historico_tuberia_df["PrecioBase"]
                )

            ).replace(
                [float("inf"), -float("inf")],
                0
            )

            # CREAR ESTRUCTURA PARA LA TABLA #
            historico_tabla = {}

            for _, fila in historico_tuberia_df.iterrows():
                linea_historica = fila["Linea"]
                mes = fila["Mes"]

                if linea_historica not in historico_tabla:
                    historico_tabla[linea_historica] = {
                        "Linea": linea_historica
                    }

                historico_tabla[linea_historica][
                    f"{mes}_Cantidad"
                ] = fila["Cantidad"]

                historico_tabla[linea_historica][
                    f"{mes}_Precio"
                ] = fila["PrecioPromedio"]

                historico_tabla[linea_historica][
                    f"{mes}_Desc"
                ] = fila["DescEquivPL"]

            historico_tuberia = list(
                historico_tabla.values()
            )

        print("PARAMETROS ENVIADOS:", parametros)
        print("REGISTROS OBTENIDOS:", len(df))

        if df is None or df.empty:

            return render_template(
                "tuberia.html",
                datos=[],
                descuento_ponderado=0,
                fecha_inicio=fecha_inicio_sel,
                fecha_fin=fecha_fin_sel,
                marcas=[],
                lineas=[],
                almacenes=[],
                gerentes=[],
                cantidad_total=0,
                importe_total=0,
                color_tabla=color_tabla,

                meses_historico=meses_historico,
                mes_historico=mes_historico,
                meses_tabla_historico=[],

                historico_tuberia=[]
            )
        
        marcas = [
            "KOBREX",
            "RYMCO",
            "JUPITER"
        ]

        # OBTENER TODAS LAS LÍNEAS DISPONIBLES SEGÚN LA MARCA SELECCIONADA #
        parametros_lineas = {
            "fecha_inicio": fecha_inicio,
            "fecha_fin": fecha_fin,
            "marca": marca,
            "linea": None,
            "almacen": None,
            "gerente": None
        }

        df_lineas = ejecutar_sql_desde_archivo(
            ruta_sql,
            parametros_lineas
        )

        if df_lineas is not None and not df_lineas.empty:

            lineas = sorted(
                df_lineas["Linea"]
                .dropna()
                .astype(str)
                .str.strip()
                .unique()
                .tolist()
        )

        else:

            lineas = []

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

        total_importe = df["ImporteVenta"].sum()
        total_pb = df["PBxCantidad"].sum()

        if total_pb != 0:

            descuento_ponderado = (
                1 - (total_importe / total_pb)
            )

        else:

            descuento_ponderado = 0

        cantidad_total = df["Cantidad"].sum()
        importe_total = df["ImporteVenta"].sum()

        df = df.groupby(
            "Articulo",
            as_index=False
        ).agg({

            "PrecioBase": "mean",
            "Cantidad": "sum",
            "ImporteVenta": "sum",
            "PBxCantidad": "sum"

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
                1 - (
                    x["PrecioPromedio"] /
                    x["PrecioBase"]
                )
                if x["PrecioBase"] != 0
                else 0,
            axis=1
        )

        df = df.fillna(0)

        total_importe = df["ImporteVenta"].sum()
        total_pb = df["PBxCantidad"].sum()

        if total_pb != 0:

            descuento_ponderado = -(
                (total_importe / total_pb) - 1
            )

        else:

            descuento_ponderado = 0

        df = df.sort_values(
            "ImporteVenta",
            ascending=False
        )

        datos = df.to_dict(
            orient="records"
        )

        # Meses que se mostrarán en la tabla histórica
        if "TODOS" in mes_historico:
            meses_tabla_historico = meses_historico[1:]
        else:
            meses_tabla_historico = mes_historico

    return render_template(
        "tuberia.html",
        datos=datos,
        descuento_ponderado=descuento_ponderado,
        fecha_inicio=fecha_inicio_sel,
        fecha_fin=fecha_fin_sel,
        marcas=marcas,
        lineas=lineas,
        almacenes=almacenes,
        gerentes=gerentes,
        cantidad_total=cantidad_total,
        importe_total=importe_total,
        color_tabla=color_tabla,
        meses_historico=meses_historico,
        mes_historico=mes_historico,
        meses_tabla_historico=meses_tabla_historico,
        historico_tuberia=historico_tuberia

    )

@dashboard.route("/tuberia_lineas", methods=["POST"])
def tuberia_lineas():

    marca = request.form.get("marca") or None

    parametros = {
        "fecha_inicio": request.form.get("fecha_inicio"),
        "fecha_fin": request.form.get("fecha_fin"),
        "marca": marca,
        "linea": None,
        "almacen": None,
        "gerente": None
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
        "TUBERIA.sql"
    )

    df = ejecutar_sql_desde_archivo(
        ruta_sql,
        parametros
    )

    if df is None or df.empty:
        return jsonify([])

    lineas = sorted(
        df["Linea"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
        .tolist()
    )

    print("MARCA PARA LINEAS:", marca)
    print("LINEAS ENCONTRADAS:", lineas)

    return jsonify(lineas)

def cargar_ponderados_compra():

    BASE_DIR = os.path.abspath(
        os.path.join(
            os.path.dirname(__file__),
            "..",
            ".."
        )
    )

    ruta_excel = os.path.join(
        BASE_DIR,
        "PONDERADO COMPRA",
        "PONDERADOS COMPRA REPORTE PYTHON.xlsx"
    )

    df = pd.read_excel(
        ruta_excel,
        sheet_name="Hoja1"
    )

    # NORMALIZAR COLUMNAS EXCEL
    df.columns = [
        "Mes",
        "Condumex Desc. Pond. Compra",
        "Condulac Desc. Pond. Compra",
        "Condulac Cal. 12 Compra",
        "Kobrex Desc. Pond. Compra",
        "Kobrex Cal. 12 Compra",
        "Serie 8000 Desc. Pond. Compra"
    ]

    return df

def aplicar_ponderado_compra_excel(
    fila,
    mes,
    ponderados_compra
):

    meses_disponibles = [
        "ENERO", "FEBRERO", "MARZO", "ABRIL",
        "MAYO", "JUNIO", "JULIO", "AGOSTO",
        "SEPTIEMBRE", "OCTUBRE", "NOVIEMBRE", "DICIEMBRE"
    ]

    nombre_mes = meses_disponibles[mes - 1]

    ponderado_mes = ponderados_compra[
        ponderados_compra["Mes"]
        .astype(str)
        .str.upper()
        .str.strip()
        == nombre_mes
    ]

    if ponderado_mes.empty:
        return

    registro = ponderado_mes.iloc[0]

    # DESCUENTOS PONDERADOS COMPRA #

    fila["condumex_costo"] = registro.iloc[1]
    fila["condulac_costo"] = registro.iloc[2]
    fila["kobrex_costo"] = registro.iloc[4]
    fila["serie8000_costo"] = registro.iloc[6]

    # CAL. 12 COMPRA # 

    fila["cal12_condulac_costo"] = registro.iloc[3]
    fila["cal12_kobrex_costo"] = registro.iloc[5]
    

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

    # CONVERTIDORES #
    convertidores = cargar_convertidores()

    # PONDERADOS COMPRA EXCEL #
    ponderados_compra = cargar_ponderados_compra()
    
    # RUTAS SQL #

    ruta_thw = os.path.join(
        BASE_DIR,
        "sql",
        "backup_sql",
        "THW.sql"
    )

    ruta_desnudo = os.path.join(
        BASE_DIR,
        "sql",
        "backup_sql",
        "DESNUDO.sql"
    )

    ruta_serie = os.path.join(
        BASE_DIR,
        "sql",
        "backup_sql",
        "SERIE_8000.sql"
    )

    ruta_thw_compra = os.path.join(
        BASE_DIR,
        "sql",
        "backup_sql",
        "THW_COMPRA.sql"
    )

    ruta_serie_compra = os.path.join(
        BASE_DIR,
        "sql",
        "backup_sql",
        "S8000_COMPRA.sql"
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

    def calcular_descuento_costo(df):

        if df is None or df.empty:
            return 0

        costo_mxn = pd.to_numeric(
            df["Costo MXN"],
            errors="coerce"
        ).fillna(0)

        cantidad = pd.to_numeric(
            df["Cantidad"],
            errors="coerce"
        ).fillna(0)

        importe_bruto = (
            costo_mxn *
            cantidad
        ).sum()

        importe_neto = pd.to_numeric(
            df["ImporteMXN"],
            errors="coerce"
        ).fillna(0).sum()

        if importe_bruto == 0:
            return 0

        return 1 - (
            importe_neto /
            importe_bruto
        )

    def calcular_cal12_costo(df, descuento_ponderado, aplicar_pp=False):

        if df is None or df.empty:
            return 0

        calibre12 = df[
            df["Calibre"]
            .astype(str)
            .str.strip()
            .eq("12")
        ]

        if calibre12.empty:
            return 0

        costo = pd.to_numeric(
            calibre12["Costo MXN"],
            errors="coerce"
        ).fillna(0)

        cantidad = pd.to_numeric(
            calibre12["Cantidad"],
            errors="coerce"
        ).fillna(0)

        cantidad_total = cantidad.sum()

        if cantidad_total == 0:
            return 0

        costo_ponderado = (
            (costo * cantidad).sum()
            / cantidad_total
        )

        resultado = (
            costo_ponderado *
            (1 - descuento_ponderado)
        )

        if aplicar_pp:
            resultado *= 0.94

        return resultado
    
    def crear_fila_resumen(periodo):

        return {

            "fecha": periodo,

            "condumex_costo": 0,
            "condumex": 0,
            "cal12_condumex": 0,
            "ton_condumex": 0,

            "condulac_costo": 0,
            "cal12_condulac_costo": 0,
            "condulac": 0,
            "cal12_condulac": 0,
            "ton_condulac": 0,

            "kobrex_costo": 0,
            "cal12_kobrex_costo": 0,
            "kobrex": 0,
            "cal12_kobrex": 0,
            "ton_kobrex": 0,

            "desnudo": 0,
            "cal12_desnudo": 0,

            "serie8000_costo": 0,
            "serie8000": 0,
            "ton_serie8000": 0
        }

    def procesar_thw(fila, df_thw):

        if df_thw is not None and not df_thw.empty:

            df_thw["Articulo"] = (
                df_thw["Articulo"]
                .astype(str)
                .str.strip()
            )

            df_thw = df_thw.merge(
                convertidores,
                left_on="Articulo",
                right_on="ARTICULO",
                how="left"
            )

            df_thw["KG/M"] = pd.to_numeric(
                df_thw["KG/M"],
                errors="coerce"
            ).fillna(0)

            df_thw["Cantidad"] = pd.to_numeric(
                df_thw["Cantidad"],
                errors="coerce"
            ).fillna(0)

            df_thw["Toneladas"] = (
                df_thw["Cantidad"] *
                df_thw["KG/M"]
            ) / 1000

            for marca, llave in [
               ("CONDUMEX", "condumex"),
               ("CONDULAC", "condulac"),
               ("KOBREX", "kobrex")
            ]:

                df_marca = df_thw[
                    df_thw["Categoria"] == marca
                ]

                # DESCUENTO PONDERADO VENTA #
                fila[llave] = calcular_descuento(
                    df_marca
                )

                # TONELADAS #
                fila[f"ton_{llave}"] = (
                    df_marca["Toneladas"].sum()
                )

                # CALIBRE 12 #
                calibre12 = df_marca[
                    df_marca["Calibre"] == "12"
                ]

                if not calibre12.empty:

                    precio_base_12 = (
                        calibre12["PrecioBase"]
                        .mean()
                    )

                    descuento = calcular_descuento(
                        df_marca
                    )

                    fila[f"cal12_{llave}"] = (
                        precio_base_12 *
                        (1 - descuento)
                    )

    def procesar_thw_compra(fila, df_thw_compra):

        if df_thw_compra is None or df_thw_compra.empty:
            return

        # NUMÉRICOS #
        for col in [
            "Costo MXN",
            "Cantidad",
            "ImporteMXN"
        ]:

            df_thw_compra[col] = pd.to_numeric(
                df_thw_compra[col],
                errors="coerce"
            ).fillna(0)

        # DESCUENTO PONDERADO COMPRA POR MARCA #

        for marca, llave in [
           ("CONDUMEX", "condumex"),
           ("CONDULAC", "condulac"),
           ("KOBREX", "kobrex")
        ]:

            df_marca = df_thw_compra[
                df_thw_compra["Categoria"] == marca
            ]

            fila[f"{llave}_costo"] = calcular_descuento_costo(
                df_marca
            )
    
    def procesar_desnudo(fila, df_desnudo):
        
        if df_desnudo is None or df_desnudo.empty:
            return
        
        kg = 0
        importe = 0

        if df_desnudo is not None and not df_desnudo.empty:

            kg = pd.to_numeric(
            df_desnudo["CantidadEntreConvertidor"],
            errors="coerce"
            ).fillna(0).sum()

            importe = pd.to_numeric(
            df_desnudo["ImporteVenta"],
            errors="coerce"
            ).fillna(0).sum()

        if kg != 0:

            fila["desnudo"] = importe / kg

            fila["cal12_desnudo"] = (
            fila["desnudo"] / 33.33
            )

    def procesar_serie8000(fila, df_serie):

        if df_serie is None or df_serie.empty:
            return

        df_serie["Articulo"] = (
            df_serie["Articulo"]
            .astype(str)
            .str.strip()
        )

        df_serie = df_serie.merge(
            convertidores,
            left_on="Articulo",
            right_on="ARTICULO",
            how="left"
        )

        df_serie["KG/M"] = pd.to_numeric(
            df_serie["KG/M"],
            errors="coerce"
        ).fillna(0)

        df_serie["Cantidad"] = pd.to_numeric(
            df_serie["Cantidad"],
            errors="coerce"
        ).fillna(0)

        df_serie["Toneladas"] = (
            df_serie["Cantidad"] *
            df_serie["KG/M"]
        ) / 1000 

        fila["serie8000"] = calcular_descuento(
            df_serie
        )
        
        fila["ton_serie8000"] = (df_serie["Toneladas"].sum())

    def procesar_serie8000_compra(fila, df_serie_compra):

        if df_serie_compra is None or df_serie_compra.empty:
            return

        # NUMÉRICOS #
        for col in [
            "Costo MXN",
            "Cantidad",
            "ImporteMXN"
        ]:

            df_serie_compra[col] = pd.to_numeric(
                df_serie_compra[col],
                errors="coerce"
            ).fillna(0)

        # DESCUENTO PONDERADO COMPRA #

        fila["serie8000_costo"] = calcular_descuento_costo(
            df_serie_compra
        )    

    def cargar_thw_rango(fecha_inicio, fecha_fin):

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

        return df_thw
    
    def cargar_desnudo_rango(fecha_inicio, fecha_fin):

        df_desnudo = ejecutar_sql_desde_archivo(
            ruta_desnudo,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "almacen": None,
                "gerente": None
            }
        )

        return df_desnudo

    def cargar_serie8000_rango(fecha_inicio, fecha_fin):

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

        return df_serie

    def cargar_thw_compra_rango(fecha_inicio, fecha_fin):

        df_thw_compra = ejecutar_sql_desde_archivo(
            ruta_thw_compra,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "extra_filters": ""
            }
        )

        return df_thw_compra


    def cargar_serie_compra_rango(fecha_inicio, fecha_fin):

        df_serie_compra = ejecutar_sql_desde_archivo(
            ruta_serie_compra,
            {
                "fecha_inicio": fecha_inicio,
                "fecha_fin": fecha_fin,
                "extra_filters": ""
            }
        )

        return df_serie_compra

    def preparar_fecha(df):

        if df is not None and not df.empty:

            df["FechaEmision"] = pd.to_datetime(
                df["FechaEmision"]
            ).dt.date

        return df
    
    fecha_actual = date.fromisoformat(fecha_inicio)
    fecha_final = date.fromisoformat(fecha_fin)

    # CARGA ÚNICA DEL PERIODO #
    hoy = date.today()
    anio_actual = hoy.year

    fecha_inicio_historico = date(
    anio_actual,
    1,
    1
    )

    df_thw_rango = cargar_thw_rango(
        fecha_inicio_historico,
        fecha_fin
    )

    df_desnudo_rango = cargar_desnudo_rango(
        fecha_inicio_historico,
        fecha_fin
    )

    df_serie_rango = cargar_serie8000_rango(
        fecha_inicio_historico,
        fecha_fin
    )

    df_thw_compra_rango = cargar_thw_compra_rango(
        fecha_inicio_historico,
        fecha_fin
    )

    df_serie_compra_rango = cargar_serie_compra_rango(
        fecha_inicio_historico,
        fecha_fin
    )

    df_thw_rango = preparar_fecha(
        df_thw_rango
    )

    df_desnudo_rango = preparar_fecha(
        df_desnudo_rango
    )

    df_serie_rango = preparar_fecha(
        df_serie_rango
    )

    df_thw_compra_rango = preparar_fecha(
        df_thw_compra_rango
    )
    
    df_serie_compra_rango = preparar_fecha(
        df_serie_compra_rango
    )

    # FECHAS MES ANTERIOR # 
    
    meses_disponibles = ["ENERO","FEBRERO","MARZO","ABRIL","MAYO","JUNIO","JULIO","AGOSTO","SEPTIEMBRE","OCTUBRE","NOVIEMBRE","DICIEMBRE"]

    primer_dia_mes_actual = hoy.replace(day=1)

    ultimo_dia_mes_anterior = (
        primer_dia_mes_actual -
        timedelta(days=1)
    )

    primer_dia_mes_anterior = (
        ultimo_dia_mes_anterior.replace(day=1)
    )

    # RESUMEN MESES DEL AÑO #
    meses_resumen = []
    for mes in range(1, hoy.month):
    
            primer_dia = date(
                anio_actual,
                mes,
                1
            )
    
            if mes == 12:
    
                ultimo_dia = date(
                    anio_actual,
                    12,
                    31
                )
    
            else:
    
                ultimo_dia = date(
                    anio_actual,
                    mes + 1,
                    1
                ) - timedelta(days=1)
    
            fila_mes = crear_fila_resumen(
                meses_disponibles[mes - 1]
            )

            # PONDERADO COMPRA DESDE EXCEL #

            aplicar_ponderado_compra_excel(
                fila_mes,
                mes,
                ponderados_compra
            )

            thw_mes = df_thw_rango[
                (df_thw_rango["FechaEmision"] >= primer_dia) &
                (df_thw_rango["FechaEmision"] <= ultimo_dia)
            ]
 
            desnudo_mes = df_desnudo_rango[
                (df_desnudo_rango["FechaEmision"] >= primer_dia) &
                (df_desnudo_rango["FechaEmision"] <= ultimo_dia)
            ]

            serie_mes = df_serie_rango[
                (df_serie_rango["FechaEmision"] >= primer_dia) &
                (df_serie_rango["FechaEmision"] <= ultimo_dia)
            ]
            
            procesar_thw(
                fila_mes,
                thw_mes
            )
    
            procesar_desnudo(
                fila_mes,
                desnudo_mes
            )
    
            procesar_serie8000(
                fila_mes,
                serie_mes
            )
    
            meses_resumen.append(fila_mes)

    
    while fecha_actual <= fecha_final:

        # OMITIR DOMINGOS #
        if fecha_actual.weekday() == 6:
                fecha_actual += timedelta(days=1)
                continue

        fecha_dia = fecha_actual.isoformat()

        fila = {

            "fecha": fecha_dia,

            "condumex_costo": 0,
            "condumex": 0,
            "cal12_condumex": 0,
            "ton_condumex": 0,

            "condulac_costo": 0,
            "cal12_condulac_costo": 0,
            "condulac": 0,
            "cal12_condulac": 0,
            "ton_condulac": 0,

            "kobrex_costo": 0,
            "cal12_kobrex_costo": 0,
            "kobrex": 0,
            "cal12_kobrex": 0,
            "ton_kobrex": 0,

            "desnudo": 0,
            "cal12_desnudo": 0,

            "serie8000_costo": 0,
            "serie8000": 0,
            "ton_serie8000": 0
        }

        aplicar_ponderado_compra_excel(
            fila,
            fecha_actual.month,
            ponderados_compra
        )
        # FILTRAR DATOS DEL DÍA #

        fecha_comparacion = fecha_actual

        thw_dia = df_thw_rango[
            df_thw_rango["FechaEmision"] == fecha_comparacion
        ]

        desnudo_dia = df_desnudo_rango[
            df_desnudo_rango["FechaEmision"] == fecha_comparacion
        ]

        serie_dia = df_serie_rango[
            df_serie_rango["FechaEmision"] == fecha_comparacion
        ]

        thw_compra_dia = df_thw_compra_rango[
            df_thw_compra_rango["FechaEmision"] == fecha_comparacion
        ]

        serie_compra_dia = df_serie_compra_rango[
            df_serie_compra_rango["FechaEmision"] == fecha_comparacion
        ] 

        # THW #
        procesar_thw(
            fila,
            thw_dia
        )

        procesar_thw_compra(
            fila,
            thw_compra_dia
        )

        # CAL. 12 COSTO - PONDERADO ACTUAL #

        condulac_12 = thw_compra_dia[
            thw_compra_dia["Categoria"]
            .astype(str)
            .str.upper()
            .str.strip()
            .eq("CONDULAC")
        ]

        kobrex_12 = thw_compra_dia[
            thw_compra_dia["Categoria"]
            .astype(str)
            .str.upper()
            .str.strip()
            .eq("KOBREX")
        ]

        fila["cal12_condulac_costo"] = calcular_cal12_costo(
            condulac_12,
            fila["condulac_costo"],
            aplicar_pp=True
        )

        fila["cal12_kobrex_costo"] = calcular_cal12_costo(
            kobrex_12,
            fila["kobrex_costo"]
        )
       
        # DESNUDO #
        procesar_desnudo(
            fila,
            desnudo_dia 
        )

        # SERIE 8000 #
        procesar_serie8000(
            fila,
            serie_dia
        )

        procesar_serie8000_compra(
            fila,
            serie_compra_dia
        )
        
        # GUARDAR EL DÍA COMPLETO #
        datos.append(fila)

        # SIGUIENTE DÍA #
        fecha_actual += timedelta(days=1)

    # FILA GENERAL DEL MES ACTUAL #

    primer_dia_mes_actual = hoy.replace(day=1)

    fila_general = {

    "fecha": "General",

    "condumex_costo": 0,
    "condumex": 0,
    "cal12_condumex": 0,
    "ton_condumex": 0,

    "condulac_costo": 0,
    "cal12_condulac_costo": 0,
    "condulac": 0,
    "cal12_condulac": 0,
    "ton_condulac": 0,

    "kobrex_costo": 0,
    "cal12_kobrex_costo": 0,
    "kobrex": 0,
    "cal12_kobrex": 0,
    "ton_kobrex": 0,

    "desnudo": 0,
    "cal12_desnudo": 0,

    "serie8000_costo": 0,
    "serie8000": 0,
    "ton_serie8000": 0
}

    aplicar_ponderado_compra_excel(
        fila_general,
        hoy.month,
        ponderados_compra
    )

    # DATOS DEL MES ACTUAL #

    thw_mes_actual = df_thw_rango[
        (df_thw_rango["FechaEmision"] >= primer_dia_mes_actual) &
        (df_thw_rango["FechaEmision"] <= hoy)
    ]

    desnudo_mes_actual = df_desnudo_rango[
        (df_desnudo_rango["FechaEmision"] >= primer_dia_mes_actual) &
        (df_desnudo_rango["FechaEmision"] <= hoy)
    ]

    serie_mes_actual = df_serie_rango[
        (df_serie_rango["FechaEmision"] >= primer_dia_mes_actual) &
        (df_serie_rango["FechaEmision"] <= hoy)
    ]

    thw_compra_mes_actual = df_thw_compra_rango[
        (df_thw_compra_rango["FechaEmision"] >= primer_dia_mes_actual) &
        (df_thw_compra_rango["FechaEmision"] <= hoy)
    ]

    serie_compra_mes_actual = df_serie_compra_rango[
        (df_serie_compra_rango["FechaEmision"] >= primer_dia_mes_actual) &
        (df_serie_compra_rango["FechaEmision"] <= hoy)
    ]
    
    # CALCULAR GENERAL #
    procesar_thw(
        fila_general,
        thw_mes_actual
    )

    procesar_thw_compra(
        fila_general,
        thw_compra_mes_actual
    )

    # CAL. 12 COSTO - PONDERADO ACTUAL #
    condulac_12 = thw_compra_mes_actual[
        thw_compra_mes_actual["Categoria"]
        .astype(str)
        .str.upper()
        .str.strip()
        .eq("CONDULAC")
    ]

    kobrex_12 = thw_compra_mes_actual[
        thw_compra_mes_actual["Categoria"]
        .astype(str)
        .str.upper()
        .str.strip()
        .eq("KOBREX")
    ]
   
    fila_general["cal12_condulac_costo"] = calcular_cal12_costo(
        condulac_12,
        fila_general["condulac_costo"],
        aplicar_pp=True
    )

    fila_general["cal12_kobrex_costo"] = calcular_cal12_costo(
        kobrex_12,
        fila_general["kobrex_costo"]
    )
 
    procesar_desnudo(
        fila_general,
        desnudo_mes_actual
    )

    procesar_serie8000(
        fila_general,
        serie_mes_actual
    )

    procesar_serie8000_compra(
        fila_general,
        serie_compra_mes_actual
    )

    # AGREGAR AL FINAL DE PONDERADO ACTUAL #
    datos.append(fila_general)

    return render_template(
        "resumen.html",
        datos=datos,
        meses_resumen=meses_resumen
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

    # AGREGAR CONVERTIDOR KG/M #
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

    # NUMÉRICOS #
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

    # TONELADAS #
    df["Toneladas"] = (
    df["Cantidad"] *
    df["KG/M"]
    ) / 1000

    # AGRUPACIÓN #
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

    # CÁLCULOS #
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

    # PROCESAR REPORTE CALIBRE #
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

    # COLUMNAS QUE SE EXPORTARÁN #
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

    # PROCESAR REPORTE ARTICULOS #
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

    # COLUMNAS QUE SE EXPORTARÁN #
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

    # AGREGAR KG/M #
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

    # FILTRO GERENTE #
    if gerente:

        df = df[
            df["GerenteRegional"] == gerente
        ]

    # NUMÉRICOS #
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

    # AGRUPACIÓN IGUAL A TABLA #
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

    # NUMÉRICOS #
    for col in [
        "Cantidad",
        "ImporteVenta",
        "PrecioBase"
    ]:

        df[col] = pd.to_numeric(
            df[col],
            errors="coerce"
        ).fillna(0)

    # AGRUPACIÓN IGUAL QUE TABLA #
    df = df.groupby(
        "Articulo",
        as_index=False
    ).agg({

        "Cantidad":"sum",
        "ImporteVenta":"sum",
        "PrecioBase":"mean"
    })

    # PRECIO PROMEDIO #
    df["PrecioPromedio"] = df.apply(

        lambda x:
        x["ImporteVenta"] / x["Cantidad"]
        if x["Cantidad"] != 0
        else 0,
        axis=1
    )

    # DESC. EQUIV SOBRE PL #
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

    # TABLA RÉPLICA EXCEL #
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

@dashboard.route("/descargar_tuberia", methods=["POST"])
def descargar_tuberia():

    fecha_inicio = request.form.get("fecha_inicio")
    fecha_fin = request.form.get("fecha_fin")

    marca = request.form.get("marca") or None
    linea = request.form.get("linea") or None
    almacen = request.form.get("almacen") or None
    gerente = request.form.get("gerente") or None

    parametros = {
        "fecha_inicio": fecha_inicio,
        "fecha_fin": fecha_fin,
        "marca": marca,
        "linea": linea,
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
        "TUBERIA.sql"
    )

    df = ejecutar_sql_desde_archivo(
        ruta_sql,
        parametros
    )

    if df is None or df.empty:

        return render_template(
            "tuberia.html",
            datos=[],
            descuento_ponderado=0,
            fecha_inicio=fecha_inicio,
            fecha_fin=fecha_fin,
            marcas=["KOBREX", "RYMCO", "JUPITER"],
            lineas=[],
            almacenes=[],
            gerentes=[],
            cantidad_total=0,
            importe_total=0,
            color_tabla="tabla-thw-default"
        )

    # CONVERTIR CAMPOS NUMÉRICOS

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

    # AGRUPAR POR ARTÍCULO

    df = df.groupby(
        "Articulo",
        as_index=False
    ).agg({

        "PrecioBase": "mean",
        "Cantidad": "sum",
        "ImporteVenta": "sum",
        "PBxCantidad": "sum"

    })

    # PRECIO PROMEDIO

    df["PrecioPromedio"] = df.apply(
        lambda x:
            x["ImporteVenta"] / x["Cantidad"]
            if x["Cantidad"] != 0
            else 0,
        axis=1
    )

    # DESCUENTO EQUIVALENTE SOBRE PL

    df["DescEquivPL"] = df.apply(
        lambda x:
            1 - (
                x["PrecioPromedio"] /
                x["PrecioBase"]
            )
            if x["PrecioBase"] != 0
            else 0,
        axis=1
    )

    df = df.fillna(0)

    # COLUMNAS DEL EXCEL

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
            sheet_name="TUBERIA"
        )

    archivo.seek(0)

    return send_file(
        archivo,
        download_name="Reporte_Tuberia.xlsx",
        as_attachment=True
    )




