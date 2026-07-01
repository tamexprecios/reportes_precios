from flask import Blueprint, render_template, request


dashboard = Blueprint(
    "dashboard",
    __name__
)


@dashboard.route("/thw", methods=["GET", "POST"])
def thw():


    datos = None


    if request.method == "POST":


        fecha_inicio = request.form.get(
            "fecha_inicio"
        )


        fecha_fin = request.form.get(
            "fecha_fin"
        )


        marca = request.form.get(
            "marca"
        )


        almacen = request.form.get(
            "almacen"
        )


        gerente = request.form.get(
            "gerente"
        )


        datos = {

            "fecha_inicio": fecha_inicio,

            "fecha_fin": fecha_fin,

            "marca": marca,

            "almacen": almacen,

            "gerente": gerente

        }


    return render_template(
        "cable_thw.html",
        datos=datos
    )


@dashboard.route("/desnudo")
def desnudo():

    return render_template(
        "cable_desnudo.html"
    )


@dashboard.route("/serie8000")
def serie8000():

    return render_template(
        "cable_serie8000.html"
    )


@dashboard.route("/resumen")
def resumen():

    return render_template(
        "resumen.html"
    )