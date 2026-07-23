from flask import Blueprint, render_template, request, send_file
from database import ejecutar_sql_desde_archivo
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

    marcas = []
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

        df = df.groupby(["Articulo", "Calibre"], as_index=False).agg({

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
        importe_total=importe_total,
        pb_total=pb_total,
        color_tabla=color_tabla
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


    archivo = BytesIO()


    with pd.ExcelWriter(
        archivo,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
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


    df = ejecutar_sql_desde_archivo(
        ruta_sql,
        parametros
    )


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

@dashboard.route("/descargar_serie8000", methods=["POST"])
def descargar_serie8000():

    fecha_inicio = request.form.get("fecha_inicio")
    fecha_fin = request.form.get("fecha_fin")

    almacen = request.form.get("almacen") or None
    gerente = request.form.get("gerente") or None
    tipo = request.form.get("tipo") or None

    
    extra_filters = ""

    if tipo:
        extra_filters = " AND TipoCalculado = :tipo"


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


    archivo = BytesIO()


    with pd.ExcelWriter(
        archivo,
        engine="openpyxl"
    ) as writer:

        df.to_excel(
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