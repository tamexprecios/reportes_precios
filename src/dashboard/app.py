import streamlit as st
import requests
import pandas as pd

st.set_page_config(
    page_title="Reporte de Márgenes",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Margen de Utilidad en Pedidos Afectados")
st.write("Reportes Área de Precios")

# ---------------------------
# URL DE LA API
# ---------------------------
API_URL = "http://127.0.0.1:8000/datos"

# ---------------------------
# FUNCIÓN API
# ---------------------------
def obtener_datos_api():
    try:
        response = requests.get(API_URL, timeout=30)

        st.write("STATUS CODE:", response.status_code)
        st.write("RESPUESTA RAW:", response.text)

        if response.status_code != 200:
            st.error("Error conectando con la API")
            return pd.DataFrame()

        data = response.json()
        return pd.DataFrame(data)

    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()
# ---------------------------
# CARGA DE DATOS
# ---------------------------
with st.spinner("Cargando datos..."):
    df = obtener_datos_api()

# -----------------------------
# LIMPIEZA DE DATOS NUMÉRICOS
# -----------------------------
columnas_numericas = [
    "PrecioVentaFinal",
    "DescuentoLinea",
    "MargenPedidoPct",
    "Cantidad",
    "ImportexPartidaMXN",
    "Precio",
    "TipoCambio"
]

for col in columnas_numericas:
    if col in df.columns:
        df[col] = pd.to_numeric(df[col], errors="coerce")

# -----------------------------
# VALIDACIÓN
# -----------------------------
if not df.empty:

    st.subheader("📊 Indicadores generales")

    col1, col2, col3 = st.columns(3)

    with col1:
        st.metric("Pedidos", df["ID"].nunique())

    with col2:
        st.metric("Clientes", df["Cliente"].nunique())

    with col3:
        st.metric(
            "Margen promedio",
            f'{df["MargenPedidoPct"].mean():.2f}%'
        )

    st.subheader("📋 Detalle de pedidos")

    st.dataframe(
        df,
        width="stretch"
    )