from waitress import serve
from app import app


if __name__ == "__main__":

    print("SERVIDOR WAITRESS INICIADO")
    print ("http://192.168.60.105:8080")
    serve(
        app,
        host="0.0.0.0",
        port=8080
    )