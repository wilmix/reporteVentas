"""
Funciones básicas para el procesamiento de datos de ventas.
"""

import os
import pandas as pd
import numpy as np
from datetime import datetime
import zipfile
import tempfile
import configparser
import mysql.connector
import warnings
import contextlib

@contextlib.contextmanager
def suppress_openpyxl_warnings():
    """Suprimir advertencias de openpyxl durante la ejecución."""
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
        yield

def process_zipped_sales_excel(zip_file_path, sheet_name="hoja1"):
    """
    Procesar un archivo Excel comprimido con datos de ventas.
    
    Args:
        zip_file_path (str): Ruta al archivo ZIP que contiene el Excel
        sheet_name (str): Nombre de la hoja a procesar
        
    Returns:
        DataFrame: Datos procesados del archivo Excel, o None si ocurre un error
    """
    try:
        # Crear directorio temporal para extraer los archivos
        with tempfile.TemporaryDirectory() as temp_dir:
            # Extraer archivos del ZIP
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            
            # Buscar archivos Excel en el directorio temporal
            excel_files = [f for f in os.listdir(temp_dir) if f.endswith('.xlsx')]
            
            if not excel_files:
                print(f"No se encontraron archivos Excel en {zip_file_path}")
                return None
            
            # Tomar el primer archivo Excel encontrado
            excel_path = os.path.join(temp_dir, excel_files[0])
            
            # Leer el archivo Excel con pandas
            with suppress_openpyxl_warnings():
                return pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as e:
        print(f"Error al procesar el archivo ZIP: {e}")
        return None

def get_db_config(config_file_path):
    """
    Obtener configuración de la base de datos desde un archivo INI.
    
    Args:
        config_file_path (str): Ruta al archivo de configuración
        
    Returns:
        dict: Parámetros de conexión a la base de datos
    """
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
    """
    Conectar a la base de datos MySQL.
    
    Args:
        db_params (dict): Parámetros de conexión
        
    Returns:
        MySQLConnection: Conexión a la base de datos, o None si falla
    """
    try:
        return mysql.connector.connect(**db_params)
    except mysql.connector.Error as err:
        print(f"Error de conexión a la base de datos: {err}")
        return None

def process_sales_data(sales_data):
    """
    Procesar y limpiar los datos de ventas.
    
    Args:
        sales_data (DataFrame): Datos crudos de ventas
        
    Returns:
        DataFrame: Datos procesados
    """
    # Hacer una copia para no alterar el original
    df = sales_data.copy()
    
    # Convertir valores numéricos
    numeric_columns = ['IMPORTE TOTAL DE LA VENTA'] if 'IMPORTE TOTAL DE LA VENTA' in df.columns else []
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    
    # Eliminar filas completamente vacías
    df = df.dropna(how='all')
    
    # Crear nuevas columnas para información extraída del CODIGO DE AUTORIZACIÓN
    if 'CODIGO DE AUTORIZACIÓN' in df.columns:
        # Inicializar nuevas columnas
        df['SUCURSAL'] = ''
        df['MODALIDAD'] = ''  
        df['TIPO EMISION'] = ''
        df['TIPO FACTURA'] = ''
        df['SECTOR'] = ''
        df['NUM FACTURA'] = ''
        df['PV'] = ''  # Punto de Venta
        df['CODIGO AUTOVERIFICADOR'] = ''
        
        # Iterar sobre cada fila para extraer información del código de autorización
        for index, row in df.iterrows():
            try:
                # Obtener el valor de la columna 'CODIGO DE AUTORIZACIÓN'
                codigo = row['CODIGO DE AUTORIZACIÓN']
                
                if isinstance(codigo, str) and len(codigo) >= 42:
                    # Obtener los valores deseados
                    hexadecimal = codigo[:42]
                    decimal = int(hexadecimal, 16)
                    cadena = str(decimal)
                    
                    # Verificar si la cadena tiene suficientes dígitos
                    if len(cadena) > 27:
                        # Extraer los segmentos de la cadena
                        cadena = cadena[27:]
                        
                        # Verificar suficiente longitud antes de extraer
                        if len(cadena) >= 24:  # Necesitamos al menos 24 caracteres
                            sucursal = cadena[:4]
                            modalidad = cadena[4:5] if len(cadena) > 4 else ''
                            tipo_emision = cadena[5:6] if len(cadena) > 5 else ''
                            tipo_factura = cadena[6:7] if len(cadena) > 6 else ''
                            tipo_documento_sector = cadena[7:9] if len(cadena) > 8 else ''
                            num_factura = cadena[9:19] if len(cadena) > 18 else ''
                            pv = cadena[19:23] if len(cadena) > 22 else ''
                            codigo_autoverificador = cadena[23:24] if len(cadena) > 23 else ''
                            
                            # Asignar los valores a las nuevas columnas
                            df.at[index, 'SUCURSAL'] = sucursal
                            df.at[index, 'MODALIDAD'] = modalidad
                            df.at[index, 'TIPO EMISION'] = tipo_emision
                            df.at[index, 'TIPO FACTURA'] = tipo_factura
                            df.at[index, 'SECTOR'] = tipo_documento_sector
                            df.at[index, 'NUM FACTURA'] = num_factura
                            df.at[index, 'PV'] = pv
                            df.at[index, 'CODIGO AUTOVERIFICADOR'] = codigo_autoverificador
            except Exception as e:
                print(f"Error al procesar el código de autorización en la fila {index}: {str(e)}")
                continue
    
    return df

