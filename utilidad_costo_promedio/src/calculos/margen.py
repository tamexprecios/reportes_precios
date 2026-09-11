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

def calcular_evolucion_mensual(df: pd.DataFrame) -> list:
    """
    Calcula la evolución mensual del margen de utilidad
    con costo promedio y costo con PPP.
    """

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

    df = df.copy()

    df["FechaEmision"] = pd.to_datetime(
        df["FechaEmision"],
        errors="coerce"
    )

    df = df.dropna(
        subset=["FechaEmision"]
    )

    resultados = []

    for numero_mes, nombre_mes in meses.items():

        df_mes = df[
            df["FechaEmision"].dt.month == numero_mes
        ].copy()

        if df_mes.empty:
            continue

        venta = df_mes["SubTotalMN"].sum()

        costo_promedio = df_mes["ImporteCosto"].sum()

        costo_ppp = df_mes["ImporteCostoPPP"].sum()

        utilidad_promedio = (
            venta - costo_promedio
        )

        utilidad_ppp = (
            venta - costo_ppp
        )

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

        resultados.append({
            "mes": nombre_mes,
            "margen_promedio": margen_promedio,
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
