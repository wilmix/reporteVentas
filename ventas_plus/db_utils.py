"""
Módulo para la conexión y consulta a la base de datos.
"""
import configparser
import mysql.connector
import pandas as pd

def get_db_config(config_file_path):
    config = configparser.ConfigParser()
    config.read(config_file_path)
    if 'mysql' not in config:
        raise ValueError("La sección 'mysql' no existe en el archivo de configuración")
    return {
        'host': config['mysql'].get('host', 'localhost'),
        'user': config['mysql'].get('user', 'root'),
        'password': config['mysql'].get('password', ''),
        'database': config['mysql'].get('database', ''),
        'port': config['mysql'].getint('port', 3306)
    }

def connect_to_db(db_params):
    try:
        return mysql.connector.connect(**db_params)
    except mysql.connector.Error as err:
        print(f"Error de conexión a la base de datos: {err}")
        return None

def get_inventory_system_invoices(db_params, year, month):
    try:
        conn = connect_to_db(db_params)
        if conn is None:
            return None
        query = """
            SELECT
                DATE_FORMAT(f.fechaFac, '%d/%m/%Y') fechaFac,
                nFactura,
                fs.cuf autorizacion,
                fs.codigoSucursal,
                f.ClienteNit nit,
                '' complemento,
                f.ClienteFactura razonSocial,
                f.total importeTotal,
                0 ICE,
                0 IEHD,
                0 IPJ,
                0 tasas,
                0 otrosNoSujetos,
                0 excentos,
                0 ventasTasaCero,
                f.total subTotal,
                0 descuentos,
                0 gift, 
                f.total base,
                ROUND ((f.total * 0.13), 3) AS debito,
                IF(anulada = 0, 'V', 'A') estado,
                IF(codigoControl = '', 0, codigoControl) AS codigoControl,
                0 tipoVenta,
                a.almacen _alm,
                '' _revision,
                IF(df.manual = 1, 'SIAT-DESKTOP-FE', 'ONLINE') _tipoFac,
                f.glosa _obs,
                concat(u.first_name, ' ' , u.last_name) _autor 
            FROM
                factura f
                INNER JOIN datosfactura df ON df.idDatosFactura = f.lote
                INNER JOIN factura_siat fs ON fs.factura_id = f.idFactura
                INNER JOIN almacenes a ON a.idalmacen = f.almacen
                INNER JOIN tipoPago tp ON tp.id = f.tipoPago
                INNER JOIN users u on u.id = f.autor
            WHERE
                year(f.fechaFac) = %s
                AND month(f.fechaFac) = %s
            ORDER BY
                a.idalmacen,
                f.fechaFac,
                df.idDatosFactura DESC,
                nFactura
        """
        print(f"Consultando facturas del sistema de inventarios para {month}/{year}...")
        df = pd.read_sql(query, conn, params=(year, month))
        conn.close()
        print(f"Se encontraron {len(df)} facturas en el sistema de inventarios")
        return df
    except Exception as e:
        print(f"Error al consultar facturas del sistema de inventarios: {e}")
        return None
