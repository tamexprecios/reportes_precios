from flask import Flask, render_template

from routes.dashboard import dashboard


app = Flask(__name__)


app.register_blueprint(dashboard)


@app.route("/")
def inicio():

    return render_template(
        "inicio.html"
    )


if __name__ == "__main__":
    print("APP INICIADA")
    app.run(debug=True)