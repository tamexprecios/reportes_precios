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

        if response.status_code != 200:
            st.error(f"Error conectando con la API: {response.status_code}")
            return pd.DataFrame()

        data = response.json()
        return pd.DataFrame(data)

    except Exception as e:
        st.error(f"Error de conexión: {e}")
        return pd.DataFrame()

# ---------------------------
# CARGA DE DATOS
# ---------------------------
df = obtener_datos_api()

st.subheader("Datos desde API")
st.dataframe(df)