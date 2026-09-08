from flask import Flask, render_template, request

from src.data.excel.ventas import cargar_ventas_2026
from src.calculos.margen import calcular_metricas


app = Flask(__name__)


# ============================================================
# CARGA DE DATOS
# ============================================================

df_ventas = cargar_ventas_2026()

metricas = calcular_metricas(df_ventas)

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

def formato_millones(valor):
    return f"${valor / 1_000_000:,.1f} M"


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

        venta=formato_millones(
            metricas_filtradas["venta"]
        ),

        costo_promedio=formato_millones(
            metricas_filtradas["costo_promedio"]
        ),

        margen_promedio=formato_porcentaje(
            metricas_filtradas["margen_promedio"]
        ),

        costo_ppp=formato_millones(
            metricas_filtradas["costo_ppp"]
        ),

        margen_ppp=formato_porcentaje(
            metricas_filtradas["margen_ppp"]
        ),

        marcas=marcas,

        marca_seleccionada=marca_seleccionada,
    )
