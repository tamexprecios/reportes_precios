from flask import Flask, render_template, request

from src.data.excel.ventas import cargar_ventas_2026
from src.calculos.margen import (calcular_metricas,calcular_evolucion_mensual,calcular_contribucion_utilidad)

app = Flask(__name__)

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

fin_contribucion = time.perf_counter()

print(
    f"[OK] Cálculo contribución utilidad: "
    f"{fin_contribucion - inicio_contribucion:.2f} segundos"
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

    marca_seleccionada = request.args.get(
        "marca",
        "TODAS"
    )

    df_filtrado = df_ventas.copy()

    if marca_seleccionada != "TODAS":

        df_filtrado = df_filtrado[
            df_filtrado["Categoria"]
            .astype(str)
            .str.strip()
            == marca_seleccionada
        ].copy()

    metricas_filtradas = calcular_metricas(
        df_filtrado
    )

    return render_template(

        "dashboard.html",

        evolucion_mensual=evolucion_mensual,
        contribucion_utilidad=contribucion_utilidad,
        
        venta=formato_moneda(
            metricas["venta"]
        ),

        costo_promedio=formato_moneda(
            metricas["costo_promedio"]
        ),

        margen_promedio=formato_porcentaje(
            metricas_filtradas["margen_promedio"]
        ),

        costo_ppp=formato_moneda(
            metricas["costo_ppp"]
        ),

        margen_ppp=formato_porcentaje(
            metricas_filtradas["margen_ppp"]
        ),

        marcas=marcas,

        marca_seleccionada=marca_seleccionada,
    )


