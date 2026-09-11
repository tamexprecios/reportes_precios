import time

inicio = time.perf_counter()

print("=" * 60)
print("INICIANDO REPORTE DE UTILIDAD")
print("=" * 60)

print("\nCargando aplicación...")

from waitress import serve
from app import app

fin_carga = time.perf_counter()

tiempo_carga = fin_carga - inicio

print("\n" + "=" * 60)
print("CARGA COMPLETADA")
print("=" * 60)

print("Todos los archivos y datos fueron cargados correctamente.")
print(f"Tiempo de carga: {tiempo_carga:.2f} segundos")

print("\nSERVIDOR WAITRESS INICIADO")
print("Acceso local: http://127.0.0.1:5050")
print("Acceso en red: http://192.168.60.105:5050")

print("=" * 60)
print("APLICACIÓN LISTA PARA USARSE")
print("=" * 60)

serve(
    app,
    host="0.0.0.0",
    port=5050
)
