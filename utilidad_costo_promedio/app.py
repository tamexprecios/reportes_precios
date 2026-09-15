from flask import Flask, render_template, request
import pandas as pd
from src.data.excel.ventas import cargar_ventas_2026
from src.calculos.margen import (
    calcular_metricas,
    calcular_evolucion_mensual,
    calcular_contribucion_utilidad,
    calcular_margen_por_linea,
    calcular_margen_por_sucursal,
    calcular_margen_por_almacen
)


app = Flask(__name__)

print("========== APP.PY ACTUALIZADO ==========")


# ============================================================
# CARGA DE DATOS
# ============================================================

import time

inicio_app = time.perf_counter()

print("\n" + "=" * 60)
print("INICIANDO CARGA DE DATOS DEL DASHBOARD")
print("=" * 60)

inicio_ventas = time.perf_counter()

df_ventas = cargar_ventas_2026()

print("\nMESES DISPONIBLES:")

print(
    pd.to_datetime(
        df_ventas["FechaEmision"],
        errors="coerce"
    )
    .dt.month
    .dropna()
    .astype(int)
    .unique()
)


fin_ventas = time.perf_counter()

print(
    f"[OK] Carga de ventas: "
    f"{fin_ventas - inicio_ventas:.2f} segundos"
)

inicio_metricas = time.perf_counter()

metricas = calcular_metricas(df_ventas)

fin_metricas = time.perf_counter()

print(
    f"[OK] Cálculo de métricas: "
    f"{fin_metricas - inicio_metricas:.2f} segundos"
)

inicio_evolucion = time.perf_counter()

evolucion_mensual = calcular_evolucion_mensual(
    df_ventas
)

fin_evolucion = time.perf_counter()

print(
    f"[OK] Cálculo de evolución mensual: "
    f"{fin_evolucion - inicio_evolucion:.2f} segundos"
)

inicio_contribucion = time.perf_counter()

contribucion_utilidad = calcular_contribucion_utilidad(
    df_ventas
)

margen_por_linea = calcular_margen_por_linea(
    df_ventas
)


fin_contribucion = time.perf_counter()

print(
    f"[OK] Cálculo contribución utilidad: "
    f"{fin_contribucion - inicio_contribucion:.2f} segundos"
)

inicio_lineas = time.perf_counter()

margen_por_linea = calcular_margen_por_linea(
    df_ventas
)

fin_lineas = time.perf_counter()

print(
    f"[OK] Cálculo margen por línea: "
    f"{fin_lineas - inicio_lineas:.2f} segundos"
)

print("\nEVOLUCIÓN MENSUAL:")
print(evolucion_mensual)

print("\nCONTRIBUCIÓN A LA UTILIDAD:")
print(contribucion_utilidad)

fin_app = time.perf_counter()

print(
    f"\nTIEMPO TOTAL DE CARGA: "
    f"{fin_app - inicio_app:.2f} segundos"
)

print("=" * 60)