def analyze_sales_data_basic(df):
    """
    Realizar un análisis básico de los datos de ventas.
    
    Args:
        df (DataFrame): Datos procesados de ventas
        
    Returns:
        dict: Estadísticas básicas de los datos
    """
    results = {
        "total_records": len(df),
        "columns": list(df.columns),
    }
    
    # Si existen las columnas necesarias, agregar estadísticas
    if 'IMPORTE TOTAL DE LA VENTA' in df.columns:
        results['total_ventas'] = df['IMPORTE TOTAL DE LA VENTA'].sum()
        results['promedio_venta'] = df['IMPORTE TOTAL DE LA VENTA'].mean()
        results['venta_maxima'] = df['IMPORTE TOTAL DE LA VENTA'].max()
    
    if 'ESTADO' in df.columns:
        results['conteo_estados'] = df['ESTADO'].value_counts().to_dict()
    
    # Añadir análisis de las nuevas columnas extraídas del código de autorización
    if 'SUCURSAL' in df.columns:
        results['conteo_sucursales'] = df['SUCURSAL'].value_counts().to_dict()
    
    if 'TIPO EMISION' in df.columns:
        results['conteo_tipo_emision'] = df['TIPO EMISION'].value_counts().to_dict()
        
    if 'SECTOR' in df.columns:
        results['conteo_sector'] = df['SECTOR'].value_counts().to_dict()
    
    return results

