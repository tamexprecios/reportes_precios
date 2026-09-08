from waitress import serve
from app import app


if __name__ == "__main__":
    print("SERVIDOR WAITRESS INICIADO")
    print("Acceso local: http://127.0.0.1:5050")
    print("Acceso en red: http://192.168.60.105:5050")

    serve(
        app,
        host="0.0.0.0",
        port=5050
    )