marcas = sorted(
    df_ventas["Categoria"]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

lineas = sorted(
    df_ventas["Linea"]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

sucursales = sorted(
    df_ventas["NOMBRE"]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

print("\n========================================")
print("SUCURSALES DISPONIBLES PARA EL FILTRO")
print("========================================")
print(sucursales)
print("========================================")

almacenes = sorted(
    df_ventas["Almacen"]
    .dropna()
    .astype(str)
    .str.strip()
    .unique()
)

meses = [
    (1, "Enero"),
    (2, "Febrero"),
    (3, "Marzo"),
    (4, "Abril"),
    (5, "Mayo"),
    (6, "Junio"),
    (7, "Julio"),
    (8, "Agosto"),
    (9, "Septiembre"),
]

# ============================================================
# FORMATO DE MONEDA
# ============================================================
def formato_moneda(valor):
    return f"${valor:,.2f}"

def formato_porcentaje(valor):
    return f"{valor * 100:.1f}%"

# ============================================================
# DASHBOARD
# ============================================================
@app.route("/")
def dashboard():

    print("========== DASHBOARD EJECUTADO ==========")


    # ========================================================
    # FILTRO MARCA
    # ========================================================

    marca_seleccionada = request.args.get(
        "marca",
        "TODAS"
    )

    # ========================================================
    # FILTRO LÍNEA
    # ========================================================

    linea_seleccionada = request.args.get(
        "linea",
        "TODAS"
    )

    # ========================================================
    # FILTRO SUCURSAL
    # ========================================================

    sucursal_seleccionada = request.args.get(
        "sucursal",
        "TODAS"
    )

    # ========================================================
    # FILTRO ALMACÉN
    # ========================================================

    almacen_seleccionado = request.args.get(
        "almacen",
        "TODOS"
    )

    # ========================================================
    # FILTRO PERIODO
    # ========================================================

    meses_seleccionados = request.args.getlist("mes")

    if not meses_seleccionados:
        meses_seleccionados = ["TODOS"]

    # ========================================================
    # DATAFRAME BASE
    # ========================================================

    df_filtrado = df_ventas.copy()

    # ========================================================
    # APLICAR FILTRO MARCA
    # ========================================================

    if marca_seleccionada != "TODAS":

        df_filtrado = df_filtrado[
            df_filtrado["Categoria"]
            .astype(str)
            .str.strip()
            == marca_seleccionada
        ].copy()

    # ========================================================
    # OBTENER LÍNEAS DISPONIBLES
    # ========================================================

    if marca_seleccionada != "TODAS":

        lineas = sorted(
            df_filtrado["Linea"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )

    else:

        lineas = sorted(
            df_ventas["Linea"]
            .dropna()
            .astype(str)
            .str.strip()
            .unique()
        )

    # ========================================================
    # VALIDAR LÍNEA SELECCIONADA
    # ========================================================

    if linea_seleccionada != "TODAS":

        if linea_seleccionada not in lineas:

            linea_seleccionada = "TODAS"

    # ========================================================
    # VALIDAR SUCURSAL SELECCIONADA
    # ========================================================

    if sucursal_seleccionada != "TODAS":

        if sucursal_seleccionada not in sucursales:

            sucursal_seleccionada = "TODAS"

    # ========================================================
    # VALIDAR ALMACÉN SELECCIONADO
    # ========================================================

    if almacen_seleccionado != "TODOS":

        if almacen_seleccionado not in almacenes:

            almacen_seleccionado = "TODOS"

    # ========================================================
    # APLICAR FILTRO LÍNEA
    # ========================================================

    if linea_seleccionada != "TODAS":

        df_filtrado = df_filtrado[
            df_filtrado["Linea"]
            .astype(str)
            .str.strip()
            == linea_seleccionada
        ].copy()

    # ========================================================
    # APLICAR FILTRO SUCURSAL
    # ========================================================

    if sucursal_seleccionada != "TODAS":

        df_filtrado = df_filtrado[
            df_filtrado["NOMBRE"]
            .astype(str)
            .str.strip()
            == sucursal_seleccionada
        ].copy()

    # ========================================================
    # APLICAR FILTRO ALMACÉN
    # ========================================================

    if almacen_seleccionado != "TODOS":

        df_filtrado = df_filtrado[
            df_filtrado["Almacen"]
            .astype(str)
            .str.strip()
            == almacen_seleccionado
        ].copy()

    # ========================================================
    # APLICAR FILTRO PERIODO
    # ========================================================

    if "TODOS" not in meses_seleccionados:

        meses_numericos = [
            int(mes)
            for mes in meses_seleccionados
        ]

        fechas = pd.to_datetime(
            df_filtrado["FechaEmision"],
            errors="coerce"
        )

        df_filtrado = df_filtrado[
            fechas.dt.month.isin(meses_numericos)
        ].copy()

    # ========================================================
    # MÉTRICAS DEL DATAFRAME FILTRADO
    # ========================================================

    metricas_filtradas = calcular_metricas(
        df_filtrado
    )


    # ========================================================
    # EVOLUCIÓN MENSUAL / DIARIA
    # ========================================================

    if (
        "TODOS" not in meses_seleccionados
        and len(meses_seleccionados) == 1
    ):

        evolucion_mensual_filtrada = calcular_evolucion_mensual(
            df_filtrado,
            modo="dia"
        )

    else:

        evolucion_mensual_filtrada = calcular_evolucion_mensual(
            df_filtrado,
            modo="mes"
        )

    print("\n========================================")
    print("DATOS DE EVOLUCIÓN MENSUAL")
    print("========================================")
    print(evolucion_mensual_filtrada)
    print("TOTAL DE PUNTOS:", len(evolucion_mensual_filtrada))
    print("========================================")


    contribucion_utilidad_filtrada = calcular_contribucion_utilidad(
        df_filtrado
    )

    margen_por_linea_filtrado = calcular_margen_por_linea(
        df_filtrado
    )

    df_tabla_sucursal = df_ventas.copy()

    # --------------------------------------------------------
    # FILTRO MARCA
    # --------------------------------------------------------

    if marca_seleccionada != "TODAS":

        df_tabla_sucursal = df_tabla_sucursal[
            df_tabla_sucursal["Categoria"]
            .astype(str)
            .str.strip()
            == marca_seleccionada
        ].copy()

    # --------------------------------------------------------
    # FILTRO LÍNEA
    # --------------------------------------------------------

    if linea_seleccionada != "TODAS":

        df_tabla_sucursal = df_tabla_sucursal[
            df_tabla_sucursal["Linea"]
            .astype(str)
            .str.strip()
            == linea_seleccionada
        ].copy()

    # --------------------------------------------------------
    # FILTRO PERIODO
    # --------------------------------------------------------

    if "TODOS" not in meses_seleccionados:

        fechas_tabla_sucursal = pd.to_datetime(
            df_tabla_sucursal["FechaEmision"],
            errors="coerce"
        )

        df_tabla_sucursal = df_tabla_sucursal[
            fechas_tabla_sucursal.dt.month.isin(
                meses_numericos
            )
        ].copy()

    # ========================================================
    # DATAFRAME PARA TABLA POR ALMACÉN
    # ========================================================

    df_tabla_almacen = df_ventas.copy()

    # --------------------------------------------------------
    # FILTRO MARCA
    # --------------------------------------------------------

    if marca_seleccionada != "TODAS":

        df_tabla_almacen = df_tabla_almacen[
            df_tabla_almacen["Categoria"]
            .astype(str)
            .str.strip()
            == marca_seleccionada
        ].copy()

    # --------------------------------------------------------
    # FILTRO LÍNEA
    # --------------------------------------------------------

    if linea_seleccionada != "TODAS":

        df_tabla_almacen = df_tabla_almacen[
            df_tabla_almacen["Linea"]
            .astype(str)
            .str.strip()
            == linea_seleccionada
        ].copy()

    # --------------------------------------------------------
    # FILTRO PERIODO
    # --------------------------------------------------------

    if "TODOS" not in meses_seleccionados:

        fechas_tabla_almacen = pd.to_datetime(
            df_tabla_almacen["FechaEmision"],
            errors="coerce"
        )

        df_tabla_almacen = df_tabla_almacen[
            fechas_tabla_almacen.dt.month.isin(
                meses_numericos
            )
        ].copy()

    # ========================================================
    # CALCULAR TABLAS
    # ========================================================

    margen_por_sucursal_filtrado = calcular_margen_por_sucursal(
        df_tabla_sucursal
    )

    margen_por_almacen_filtrado = calcular_margen_por_almacen(
        df_tabla_almacen
    )

    return render_template(

        "dashboard.html",

        # ----------------------------------------------------
        # GRÁFICAS
        # ----------------------------------------------------

        evolucion_mensual=evolucion_mensual_filtrada,

        contribucion_utilidad=contribucion_utilidad_filtrada,

        margen_por_linea=margen_por_linea_filtrado,

        # ----------------------------------------------------
        # KPIs
        # ----------------------------------------------------

        venta=formato_moneda(
            metricas_filtradas["venta"]
        ),

        costo_promedio=formato_moneda(
            metricas_filtradas["costo_promedio"]
        ),

        margen_promedio=formato_porcentaje(
            metricas_filtradas["margen_promedio"]
        ),

        costo_ppp=formato_moneda(
            metricas_filtradas["costo_ppp"]
        ),

        margen_ppp=formato_porcentaje(
            metricas_filtradas["margen_ppp"]
        ),

        # ----------------------------------------------------
        # FILTROS
        # ----------------------------------------------------
        marcas=marcas,
        marca_seleccionada=marca_seleccionada,
        lineas=lineas,
        linea_seleccionada=linea_seleccionada,
        sucursales=sucursales,
        sucursal_seleccionada=sucursal_seleccionada,
        almacenes=almacenes,
        almacen_seleccionado=almacen_seleccionado,
        meses=meses,
        meses_seleccionados=meses_seleccionados,
        margen_por_sucursal=margen_por_sucursal_filtrado,
        margen_por_almacen=margen_por_almacen_filtrado
    )