import streamlit as st
import sys
import os

# permitir que Python encuentre "src"
sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))

from src.data.conexion_sql import obtener_datos

st.set_page_config(
    page_title="Reporte de Márgenes",
    page_icon="📊",
    layout="wide"
)

st.title("📊 Margen de Utilidad en Pedidos Afectados")
st.write("Reportes Área de Precios")

# Cargar datos
df = obtener_datos()

st.subheader("Datos desde SQL Server")
st.dataframe(df)