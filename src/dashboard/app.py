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
API_URL = "https://reportes-precios.onrender.com"

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
df = obtener_datos_api()

st.subheader("Datos desde API")
st.dataframe(df)