def analyze_sales_data_detailed(df):
    """
    Realizar un análisis detallado de datos de ventas por sucursal y sector.
    
    Args:
        df (DataFrame): Datos procesados de ventas
        
    Returns:
        dict: Estadísticas detalladas de los datos por sucursal y sector
    """
    results = {}
    
    # Verificar que existen las columnas necesarias
    required_columns = ['ESTADO', 'SECTOR', 'SUCURSAL', 'IMPORTE TOTAL DE LA VENTA']
    for col in required_columns:
        if col not in df.columns:
            print(f"Advertencia: No se encontró la columna {col}, análisis detallado limitado")
            return {"error": f"Falta la columna {col} para el análisis detallado"}
    
    # ANÁLISIS DE ALQUILERES (SECTOR 02)
    df_alq = df[df["SECTOR"] == '02']
    df_alq_valida = df[(df["SECTOR"] == '02') & (df['ESTADO'] == 'VALIDA')]
    df_alq_anulada = df[(df["SECTOR"] == '02') & (df['ESTADO'] == 'ANULADA')]
    
    # Total facturado en alquileres
    total_facturado_alquiler = df_alq_valida["IMPORTE TOTAL DE LA VENTA"].sum()
    results['alquileres'] = {
        'total_facturado': total_facturado_alquiler,
        'cantidad_validas': len(df_alq_valida),
        'cantidad_anuladas': len(df_alq_anulada),
        'cantidad_total': len(df_alq)
    }
    
    # ANÁLISIS GENERAL
    # Facturas válidas y total facturado
    df_validas = df[df["ESTADO"] == "VALIDA"]
    total_venta_valida = df_validas["IMPORTE TOTAL DE LA VENTA"].sum()
    
    results['general'] = {
        'total_facturado_valida': total_venta_valida,
        'total_facturado_sin_alquiler': total_venta_valida - total_facturado_alquiler,
        'total_facturas': len(df),
        'cantidad_validas': len(df_validas),
        'cantidad_anuladas': len(df[df["ESTADO"] == "ANULADA"])
    }
    
    # ANÁLISIS POR SUCURSAL Y SECTOR
    
    # CENTRAL - LA PAZ (0000)
    # Facturas de venta común (01) y bienes capitales (35)
    df_central_validas = df[(df['ESTADO'] == 'VALIDA') & 
                           (df['SUCURSAL'] == '0000') & 
                           ((df['SECTOR'] == '01') | (df['SECTOR'] == '35'))]
    
    df_central_validas_cv = df[(df['ESTADO'] == 'VALIDA') & 
                              (df['SUCURSAL'] == '0000') & 
                              (df['SECTOR'] == '01')]
                              
    df_central_validas_cvb = df[(df['ESTADO'] == 'VALIDA') & 
                               (df['SUCURSAL'] == '0000') & 
                               (df['SECTOR'] == '35')]
                               
    df_central_anuladas = df[(df['ESTADO'] == 'ANULADA') & 
                            (df['SUCURSAL'] == '0000') & 
                            ((df['SECTOR'] == '01') | (df['SECTOR'] == '35'))]
    
    total_central_validas = df_central_validas['IMPORTE TOTAL DE LA VENTA'].sum()
    
    results['central'] = {
        'total_facturado': total_central_validas,
        'cantidad_validas_cv': len(df_central_validas_cv),
        'cantidad_validas_cvb': len(df_central_validas_cvb),
        'cantidad_anuladas': len(df_central_anuladas),
        'cantidad_total': len(df_central_validas) + len(df_central_anuladas)
    }
    
    # POTOSÍ (0006)
    df_potosi_validas = df[(df['ESTADO'] == 'VALIDA') & 
                           (df['SUCURSAL'] == '0006') & 
                           (df['SECTOR'] == '01')]
                           
    df_potosi_anuladas = df[(df['ESTADO'] == 'ANULADA') & 
                            (df['SUCURSAL'] == '0006') & 
                            (df['SECTOR'] == '01')]
                            
    total_potosi_validas = df_potosi_validas['IMPORTE TOTAL DE LA VENTA'].sum()
    
    results['potosi'] = {
        'total_facturado': total_potosi_validas,
        'cantidad_validas': len(df_potosi_validas),
        'cantidad_anuladas': len(df_potosi_anuladas),
        'cantidad_total': len(df_potosi_validas) + len(df_potosi_anuladas)
    }
    
    # SANTA CRUZ (0005)
    df_scz_validas = df[(df['ESTADO'] == 'VALIDA') & 
                        (df['SUCURSAL'] == '0005') & 
                        (df['SECTOR'] == '01')]
                        
    df_scz_anulada = df[(df['ESTADO'] == 'ANULADA') & 
                         (df['SUCURSAL'] == '0005') & 
                         (df['SECTOR'] == '01')]
                         
    total_scz_validas = df_scz_validas['IMPORTE TOTAL DE LA VENTA'].sum()
    
    results['santa_cruz'] = {
        'total_facturado': total_scz_validas,
        'cantidad_validas': len(df_scz_validas),
        'cantidad_anuladas': len(df_scz_anulada),
        'cantidad_total': len(df_scz_validas) + len(df_scz_anulada)
    }
    
    # RESUMEN TOTAL DE FACTURAS
    total_cantidad_facturas = (
        results['central']['cantidad_validas_cv'] + 
        results['central']['cantidad_validas_cvb'] + 
        results['central']['cantidad_anuladas'] + 
        results['potosi']['cantidad_validas'] + 
        results['potosi']['cantidad_anuladas'] + 
        results['santa_cruz']['cantidad_validas'] + 
        results['santa_cruz']['cantidad_anuladas'] + 
        results['alquileres']['cantidad_total']
    )
    
    results['total_facturas_desglosado'] = total_cantidad_facturas
    
    return results

