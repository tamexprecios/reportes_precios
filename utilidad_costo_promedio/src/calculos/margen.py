import pandas as pd

def calcular_metricas(df: pd.DataFrame) -> dict:
    """
    Calcula las métricas generales del periodo seleccionado.
    """

    venta = df["SubTotalMN"].sum()

    costo_promedio = df["ImporteCosto"].sum()

    costo_ppp = df["ImporteCostoPPP"].sum()

    utilidad_promedio = venta - costo_promedio

    utilidad_ppp = venta - costo_ppp

    margen_promedio = (
        utilidad_promedio / venta
        if venta != 0
        else 0
    )

    margen_ppp = (
        utilidad_ppp / venta
        if venta != 0
        else 0
    )

    return {
        "venta": venta,
        "costo_promedio": costo_promedio,
        "utilidad_promedio": utilidad_promedio,
        "margen_promedio": margen_promedio,
        "costo_ppp": costo_ppp,
        "utilidad_ppp": utilidad_ppp,
        "margen_ppp": margen_ppp,
    }

def calcular_evolucion_mensual(
    df: pd.DataFrame,
    modo: str = "mes"
) -> list:
    """
    Calcula la evolución del margen de utilidad con PP.

    modo="mes":
        Devuelve un punto por cada mes.

    modo="dia":
        Devuelve un punto por cada día con información
        dentro del periodo seleccionado.
    """

    df = df.copy()

    df["FechaEmision"] = pd.to_datetime(
        df["FechaEmision"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["FechaEmision"]
    )

    resultados = []

    # ========================================================
    # EVOLUCIÓN DIARIA
    # ========================================================

    if modo == "dia":

        df["Dia"] = df["FechaEmision"].dt.date

        fechas = sorted(
            df["Dia"].unique()
        )

        for fecha in fechas:

            df_dia = df[
                df["Dia"] == fecha
            ]

            venta = df_dia["SubTotalMN"].sum()

            costo_ppp = df_dia["ImporteCostoPPP"].sum()

            utilidad_ppp = (
                venta - costo_ppp
            )

            margen_ppp = (
                utilidad_ppp / venta
                if venta != 0
                else 0
            )

            resultados.append({
                "mes": fecha.strftime("%d"),
                "margen_ppp": margen_ppp,
            })

        return resultados


    # ========================================================
    # EVOLUCIÓN MENSUAL
    # ========================================================

    meses = {
        1: "Ene",
        2: "Feb",
        3: "Mar",
        4: "Abr",
        5: "May",
        6: "Jun",
        7: "Jul",
        8: "Ago",
        9: "Sep",
        10: "Oct",
        11: "Nov",
        12: "Dic",
    }

    for numero_mes, nombre_mes in meses.items():

        df_mes = df[
            df["FechaEmision"].dt.month == numero_mes
        ].copy()

        if df_mes.empty:
            continue

        venta = df_mes["SubTotalMN"].sum()

        costo_ppp = df_mes["ImporteCostoPPP"].sum()

        utilidad_ppp = (
            venta - costo_ppp
        )

        margen_ppp = (
            utilidad_ppp / venta
            if venta != 0
            else 0
        )

        resultados.append({
            "mes": nombre_mes,
            "margen_ppp": margen_ppp,
        })

    return resultados


def calcular_contribucion_utilidad(df: pd.DataFrame) -> list:
    """
    Calcula la contribución de cada marca (Categoria)
    a la utilidad total del periodo.

    Devuelve las 9 marcas con mayor utilidad
    y agrupa el resto en 'Otras'.
    """

    df = df.copy()

    # Utilidad por registro
    df["Utilidad"] = (
        df["SubTotalMN"] - df["ImporteCostoPPP"]
    )

    # Limpiar marca
    df["Categoria"] = (
        df["Categoria"]
        .fillna("SIN MARCA")
        .astype(str)
        .str.strip()
    )

    # Agrupar por marca
    resumen = (
        df.groupby("Categoria", as_index=False)
        .agg(
            venta=("SubTotalMN", "sum"),
            utilidad=("Utilidad", "sum")
        )
    )

    # Utilidad total
    utilidad_total = resumen["utilidad"].sum()

    if utilidad_total == 0:
        return []

    # Ordenar de mayor a menor utilidad
    resumen = resumen.sort_values(
        "utilidad",
        ascending=False
    ).reset_index(drop=True)

    # 9 marcas principales
    principales = resumen.head(9).copy()

    # Resto de las marcas
    otras = resumen.iloc[9:]

    venta_otras = otras["venta"].sum()
    utilidad_otras = otras["utilidad"].sum()

    resultado = []

    # Agregar las 9 principales
    for _, fila in principales.iterrows():

        resultado.append({
            "marca": fila["Categoria"],
            "venta": fila["venta"],
            "utilidad": fila["utilidad"],
            "contribucion": fila["utilidad"] / utilidad_total,
        })

    # Agregar la décima categoría: Otras
    if not otras.empty:

        resultado.append({
            "marca": "Otras",
            "venta": venta_otras,
            "utilidad": utilidad_otras,
            "contribucion": utilidad_otras / utilidad_total,
        })

    return resultado

def calcular_margen_por_linea(df: pd.DataFrame,marca: str = "TODAS") -> list:

    """
    Calcula el margen de utilidad con costo promedio
    agrupado por línea.
    """

    df = df.copy()

    if marca != "TODAS":

        df = df[
            df["Categoria"]
            .astype(str)
            .str.strip()
            == marca
        ].copy()


    # Limpiar línea
    df["Linea"] = (
        df["Linea"]
        .fillna("SIN LÍNEA")
        .astype(str)
        .str.strip()
    )

    resumen = (
        df.groupby(
            ["Categoria", "Linea"],
            as_index=False
        )
        .agg(
            venta=("SubTotalMN", "sum"),
            costo_promedio=("ImporteCostoPPP", "sum")
        )
    )

    # Calcular utilidad
    resumen["utilidad"] = (
        resumen["venta"] - resumen["costo_promedio"]
    )

    # Calcular margen
    resumen["margen_promedio"] = (
        resumen["utilidad"] / resumen["venta"]
    ).where(
        resumen["venta"] != 0,
        0
    )

    # Ordenar de mayor a menor margen
    resumen = resumen.sort_values(
        "margen_promedio",
        ascending=False
    ).reset_index(drop=True)

    resultado = []

    for _, fila in resumen.iterrows():

        resultado.append({
            "marca": fila["Categoria"],
            "linea": fila["Linea"],
            "venta": fila["venta"],
            "costo_promedio": fila["costo_promedio"],
            "utilidad": fila["utilidad"],
            "margen_promedio": fila["margen_promedio"],
        })


    return resultado

def calcular_margen_por_sucursal(df: pd.DataFrame) -> list:
    """
    Calcula el margen de utilidad por sucursal.

    La tabla muestra una fila por cada sucursal
    disponible en el DataFrame recibido.
    """

    df = df.copy()

    # ========================================================
    # LIMPIAR NOMBRE DE SUCURSAL
    # ========================================================

    df["NOMBRE"] = (
        df["NOMBRE"]
        .fillna("SIN SUCURSAL")
        .astype(str)
        .str.strip()
    )

    # ========================================================
    # AGRUPAR POR SUCURSAL
    # ========================================================

    resumen = (
        df.groupby("NOMBRE", as_index=False)
        .agg(
            imp_venta=("SubTotalMN", "sum"),
            imp_costo=("ImporteCosto", "sum"),
            imp_costo_pp=("ImporteCostoPPP", "sum")
        )
    )

    # ========================================================
    # PORCENTAJE DE PARTICIPACIÓN EN VENTAS
    # ========================================================

    venta_total = resumen["imp_venta"].sum()

    if venta_total != 0:

        resumen["participacion"] = (
            resumen["imp_venta"] / venta_total
        )

    else:

        resumen["participacion"] = 0


    # ========================================================
    # MARGEN SIN PP
    # ========================================================

    resumen["margen_sin_pp"] = (
        (
            resumen["imp_venta"]
            - resumen["imp_costo"]
        )
        / resumen["imp_venta"]
    ).where(
        resumen["imp_venta"] != 0,
        0
    )

    # ========================================================
    # MARGEN CON PP
    # ========================================================

    resumen["margen_con_pp"] = (
        (
            resumen["imp_venta"]
            - resumen["imp_costo_pp"]
        )
        / resumen["imp_venta"]
    ).where(
        resumen["imp_venta"] != 0,
        0
    )

    # ========================================================
    # ORDENAR POR IMPORTE DE VENTA
    # ========================================================

    resumen = resumen.sort_values(
        "imp_venta",
        ascending=False
    ).reset_index(drop=True)

    # ========================================================
    # CONSTRUIR RESULTADO
    # ========================================================

    resultado = []

    for _, fila in resumen.iterrows():

        resultado.append({
            "sucursal": fila["NOMBRE"],
            "imp_venta": fila["imp_venta"],
            "imp_costo": fila["imp_costo"],
            "imp_costo_pp": fila["imp_costo_pp"],
            "margen_sin_pp": fila["margen_sin_pp"],
            "margen_con_pp": fila["margen_con_pp"],
            "participacion": fila["participacion"],
        })

    return resultado


def calcular_margen_por_almacen(df: pd.DataFrame) -> list:
    """
    Calcula el margen de utilidad por almacén.

    La tabla muestra una fila por cada almacén
    disponible en el DataFrame recibido.
    """

    df = df.copy()

    # ========================================================
    # LIMPIAR ALMACÉN
    # ========================================================

    df["Almacen"] = (
        df["Almacen"]
        .fillna("SIN ALMACÉN")
        .astype(str)
        .str.strip()
    )

    # ========================================================
    # AGRUPAR POR ALMACÉN
    # ========================================================

    resumen = (
        df.groupby("Almacen", as_index=False)
        .agg(
            imp_venta=("SubTotalMN", "sum"),
            imp_costo=("ImporteCosto", "sum"),
            imp_costo_pp=("ImporteCostoPPP", "sum")
        )
    )

    # ========================================================
    # PORCENTAJE DE PARTICIPACIÓN EN VENTAS
    # ========================================================

    venta_total = resumen["imp_venta"].sum()

    if venta_total != 0:

        resumen["participacion"] = (
            resumen["imp_venta"] / venta_total
        )

    else:

        resumen["participacion"] = 0

    # ========================================================
    # MARGEN SIN PP
    # ========================================================

    resumen["margen_sin_pp"] = (
        (
            resumen["imp_venta"]
            - resumen["imp_costo"]
        )
        / resumen["imp_venta"]
    ).where(
        resumen["imp_venta"] != 0,
        0
    )

    # ========================================================
    # MARGEN CON PP
    # ========================================================

    resumen["margen_con_pp"] = (
        (
            resumen["imp_venta"]
            - resumen["imp_costo_pp"]
        )
        / resumen["imp_venta"]
    ).where(
        resumen["imp_venta"] != 0,
        0
    )

    # ========================================================
    # ORDENAR POR IMPORTE DE VENTA
    # ========================================================

    resumen = resumen.sort_values(
        "imp_venta",
        ascending=False
    ).reset_index(drop=True)

    # ========================================================
    # CONSTRUIR RESULTADO
    # ========================================================

    resultado = []

    for _, fila in resumen.iterrows():

        resultado.append({
            "almacen": fila["Almacen"],
            "imp_venta": fila["imp_venta"],
            "imp_costo": fila["imp_costo"],
            "imp_costo_pp": fila["imp_costo_pp"],
            "margen_sin_pp": fila["margen_sin_pp"],
            "margen_con_pp": fila["margen_con_pp"],
            "participacion": fila["participacion"],
        })

    return resultado
