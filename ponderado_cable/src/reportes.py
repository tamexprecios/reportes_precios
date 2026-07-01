import pandas as pd
from database import obtener_conexion


def ejecutar_reporte():

    engine = obtener_conexion()


    consulta = """
    SELECT
    V.ID,
    V.Mov,
    V.MovId,
    V.FechaEmision,
    V.Periodo AS Mes,
    V.Moneda,
    V.TipoCambio,
    V.Estatus,
    V.Almacen,

    UPPER(REPLACE(REPLACE(REPLACE(REPLACE(V.Agente, CHAR(10), ' '), CHAR(13), ''), CHAR(34), ''), CHAR(9), '')) AS Agente,
    UPPER(REPLACE(REPLACE(REPLACE(REPLACE(G.Nombre, CHAR(10), ' '), CHAR(13), ''), CHAR(34), ''), CHAR(9), '')) AS NombreAgente,

     G.SucursalEmpresa AS [Sucursal Agente],

    CASE
        WHEN G.SucursalEmpresa = 0 THEN 'MATRIZ'
        WHEN G.SucursalEmpresa = 2 THEN 'OBSERV'
        WHEN G.SucursalEmpresa = 4 THEN 'PUEBLA'
        WHEN G.SucursalEmpresa = 5 THEN 'MERIDA-A'
        WHEN G.SucursalEmpresa = 6 THEN 'AGS'
        WHEN G.SucursalEmpresa = 7 THEN 'QUERETARO'
        WHEN G.SucursalEmpresa = 9 THEN 'COATZA'
        WHEN G.SucursalEmpresa = 10 THEN 'TAMPICO'
        WHEN G.SucursalEmpresa = 11 THEN 'CANCUN-A'
        WHEN G.SucursalEmpresa = 13 THEN 'MONTERREY'
        WHEN G.SucursalEmpresa = 14 THEN 'MARINA'
        WHEN G.SucursalEmpresa = 15 THEN 'GUADAL'
        WHEN G.SucursalEmpresa = 16 THEN 'CEDISVILLA'
        WHEN G.SucursalEmpresa = 17 THEN 'VERACRUZ'
        WHEN G.SucursalEmpresa = 19 THEN 'IZTAPALA-A'
        WHEN G.SucursalEmpresa = 20 THEN 'TOLUCA-A'
        WHEN G.SucursalEmpresa = 21 THEN 'LEON'
        WHEN G.SucursalEmpresa = 22 THEN 'SANLUIS'
        WHEN G.SucursalEmpresa = 23 THEN 'VALSEQ'
        WHEN G.SucursalEmpresa = 27 THEN 'CANCUN-A2'
        WHEN G.SucursalEmpresa = 28 THEN 'MERIDA-A2'
        WHEN G.SucursalEmpresa = 29 THEN 'ING-A'
        WHEN G.SucursalEmpresa = 30 THEN 'CULIACAN'
        WHEN G.SucursalEmpresa = 31 THEN 'CEDISMX'
        WHEN G.SucursalEmpresa = 32 THEN 'LOSCABOS'
        WHEN G.SucursalEmpresa = 33 THEN 'PACHUCA'
        WHEN G.SucursalEmpresa = 34 THEN 'TIJUANA IN'
        WHEN G.SucursalEmpresa = 35 THEN 'E-COMMERCE'
        WHEN G.SucursalEmpresa = 36 THEN 'MONTERREYB'
        WHEN G.SucursalEmpresa = 37 THEN 'PUEBLA2'
        WHEN G.SucursalEmpresa = 39 THEN 'CUERNAVACA'
        WHEN G.SucursalEmpresa = 40 THEN 'HERMOSILLO'
        WHEN G.SucursalEmpresa = 41 THEN 'CHIHUAHUA'
        WHEN G.SucursalEmpresa = 42 THEN 'LOSCABOSA2'
        WHEN G.SucursalEmpresa = 43 THEN 'SOLAR'
        WHEN G.SucursalEmpresa = 44 THEN 'ACAPULCO'
        WHEN G.SucursalEmpresa = 45 THEN 'PVALLARTA'
        ELSE 'SIN ASIGNAR'
    END AS NombreSucursalA,
     
     V.Sucursal,

    CASE
        WHEN G.SucursalEmpresa IN (0,13,15,41,36,45) THEN 'Mauricio Tabachnik'
        WHEN G.SucursalEmpresa IN (4,6,7,21,22,23) THEN 'Benjamín Cuevas'
        WHEN G.SucursalEmpresa IN (44,39,19,14,2,33,20) THEN 'José Montoya'
        WHEN G.SucursalEmpresa IN (10,17,9,5,28,11,27,16) THEN 'Dan Pérez'
        WHEN G.SucursalEmpresa IN (30,34,40,42) THEN 'Juan Antonio Angulo'
        WHEN G.SucursalEmpresa = 35 THEN 'Ecommerce'
        ELSE 'SIN ASIGNAR'
    END AS GerenteRegional,

    V.Cliente,
    T.Nombre AS NombreCliente,
    T.Rama,

    REPLACE(REPLACE(REPLACE(REPLACE(D.Articulo, CHAR(10), ' '), CHAR(13), ''), CHAR(34), ''), CHAR(9), '') AS Articulo,

    A.ClaveFabricante AS Calibre,

    REPLACE(REPLACE(REPLACE(REPLACE(A.Descripcion1, CHAR(10), ' '), CHAR(13), ''), CHAR(34), ''), CHAR(9), '') AS Descripcion,
    REPLACE(REPLACE(REPLACE(REPLACE(A.Categoria, CHAR(10), ' '), CHAR(13), ''), CHAR(34), ''), CHAR(9), '') AS Categoria,
    REPLACE(REPLACE(REPLACE(REPLACE(A.Familia, CHAR(10), ' '), CHAR(13), ''), CHAR(34), ''), CHAR(9), '') AS Familia,
    REPLACE(REPLACE(REPLACE(REPLACE(A.Linea, CHAR(10), ' '), CHAR(13), ''), CHAR(34), ''), CHAR(9), '') AS Linea,
    REPLACE(REPLACE(REPLACE(REPLACE(A.SubLinea, CHAR(10), ' '), CHAR(13), ''), CHAR(34), ''), CHAR(9), '') AS SubFamilia,

    D.Cantidad,
    D.Precio,
    (A.PrecioLista * D.Cantidad) AS PBxCantidad,
    D.DescuentoImporte,
    D.DescuentoLinea,

    --Descuento PP--
    CASE 
    WHEN LEFT(D.Articulo,3) = '040' THEN 0.00
    WHEN LEFT(D.Articulo,3) = '045' THEN 0.06
    WHEN LEFT(D.Articulo,3) = '204' THEN 0.06
    ELSE 0.00
END AS DescuentoPP,

    -- Subtotales
    ((D.Precio*D.Cantidad)*(1) - ((ISNULL(D.DescuentoLinea,0)/100)*(D.Precio*D.Cantidad)*(1)) - (D.Precio*D.Cantidad*(ISNULL(V.DescuentoGlobal,0)/100)*(1))) AS SubTotal,
    ((D.Precio*D.Cantidad)*(V.TipoCambio) - ((ISNULL(D.DescuentoLinea,0)/100)*((D.Precio*D.Cantidad)*(V.TipoCambio))) - (D.Precio*D.Cantidad*(ISNULL(V.DescuentoGlobal,0)/100)*(V.TipoCambio))) AS ImporteVenta,

    -- Costo por renglón
    CA.CostoPromedio,
    CA.ImporteCosto,
    A.MonedaCosto,

    D.Renglon,
    V.Condicion,
    A.PrecioLista AS PrecioBase,
    A.Precio5 AS Precio1,
    A.Precio2 AS Precio2,

    RTRIM(Aplica) + ' ' + RTRIM(AplicaID) AS Origen

FROM Venta V
JOIN VentaD D ON V.ID = D.ID
JOIN Art A ON D.Articulo = A.Articulo
LEFT JOIN Agente G ON V.Agente = G.Agente
LEFT JOIN Sucursal S ON G.SucursalEmpresa = S.Sucursal
LEFT JOIN Cte T ON V.Cliente = T.Cliente
LEFT JOIN ArtAlm M ON D.Articulo = M.Articulo AND V.Almacen = M.Almacen

OUTER APPLY (
    SELECT
        CASE 
            WHEN A.MonedaCosto = 'Pesos' THEN AC.CostoPromedio
            WHEN A.MonedaCosto = 'Dolares' AND V.Moneda = 'Pesos' THEN AC.CostoPromedio * TC.TipoCambio
            WHEN A.MonedaCosto = 'Dolares' AND V.Moneda = 'Dolares' THEN AC.CostoPromedio * V.TipoCambio
        END AS CostoPromedio,

        CASE 
            WHEN A.MonedaCosto = 'Pesos' THEN AC.CostoPromedio * D.Cantidad
            WHEN A.MonedaCosto = 'Dolares' AND V.Moneda = 'Pesos' THEN AC.CostoPromedio * TC.TipoCambio * D.Cantidad
            WHEN A.MonedaCosto = 'Dolares' AND V.Moneda = 'Dolares' THEN AC.CostoPromedio * V.TipoCambio * D.Cantidad
        END AS ImporteCosto
    FROM ArtCosto AC
    LEFT JOIN Mon TC ON TC.Moneda = A.MonedaCosto
    WHERE AC.Articulo = D.Articulo
      AND AC.Sucursal = D.Sucursal
) CA

WHERE V.Mov LIKE 'Fac%'
  AND V.Estatus = 'Concluido'
  AND A.Linea <> 'CONDUMEX/NYLON'
  AND (
    D.Articulo LIKE '%045-CTHW%'
    OR D.Articulo LIKE '%040-CTHW%'
    OR D.Articulo LIKE '%204-CTHW%'
      )
  AND V.Almacen NOT LIKE 'ENT PROV%'
  AND V.Almacen NOT LIKE 'REF%'
  AND V.FechaEmision >= '2026-06-01'
  AND V.FechaEmision < '2026-07-01';

    """


    df = pd.read_sql(
        consulta,
        engine
    )


    return df



if __name__ == "__main__":

    resultado = ejecutar_reporte()

    print(resultado)
