import pyodbc
import pandas as pd

def get_connection():
    server = "192.168.11.239"
    database = "Tamex2"
    username = "analista03"
    password = "Pr3c2o25$sq."

    conn = pyodbc.connect(
        f"DRIVER={{ODBC Driver 17 for SQL Server}};"
        f"SERVER={server};"
        f"DATABASE={database};"
        f"UID={username};"
        f"PWD={password};"
    )
    return conn

try:
    conn = get_connection()

    query = """
    ;WITH AlmacenMap AS (
    SELECT *
    FROM (VALUES
        (0, 'MATRIZ'),
        (2, 'OBSERV'),
        (4, 'PUEBLA'),
        (5, 'MERIDA-A'),
        (6, 'AGS'),
        (7, 'QUERETARO'),
        (9, 'COATZA'),
        (10, 'TAMPICO'),
        (11, 'CANCUN-A'),
        (13, 'MONTERREY'),
        (14, 'MARINA'),
        (15, 'GUADAL'),
        (16, 'CEDISVILLA'),
        (17, 'VERACRUZ'),
        (19, 'IZTAPALA-A'),
        (20, 'TOLUCA-A'),
        (21, 'LEON'),
        (22, 'SANLUIS'),
        (23, 'VALSEQ'),
        (27, 'CANCUN-A2'),
        (28, 'MERIDA-A2'),
        (29, 'ING-A'),
        (30, 'CULIACAN'),
        (31, 'CEDISMX'),
        (32, 'LOSCABOS'),
        (33, 'PACHUCA'),
        (34, 'TIJUANA IN'),
        (35, 'E-COMMERCE'),
        (36, 'MONTERREYB'),
        (37, 'PUEBLA2'),
        (39, 'CUERNAVACA'),
        (40, 'HERMOSILLO'),
        (41, 'CHIHUAHUA'),
        (42, 'LOSCABOSA2'),
        (43, 'SOLAR'),
        (44, 'ACAPULCO'),
        (45, 'PVALLARTA')
    ) X(Sucursal, Almacen)
),

Base AS (

    SELECT 
        V.ID,
        V.MovID,
        V.Mov,
        V.FechaEmision AS FechaPedido,
        V.Estatus,
        V.Usuario AS UsuarioV,
        DP.Usuario AS UsuarioP,
        DP.Motivo,

        V.Almacen,
        V.SucursalVenta AS SucVenta,
        AMSuc.Almacen AS NomSucVenta,

        CASE
            WHEN V.SucursalVenta IN (0,13,15,41,36,45) THEN 'Mauricio Tabachnik'
            WHEN V.SucursalVenta IN (4,6,7,21,22,23) THEN 'Benjamín Cuevas'
            WHEN V.SucursalVenta IN (44,39,19,14,2,33,20) THEN 'José Montoya'
            WHEN V.SucursalVenta IN (10,17,9,5,28,11,27,16) THEN 'Dan Pérez'
            WHEN V.SucursalVenta IN (30,32,34,40,42) THEN 'Juan Antonio Angulo'
            WHEN V.SucursalVenta = 35 THEN 'Ecommerce'
            WHEN V.SucursalVenta = 43 THEN 'Alfredo Menendez'
            ELSE 'SIN ASIGNAR'
        END AS GerenteRegional,

        V.Agente,
        AG.Nombre AS NomAgente,

        V.Cliente,
        Cte.Nombre AS NombreCliente,

        V.Moneda AS MonedaVenta,
        MON.TipoCambio,
        V.DescuentoGlobal,
        V.ComisionTamex,

        LTRIM(RTRIM(VD.Articulo)) AS Articulo,
        A.Descripcion1 AS Descripcion,

        VD.Cantidad,
        VD.Unidad AS UnidadVenta,
        VD.Precio,
        VD.DescuentoLinea,

        ROUND(
            VD.Precio - (VD.Precio * VD.DescuentoLinea / 100.0)
        ,2) AS PrecioVentaFinal,

        ROUND(
            (
                VD.Precio - (VD.Precio * VD.DescuentoLinea / 100.0)
            ) * V.TipoCambio * VD.Cantidad
        ,2) AS ImportexPartidaMXN,

        ROUND(A.PrecioLista,2) AS PrecioBase,
        ROUND(A.Precio2,2) AS Precio2,
        ROUND(A.PrecioMinimo,2) AS PrecioMinimo,

        ROUND(AC.CostoPromedio,2) AS CostoPromedioBase,

        A.MonedaCosto,

        CASE 
            WHEN A.MonedaCosto = 'Pesos'
                THEN ROUND(AC.CostoPromedio,2)
            WHEN A.MonedaCosto = 'Dolares'
                 AND Mon.Moneda = 'Pesos'
                THEN ROUND(
                    AC.CostoPromedio * MON.TipoCambio
                ,2)
            WHEN A.MonedaCosto = 'Dolares'
                 AND Mon.Moneda = 'Dolares'
            THEN ROUND(
                    AC.CostoPromedio * MON.TipoCambio
                ,2)
            END AS CostoPromedio,

        CASE 
            WHEN A.MonedaCosto = 'Pesos'
                THEN ROUND(
                    VD.Cantidad * AC.CostoPromedio
                ,2)

            WHEN A.MonedaCosto = 'Dolares'
                 AND Mon.Moneda = 'Pesos'
                THEN ROUND(
                    VD.Cantidad * AC.CostoPromedio * MON.TipoCambio
                ,2)

            WHEN A.MonedaCosto = 'Dolares'
                 AND Mon.Moneda = 'Dolares'
                THEN ROUND(
                    VD.Cantidad * AC.CostoPromedio * Mon.TipoCambio
                ,2)
        END AS ImporteCosto,

        LEFT(A.Articulo,3) AS PrefijoArticulo,

        CASE LEFT(A.Articulo,3)
            WHEN '045' THEN 0.06
            WHEN '065' THEN 0.03
            WHEN '069' THEN 0.00
            WHEN '072' THEN 0.00
            WHEN '078' THEN 0.05
            WHEN '204' THEN 0.06
            WHEN '206' THEN 0.03
            WHEN '241' THEN 0.05    
            WHEN '242' THEN 0.06
            WHEN '243' THEN 0.00
            WHEN '304' THEN 0.00
            ELSE 0
        END AS DescuentoPP

    FROM Venta V

    INNER JOIN VentaD VD
        ON VD.ID = V.ID

    INNER JOIN Art A
        ON A.Articulo = VD.Articulo

    INNER JOIN DescPrecioMenorMinimo DP
        ON DP.ID = V.ID

    INNER JOIN Cte
        ON Cte.Cliente = V.Cliente

    INNER JOIN AlmacenMap AM
        ON AM.Almacen = LTRIM(RTRIM(V.Almacen))

    LEFT JOIN AlmacenMap AMSuc
        ON AMSuc.Sucursal = V.SucursalVenta

    INNER JOIN Agente AG
        ON AG.Agente = V.Agente

    INNER JOIN ArtCosto AC
        ON AC.Articulo = A.Articulo
       AND AC.Sucursal = AM.Sucursal

    LEFT JOIN Mon MON
        ON MON.Moneda = A.MonedaCosto


    WHERE V.Mov = 'Pedido Tamex'
      AND V.Estatus = 'CONCLUIDO'
      AND V.FechaEmision >= '2026-06-15'
      AND V.FechaEmision < '2026-06-16'
),

LineaCalculada AS (

    SELECT 

        *,

        ROUND(
            CostoPromedio * (1 - DescuentoPP)
        ,2) AS CostoConPP,

        ROUND(
            (Precio * Cantidad * TipoCambio)
            - ((ISNULL(DescuentoLinea,0) / 100.0)
            * (Precio * Cantidad * TipoCambio))
            - ((Precio * Cantidad * TipoCambio)
            * (ISNULL(DescuentoGlobal,0) / 100.0))
        ,2) AS Subtotal,

        ROUND(
            (CostoPromedio * (1 - DescuentoPP)) * Cantidad
        ,2) AS CostoLinea

    FROM Base
)

SELECT 

    ID,
    MovID,
    Mov,
    FechaPedido,
    Cliente,
    NombreCliente,
    Estatus,

    Almacen,
    Agente,
    NomAgente,
    NomSucVenta,
    GerenteRegional,

    Articulo,
    Descripcion,

    Cantidad,
    UnidadVenta,

    MonedaVenta,
    TipoCambio,

    Precio,
    DescuentoLinea,
    PrecioVentaFinal,
    ImportexPartidaMXN,

    CostoPromedio AS CostoPromAlm,
    MonedaCosto,
    ImporteCosto,

    DescuentoPP,
    CostoConPP,

    ROUND(
        ((PrecioMinimo - CostoPromedio)
        / NULLIF(PrecioMinimo,0)) * 100
    ,2) AS [Utilidad Costo Promedio],

    ROUND(  
        ((PrecioMinimo - CostoConPP)
        / NULLIF(PrecioMinimo,0)) * 100
    ,2) AS [M. Utilidad con PP],

    SUM(Subtotal) OVER(PARTITION BY ID) AS Subtotal,

    SUM(CostoLinea) OVER(PARTITION BY ID) AS ImpCostoTotalPedido,

    SUM(Subtotal - CostoLinea)
        OVER(PARTITION BY ID) AS UtilidadTotalPedido,

    ROUND(
        (
            SUM(Subtotal - CostoLinea)
                OVER(PARTITION BY ID)
            /
            NULLIF(
                SUM(Subtotal)
                    OVER(PARTITION BY ID)
            ,0)
        ) * 100
    ,2) AS MargenPedidoPct,

    UsuarioP,
    Motivo,

    ComisionTamex AS CT,

    CASE 
        WHEN ComisionTamex = 1 THEN 'REVENTA'
        WHEN ComisionTamex = 2 THEN 'SC'
        WHEN ComisionTamex = 3 THEN 'CC'
    END AS CTDetalle

FROM LineaCalculada

ORDER BY ID, Articulo;

    """

    df = pd.read_sql(query, conn)

    print(df.head())

    conn.close()

except Exception as e:
    print("❌ Error:", e)