def get_inventory_system_invoices(db_params, year, month):
    """
    Obtener facturas del sistema de inventarios para compararlas con las del SIAT.
    
    Args:
        db_params (dict): Parámetros de conexión a la base de datos
        year (int): Año a consultar
        month (int): Mes a consultar
        
    Returns:
        DataFrame: Dataframe con los datos de facturas del sistema, o None si ocurre un error
    """
    try:
        # Conectar a la base de datos
        conn = connect_to_db(db_params)
        if conn is None:
            return None
            
        # Definir la consulta SQL
        query = """
            SELECT
                DATE_FORMAT(f.fechaFac, '%d/%m/%Y') fechaFac,
                nFactura,
                fs.cuf autorizacion,
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
                a.almacen codigoSucursal,
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
        
        # Ejecutar la consulta y obtener los resultados en un DataFrame
        print(f"Consultando facturas del sistema de inventarios para {month}/{year}...")
        df = pd.read_sql(query, conn, params=(year, month))
        
        # Cerrar la conexión
        conn.close()
        
        print(f"Se encontraron {len(df)} facturas en el sistema de inventarios")
        return df
        
    except Exception as e:
        print(f"Error al consultar facturas del sistema de inventarios: {e}")
        return None

def compare_siat_with_inventory(siat_data, inventory_data):
    """
    Comparar facturas del SIAT con las del sistema de inventarios.
    
    Args:
        siat_data (DataFrame): Datos de facturas del SIAT
        inventory_data (DataFrame): Datos de facturas del sistema de inventarios
        
    Returns:
        dict: Resultados de la comparación
    """
    results = {
        'total_siat': len(siat_data),
        'total_inventory': len(inventory_data),
        'matching_invoices': 0,
        'missing_in_inventory': [],
        'missing_in_siat': [],
        'amount_difference': 0.0,
        'amount_difference_details': []
    }
    
    # Excluir facturas de alquileres del SIAT (SECTOR 02)
    siat_no_alquileres = siat_data[siat_data['SECTOR'] != '02']
    results['total_siat_no_alquileres'] = len(siat_no_alquileres)
    
    # Crear Series con autorizaciones para comparación rápida
    siat_auths = set(siat_no_alquileres['CODIGO DE AUTORIZACIÓN'].str.strip())
    inventory_auths = set(inventory_data['autorizacion'].str.strip())
    
    # Encontrar facturas que coinciden
    matching_auths = siat_auths.intersection(inventory_auths)
    results['matching_invoices'] = len(matching_auths)
    
    # Encontrar facturas que están en SIAT pero no en inventario
    missing_in_inventory = siat_auths - inventory_auths
    results['missing_in_inventory_count'] = len(missing_in_inventory)
    
    if len(missing_in_inventory) > 0:
        missing_df = siat_no_alquileres[siat_no_alquileres['CODIGO DE AUTORIZACIÓN'].isin(missing_in_inventory)]
        results['missing_in_inventory'] = missing_df[['CODIGO DE AUTORIZACIÓN', 'IMPORTE TOTAL DE LA VENTA', 'ESTADO']].to_dict('records')
    
    # Encontrar facturas que están en inventario pero no en SIAT
    missing_in_siat = inventory_auths - siat_auths
    results['missing_in_siat_count'] = len(missing_in_siat)
    
    if len(missing_in_siat) > 0:
        missing_df = inventory_data[inventory_data['autorizacion'].isin(missing_in_siat)]
        results['missing_in_siat'] = missing_df[['autorizacion', 'importeTotal', 'estado']].to_dict('records')
    
    # Verificar diferencias en montos para facturas que coinciden
    if len(matching_auths) > 0:
        # Preparar DataFrames para comparación
        siat_matching = siat_no_alquileres[siat_no_alquileres['CODIGO DE AUTORIZACIÓN'].isin(matching_auths)]
        inventory_matching = inventory_data[inventory_data['autorizacion'].isin(matching_auths)]
        
        # Crear DataFrames con solo las columnas necesarias
        siat_compare = siat_matching[['CODIGO DE AUTORIZACIÓN', 'IMPORTE TOTAL DE LA VENTA']].copy()
        inventory_compare = inventory_matching[['autorizacion', 'importeTotal']].copy()
        
        # Renombrar columnas para facilitar la comparación
        siat_compare.rename(columns={'CODIGO DE AUTORIZACIÓN': 'autorizacion', 'IMPORTE TOTAL DE LA VENTA': 'importe_siat'}, inplace=True)
        inventory_compare.rename(columns={'importeTotal': 'importe_inventory'}, inplace=True)
        
        # Combinar DataFrames para comparación
        comparison = pd.merge(siat_compare, inventory_compare, on='autorizacion')
        
        # Calcular diferencias
        comparison['diferencia'] = comparison['importe_siat'] - comparison['importe_inventory']
        
        # Filtrar solo los que tienen diferencias significativas (más de 0.01)
        differences = comparison[abs(comparison['diferencia']) > 0.01]
        
        if len(differences) > 0:
            results['amount_differences_count'] = len(differences)
            results['amount_difference'] = differences['diferencia'].sum()
            results['amount_difference_details'] = differences.to_dict('records')
    
    return results

def verify_invoice_consistency(project_root, config_file_path, month, year, export_results=True):
    """
    Verificar consistencia entre facturas del SIAT y del sistema de inventarios.
    
    Args:
        project_root (str): Directorio raíz del proyecto
        config_file_path (str): Ruta al archivo de configuración de la BD
        month (int): Mes a procesar
        year (int): Año a procesar
        export_results (bool): Si es True, exporta los resultados a un archivo CSV
        
    Returns:
        dict: Resultados de la verificación
    """
    print("\n--- Verificando consistencia de facturas ---")
    
    # Formatear mes con cero a la izquierda
    formatted_month = f"{int(month):02d}"
    
    # Obtener datos del SIAT
    zip_file_name = f"{formatted_month}VentasXlsx.zip"
    zip_file_path = os.path.join(project_root, "data", str(year), zip_file_name)
    
    if not os.path.exists(zip_file_path):
        print(f"\nError: No se encontró el archivo {zip_file_name} del SIAT")
        return None
        
    print(f"Procesando archivo del SIAT: {zip_file_path}")
    siat_data = process_zipped_sales_excel(zip_file_path, sheet_name="hoja1")
    
    if siat_data is None or siat_data.empty:
        print("No se encontraron datos del SIAT o hubo un error al procesar el archivo")
        return None
        
    # Procesar datos del SIAT
    siat_processed = process_sales_data(siat_data)
    
    # Obtener configuración de la base de datos y conectar
    try:
        db_params = get_db_config(config_file_path)
    except Exception as e:
        print(f"Error al obtener la configuración de la base de datos: {e}")
        return None
    
    # Consultar datos del sistema de inventarios
    inventory_data = get_inventory_system_invoices(db_params, year, int(month))
    
    if inventory_data is None or inventory_data.empty:
        print("No se encontraron datos en el sistema de inventarios o hubo un error en la consulta")
        return None
        
    # Comparar los datos
    print("\nComparando datos del SIAT con el sistema de inventarios...")
    # Importar la función correcta de comparison.py
    from .comparison import compare_siat_with_inventory as compare_full
    comparison_results = compare_full(siat_processed, inventory_data)
    
    # Mostrar resultados
    print("\n=== RESULTADOS DE LA VERIFICACIÓN ===")
    print(f"Facturas en SIAT: {comparison_results['total_siat']}")
    print(f"Facturas en SIAT (excluyendo alquileres): {comparison_results['total_siat_no_alquileres']}")
    print(f"Facturas en sistema de inventarios: {comparison_results['total_inventory']}")
    print(f"Facturas coincidentes: {comparison_results['matching_invoices']}")
    
    if comparison_results['missing_in_inventory_count'] > 0:
        print(f"\nFacturas en SIAT pero no en inventarios: {comparison_results['missing_in_inventory_count']}")
        
    if comparison_results['missing_in_siat_count'] > 0:
        print(f"\nFacturas en inventarios pero no en SIAT: {comparison_results['missing_in_siat_count']}")
        
    if 'amount_differences_count' in comparison_results and comparison_results['amount_differences_count'] > 0:
        print(f"\nFacturas con diferencias de montos: {comparison_results['amount_differences_count']}")
        print(f"Diferencia total: {comparison_results['amount_difference']:,.2f}")
    
    # Exportar resultados si se solicita
    if export_results:
        output_dir = os.path.join(project_root, "data", "output")
        os.makedirs(output_dir, exist_ok=True)

        # Exportar archivo completo de verificación
        if 'verificacion_completa' in comparison_results:
            verif_df = comparison_results['verificacion_completa']
            if isinstance(verif_df, pd.DataFrame) and not verif_df.empty:
                verif_path = os.path.join(output_dir, f"verificacion_completa_{formatted_month}_{year}.csv")
                verif_df.to_csv(verif_path, index=False)
                print(f"\nArchivo de verificación completa guardado en: {verif_path}")

        # Crear un DataFrame con las diferencias
        if comparison_results['missing_in_inventory']:
            missing_inv_df = pd.DataFrame(comparison_results['missing_in_inventory'])
            missing_inv_path = os.path.join(output_dir, f"missing_in_inventory_{formatted_month}_{year}.csv")
            missing_inv_df.to_csv(missing_inv_path, index=False)
            print(f"\nFacturas faltantes en inventarios guardadas en: {missing_inv_path}")

        if comparison_results['missing_in_siat']:
            missing_siat_df = pd.DataFrame(comparison_results['missing_in_siat'])
            missing_siat_path = os.path.join(output_dir, f"missing_in_siat_{formatted_month}_{year}.csv")
            missing_siat_df.to_csv(missing_siat_path, index=False)
            print(f"Facturas faltantes en SIAT guardadas en: {missing_siat_path}")

        if 'amount_difference_details' in comparison_results and comparison_results['amount_difference_details']:
            diff_df = pd.DataFrame(comparison_results['amount_difference_details'])
            diff_path = os.path.join(output_dir, f"amount_differences_{formatted_month}_{year}.csv")
            diff_df.to_csv(diff_path, index=False)
            print(f"Diferencias de montos guardadas en: {diff_path}")

    return comparison_results
