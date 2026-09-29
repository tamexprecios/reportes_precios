from flask import Flask, render_template, request
import pandas as pd
from src.calculos.margen import obtener_lista_prefijos
from src.data.excel.ventas import cargar_ventas_2026
from src.calculos.margen import (
    calcular_metricas,
    calcular_evolucion_mensual,
    calcular_contribucion_utilidad,
    calcular_margen_por_linea,
    calcular_margen_por_articulo,
    calcular_margen_por_sucursal
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
    import time

    inicio_dashboard = time.perf_counter()
    print("========== DASHBOARD EJECUTADO ==========")

    # ========================================================
    # 1. LECTURA Y VALIDACIÓN DE PARÁMETROS
    # ========================================================

    # Filtro Marca (Múltiple)
    marca_raw = request.args.get("marca", "TODAS")
    if marca_raw and marca_raw != "TODAS":
        marcas_seleccionadas = [m.strip() for m in marca_raw.split(",") if m.strip()]
    else:
        marcas_seleccionadas = []

    # Filtro Línea (Múltiple)
    linea_raw = request.args.get("linea", "TODAS")
    if linea_raw and linea_raw != "TODAS":
        lineas_seleccionadas = [l.strip() for l in linea_raw.split(",") if l.strip()]
    else:
        lineas_seleccionadas = []

    # Filtro Sucursal
    sucursal_seleccionada = request.args.get("sucursal", "TODAS")
    if sucursal_seleccionada != "TODAS" and sucursal_seleccionada not in sucursales:
        sucursal_seleccionada = "TODAS"

    # Filtro Prefijo
    prefijo_seleccionado = request.args.get('prefijo') or request.form.get('prefijo') or 'TODOS'

    # Obtener todos los prefijos de 3 dígitos disponibles
    lista_prefijos = obtener_lista_prefijos(df_ventas)

    # Filtro Periodo (Meses)
    meses_seleccionados = request.args.getlist("mes") or ["TODOS"]

    # Filtro Día
    dia_seleccionado = request.args.get('dia', 'TODOS').strip().upper()
    mes_seleccionado = request.args.get('mes', 'TODOS')

    # Mapeo numérico de meses (si no es TODOS)
    meses_numericos = []
    if "TODOS" not in meses_seleccionados:
        mapa_meses = {
            "enero": 1, "febrero": 2, "marzo": 3, "abril": 4,
            "mayo": 5, "junio": 6, "julio": 7, "agosto": 8,
            "septiembre": 9, "octubre": 10, "noviembre": 11, "diciembre": 12,
            "ene": 1, "feb": 2, "mar": 3, "abr": 4,
            "may": 5, "jun": 6, "jul": 7, "ago": 8,
            "sep": 9, "oct": 10, "nov": 11, "dic": 12
        }
        for mes in meses_seleccionados:
            mes_str = str(mes).strip().lower()
            if mes_str in mapa_meses:
                meses_numericos.append(mapa_meses[mes_str])
            elif mes_str.isdigit():
                meses_numericos.append(int(mes_str))

    # ========================================================
    # 2. CONSTRUCCIÓN DE DATAFRAME PRINCIPAL (df_filtrado)
    # ========================================================
    df_filtrado = df_ventas.copy()

    # A) Aplicar Filtro Marca
    if marcas_seleccionadas:
        df_filtrado = df_filtrado[
            df_filtrado["Categoria"]
            .astype(str)
            .str.strip()
            .isin(marcas_seleccionadas)
        ].copy()

    # B) Obtener Líneas disponibles y validar selección
    base_lineas = df_filtrado if marcas_seleccionadas else df_ventas
    lineas = sorted(
        base_lineas["Linea"]
        .dropna()
        .astype(str)
        .str.strip()
        .unique()
    )
    lineas_seleccionadas = [l for l in lineas_seleccionadas if l in lineas]

    # C) Aplicar Filtro Línea
    if lineas_seleccionadas:
        df_filtrado = df_filtrado[
            df_filtrado["Linea"]
            .astype(str)
            .str.strip()
            .isin(lineas_seleccionadas)
        ].copy()

    # D) Aplicar Filtro Sucursal
    if sucursal_seleccionada != "TODAS":
        df_filtrado = df_filtrado[
            df_filtrado["NOMBRE"]
            .astype(str)
            .str.strip()
            == sucursal_seleccionada
        ].copy()

    # E) Aplicar Filtro Prefijo
    if prefijo_seleccionado and prefijo_seleccionado != 'TODOS':
        df_filtrado = df_filtrado[
            df_filtrado['Articulo']
            .astype(str)
            .str[:3] == prefijo_seleccionado
        ].copy()

    # F) Aplicar Filtro Meses
    if meses_numericos:
        fechas = pd.to_datetime(df_filtrado["FechaEmision"], errors="coerce")
        df_filtrado = df_filtrado[fechas.dt.month.isin(meses_numericos)].copy()

    # G) Aplicar Filtro Día
    if dia_seleccionado and dia_seleccionado not in ['TODOS', 'ALL', '', 'TODOS LOS DIAS', 'TODOS LOS DÍAS']:
        if dia_seleccionado.isdigit():
            fechas_dia = pd.to_datetime(df_filtrado["FechaEmision"], errors="coerce")
            df_filtrado = df_filtrado[fechas_dia.dt.day == int(dia_seleccionado)].copy()

    # ========================================================
    # 3. DATAFRAMES SECUNDARIOS (Tabla Sucursal / Tabla Almacén)
    # ========================================================
    
    # Tabla Sucursal (Independiente del filtro de Sucursal)
    df_tabla_sucursal = df_ventas.copy()
    if marcas_seleccionadas:
        df_tabla_sucursal = df_tabla_sucursal[
            df_tabla_sucursal["Categoria"].astype(str).str.strip().isin(marcas_seleccionadas)
        ]
    if lineas_seleccionadas:
        df_tabla_sucursal = df_tabla_sucursal[
            df_tabla_sucursal["Linea"].astype(str).str.strip().isin(lineas_seleccionadas)
        ]
    if meses_numericos:
        fechas_suc = pd.to_datetime(df_tabla_sucursal["FechaEmision"], errors="coerce")
        df_tabla_sucursal = df_tabla_sucursal[fechas_suc.dt.month.isin(meses_numericos)]
    if dia_seleccionado and dia_seleccionado.isdigit():
        fechas_suc_dia = pd.to_datetime(df_tabla_sucursal["FechaEmision"], errors="coerce")
        df_tabla_sucursal = df_tabla_sucursal[fechas_suc_dia.dt.day == int(dia_seleccionado)]

    # Tabla Almacén (Si usas un dataframe base distinto o copia)
    df_tabla_almacen = df_ventas.copy()
    if marcas_seleccionadas:
        df_tabla_almacen = df_tabla_almacen[
            df_tabla_almacen["Categoria"].astype(str).str.strip().isin(marcas_seleccionadas)
        ]
    if lineas_seleccionadas:
        df_tabla_almacen = df_tabla_almacen[
            df_tabla_almacen["Linea"].astype(str).str.strip().isin(lineas_seleccionadas)
        ]
    if meses_numericos:
        fechas_alm = pd.to_datetime(df_tabla_almacen["FechaEmision"], errors="coerce")
        df_tabla_almacen = df_tabla_almacen[fechas_alm.dt.month.isin(meses_numericos)]

    # ========================================================
    # 4. CÁLCULO DE MÉTRICAS Y TABLAS
    # ========================================================
    metricas_filtradas = calcular_metricas(df_filtrado)

    modo_evolucion = "dia" if ("TODOS" not in meses_seleccionados and len(meses_seleccionados) == 1) else "mes"
    evolucion_mensual_filtrada = calcular_evolucion_mensual(df_filtrado, modo=modo_evolucion)

    contribucion_utilidad_filtrada = calcular_contribucion_utilidad(df_filtrado)
    margen_por_linea_filtrado = calcular_margen_por_linea(df_filtrado)
    margen_por_articulo_filtrado = calcular_margen_por_articulo(df_filtrado)
    margen_por_sucursal_filtrado = calcular_margen_por_sucursal(df_tabla_sucursal)

    print(f"TIEMPO TOTAL DASHBOARD: {time.perf_counter() - inicio_dashboard:.2f} segundos")

    # ========================================================
    # 5. RENDER TEMPLATE
    # ========================================================
    return render_template(
        "dashboard.html",
        # Gráficas
        evolucion_mensual=evolucion_mensual_filtrada,
        mes_seleccionado=mes_seleccionado,
        dia_seleccionado=dia_seleccionado,
        contribucion_utilidad_filtrada=contribucion_utilidad_filtrada,
        margen_por_linea=margen_por_linea_filtrado,
        margen_articulo=margen_por_articulo_filtrado,
        margen_por_sucursal=margen_por_sucursal_filtrado,
        # KPIs
        venta=formato_moneda(metricas_filtradas["venta"]),
        costo_promedio=formato_moneda(metricas_filtradas["costo_promedio"]),
        margen_promedio=formato_porcentaje(metricas_filtradas["margen_promedio"]),
        costo_ppp=formato_moneda(metricas_filtradas["costo_ppp"]),
        margen_ppp=formato_porcentaje(metricas_filtradas["margen_ppp"]),
        # Filtros
        marcas=marcas,
        marcas_seleccionadas=marcas_seleccionadas,
        lineas=lineas,
        lineas_seleccionadas=lineas_seleccionadas,
        sucursales=sucursales,
        sucursal_seleccionada=sucursal_seleccionada,
        meses=meses,
        meses_seleccionados=meses_seleccionados,
        lista_prefijos=lista_prefijos,
        prefijo_seleccionado=prefijo_seleccionado
    )