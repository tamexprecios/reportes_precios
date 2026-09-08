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
