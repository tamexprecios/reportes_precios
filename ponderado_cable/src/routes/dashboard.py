from flask import Blueprint, render_template, request


dashboard = Blueprint(
    "dashboard",
    __name__
)

@dashboard.route("/thw", methods=["GET", "POST"])
def thw():

    import pandas as pd
    from database import ejecutar_sql_desde_archivo

    # 1. Traer datos
    df = ejecutar_sql_desde_archivo("../sql/backup_sql/THW.sql")

    # 2. Filtros (solo captura)
    filtros = {
        "fecha_inicio": request.form.get("fecha_inicio"),
        "fecha_fin": request.form.get("fecha_fin"),
        "marca": request.form.get("marca"),
        "almacen": request.form.get("almacen"),
        "gerente": request.form.get("gerente"),
    } if request.method == "POST" else {
        "fecha_inicio": None,
        "fecha_fin": None,
        "marca": None,
        "almacen": None,
        "gerente": None,
    }

    # 3. Orden de calibres
    orden_calibres = [
        "2","4","6","8","10","12","14","16","18","20",
        "250","300","350","400","500","600","750","1000",
        "1/0","2/0","3/0","4/0"
    ]

    # 4. Limpieza
    df["Cantidad"] = df["Cantidad"].fillna(0)
    df["ImporteVenta"] = df["ImporteVenta"].fillna(0)
    df["PBxCantidad"] = df["PBxCantidad"].fillna(0)

    # 5. Cálculos base
    df["PrecioPromedio"] = df["ImporteVenta"] / df["Cantidad"].replace(0, 1)
    df["DescEquivPL"] = -(df["ImporteVenta"] / df["PBxCantidad"] - 1)

    # 6. Agrupación
    tabla = df.groupby("Calibre").agg({
        "Cantidad": "sum",
        "ImporteVenta": "sum",
        "PBxCantidad": "sum"
    }).reset_index()

    tabla["PrecioPromedio"] = tabla["ImporteVenta"] / tabla["Cantidad"].replace(0, 1)
    tabla["DescEquivPL"] = -(tabla["ImporteVenta"] / tabla["PBxCantidad"] - 1)

    # 7. Orden correcto
    tabla["Calibre"] = pd.Categorical(tabla["Calibre"], categories=orden_calibres, ordered=True)
    tabla = tabla.sort_values("Calibre")

    # 8. KPI calibre 12
    desc_total = tabla.loc[tabla["Calibre"] == "12", "DescEquivPL"].values
    desc_total = desc_total[0] if len(desc_total) > 0 else 0

    # 9. Debug opcional
    print(tabla.head())
    print(len(tabla))

    return render_template(
        "cable_thw.html",
        columnas=tabla.columns,
        datos=tabla.to_dict(orient="records"),
        descuento_calibre_12=desc_total
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