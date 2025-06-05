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
from ventas_plus.comparison import compare_siat_with_inventory

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

# def compare_siat_with_inventory(siat_data, inventory_data):
#     """
#     Comparar facturas del SIAT con las del sistema de inventarios.
    
#     Args:
#         siat_data (DataFrame): Datos de facturas del SIAT
#         inventory_data (DataFrame): Datos de facturas del sistema de inventarios
        
#     Returns:
#         dict: Resultados de la comparación y DataFrame con detalles
#     """
#     results = {
#         'total_siat': len(siat_data),
#         'total_inventory': len(inventory_data),
#         'matching_invoices': 0,
#         'missing_in_inventory': [],
#         'missing_in_siat': [],
#         'amount_difference': 0.0,
#         'amount_difference_details': [],
#         'field_discrepancies': []
#     }
    
#     # Excluir facturas de alquileres del SIAT (SECTOR 02)
#     siat_no_alquileres = siat_data[siat_data['SECTOR'] != '02']
#     results['total_siat_no_alquileres'] = len(siat_no_alquileres)
    
#     # Crear Series con autorizaciones para comparación rápida
#     siat_auths = set(siat_no_alquileres['CODIGO DE AUTORIZACIÓN'].str.strip())
#     inventory_auths = set(inventory_data['autorizacion'].str.strip())
    
#     # Encontrar facturas que coinciden
#     matching_auths = siat_auths.intersection(inventory_auths)
#     results['matching_invoices'] = len(matching_auths)
    
#     # Encontrar facturas que están en SIAT pero no en inventario
#     missing_in_inventory = siat_auths - inventory_auths
#     results['missing_in_inventory_count'] = len(missing_in_inventory)
    
#     if len(missing_in_inventory) > 0:
#         missing_df = siat_no_alquileres[siat_no_alquileres['CODIGO DE AUTORIZACIÓN'].isin(missing_in_inventory)]
#         results['missing_in_inventory'] = missing_df[['CODIGO DE AUTORIZACIÓN', 'IMPORTE TOTAL DE LA VENTA', 'ESTADO']].to_dict('records')
    
#     # Encontrar facturas que están en inventario pero no en SIAT
#     missing_in_siat = inventory_auths - siat_auths
#     results['missing_in_siat_count'] = len(missing_in_siat)
    
#     if len(missing_in_siat) > 0:
#         missing_df = inventory_data[inventory_data['autorizacion'].isin(missing_in_siat)]
#         results['missing_in_siat'] = missing_df[['autorizacion', 'importeTotal', 'estado']].to_dict('records')
    
#     # Verificar diferencias en campos específicos para facturas que coinciden
#     if len(matching_auths) > 0:
#         # Preparar DataFrames para comparación
#         siat_matching = siat_no_alquileres[siat_no_alquileres['CODIGO DE AUTORIZACIÓN'].isin(matching_auths)]
#         inventory_matching = inventory_data[inventory_data['autorizacion'].isin(matching_auths)]
          # Crear DataFrames con columnas a comparar
        # SIAT columns
#         siat_compare = siat_matching[[
#             'CODIGO DE AUTORIZACIÓN',
#             'FECHA DE LA FACTURA',
#             'Nº DE LA FACTURA',
#             'NIT / CI CLIENTE',
#             'NOMBRE O RAZON SOCIAL',
#             'IMPORTE TOTAL DE LA VENTA',
#             'ESTADO',
#             'SUCURSAL'
#         ]].copy()
        
        # Inventory columns
#         inventory_compare = inventory_matching[[
#             'autorizacion',
#             'fechaFac',
#             'nFactura',
#             'nit',
#             'razonSocial',
#             'importeTotal',
#             'estado',
#             'codigoSucursal'
#         ]].copy()
        
        # Renombrar columnas para facilitar la comparación
#         siat_compare.rename(columns={
#             'CODIGO DE AUTORIZACIÓN': 'autorizacion',
#             'FECHA DE LA FACTURA': 'fecha_siat',
#             'Nº DE LA FACTURA': 'nfactura_siat',
#             'NIT / CI CLIENTE': 'nit_siat',
#             'NOMBRE O RAZON SOCIAL': 'razon_social_siat',
#             'IMPORTE TOTAL DE LA VENTA': 'importe_siat',
#             'ESTADO': 'estado_siat',
#             'SUCURSAL': 'sucursal_siat'
#         }, inplace=True)
        
#         inventory_compare.rename(columns={
#             'fechaFac': 'fecha_inv',
#             'nFactura': 'nfactura_inv',
#             'nit': 'nit_inv',
#             'razonSocial': 'razon_social_inv',
#             'importeTotal': 'importe_inv',
#             'estado': 'estado_inv',
#             'codigoSucursal': 'sucursal_inv'
#         }, inplace=True)
        
        # Combinar DataFrames para comparación
#         comparison = pd.merge(siat_compare, inventory_compare, on='autorizacion')
        
        # Agregar columna de observaciones
#         comparison['OBSERVACIONES'] = ''
          # Convertir las columnas numéricas
#         comparison['nfactura_siat'] = pd.to_numeric(comparison['nfactura_siat'], errors='coerce')
#         comparison['nfactura_inv'] = pd.to_numeric(comparison['nfactura_inv'], errors='coerce')
#         comparison['nit_siat'] = comparison['nit_siat'].astype(str).str.strip()
#         comparison['nit_inv'] = comparison['nit_inv'].astype(str).str.strip()
        
        # Función para normalizar códigos de sucursal (aplicable antes del procesamiento individual)
#         def normalize_branch_code(code):
#             if code is None or pd.isna(code):
#                 return ''
#             # Convertir a string, quitar espacios, quitar ceros a la izquierda
#             normalized = str(code).strip().lstrip('0')
#             # Si quedó vacío después de quitar los ceros, era un "0" o "00", etc.
#             if normalized == '':
#                 return '0'
#             return normalized
        
        # Normalizar códigos de sucursal antes de las comparaciones
#         comparison['sucursal_siat_norm'] = comparison['sucursal_siat'].apply(normalize_branch_code)
#         comparison['sucursal_inv_norm'] = comparison['sucursal_inv'].apply(normalize_branch_code)
        
        # Convertir estados de inventario a formato SIAT (V->VALIDA, A->ANULADA)
#         comparison['estado_inv'] = comparison['estado_inv'].replace({'V': 'VALIDA', 'A': 'ANULADA'})
        
        # Verificar discrepancias en cada campo
#         for i, row in comparison.iterrows():
#             observaciones = []
            
#             # 1. Verificar fecha
#             if row['fecha_siat'] != row['fecha_inv']:
#                 observaciones.append(f"Fecha: SIAT={row['fecha_siat']}, INV={row['fecha_inv']}")
                
#             # 2. Verificar número de factura
#             if row['nfactura_siat'] != row['nfactura_inv']:
#                 observaciones.append(f"Nº Factura: SIAT={row['nfactura_siat']}, INV={row['nfactura_inv']}")
                
#             # 3. Verificar NIT
#             if row['nit_siat'] != row['nit_inv']:
#                 observaciones.append(f"NIT: SIAT={row['nit_siat']}, INV={row['nit_inv']}")
                
#             # 5. Verificar importe (con tolerancia de 0.01)
#             if abs(row['importe_siat'] - row['importe_inv']) > 0.01:
#                 observaciones.append(f"Importe: SIAT={row['importe_siat']}, INV={row['importe_inv']}")
                
#             # 6. Verificar estado
#             if row['estado_siat'] != row['estado_inv']:
#                 observaciones.append(f"Estado: SIAT={row['estado_siat']}, INV={row['estado_inv']}")            # 7. Verificar sucursal usando los valores normalizados previamente calculados
#             # Solo agregar observación si hay diferencia en el valor efectivo, no solo en formato
#             if row['sucursal_siat_norm'] != row['sucursal_inv_norm']:
#                 observaciones.append(f"Sucursal: SIAT={row['sucursal_siat']}, INV={row['sucursal_inv']}")
#                 # Para debug (opcional): podemos agregar los valores normalizados para verificación
#                 # observaciones.append(f"Sucursal normalizada: SIAT={row['sucursal_siat_norm']}, INV={row['sucursal_inv_norm']}")
                
#             # Guardar observaciones
#             if observaciones:
#                 comparison.at[i, 'OBSERVACIONES'] = "; ".join(observaciones)
#                 results['field_discrepancies'].append({
#                     'autorizacion': row['autorizacion'],
#                     'observaciones': "; ".join(observaciones)
#                 })
        
#         # Calcular diferencias en montos (igual que antes)
#         comparison['diferencia_importe'] = comparison['importe_siat'] - comparison['importe_inv']
        
#         # Filtrar solo los que tienen diferencias significativas en montos (más de 0.01)
#         differences = comparison[abs(comparison['diferencia_importe']) > 0.01]
        
#         if len(differences) > 0:
#             results['amount_differences_count'] = len(differences)
#             results['amount_difference'] = differences['diferencia_importe'].sum()
#             results['amount_difference_details'] = differences.to_dict('records')
        
#         # Guardar el DataFrame completo para retornarlo
#         results['comparison_dataframe'] = comparison
    
#     return results

def verify_invoice_consistency(project_root, config_file_path, month, year, export_results=True, print_discrepancias=True):
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

    # Mostrar resumen de ventas SIAT antes de comparar con inventario
    generar_reporte_ventas(siat_processed)

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
    comparison_results = compare_siat_with_inventory(siat_processed, inventory_data)
    
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
    
    if 'field_discrepancies' in comparison_results and comparison_results['field_discrepancies']:
        print(f"\nFacturas con discrepancias en campos: {len(comparison_results['field_discrepancies'])}")
    
    # Mostrar detalle de discrepancias en consola si corresponde
    if print_discrepancias and 'comparison_dataframe' in comparison_results:
        comparison_df = comparison_results['comparison_dataframe']
        discrepancias_df = comparison_df[comparison_df['OBSERVACIONES'].astype(str).str.strip() != '']
        if not discrepancias_df.empty:
            imprimir_discrepancias_consola(discrepancias_df)
    
    # Exportar resultados si se solicita
    if export_results:
        output_dir = os.path.join(project_root, "data", "output")
        os.makedirs(output_dir, exist_ok=True)

        # Exportar archivo de verificación completa (todas las facturas SIAT con observaciones)
        if 'verificacion_completa' in comparison_results:
            df = comparison_results['verificacion_completa']
            # Asegurarse de que las columnas necesarias existen
            if all(col in df.columns for col in ['SECTOR', 'FECHA DE LA FACTURA', 'Nº DE LA FACTURA', 'SUCURSAL']):
                # ORDENAR ANTES DE EXPORTAR: primero alquileres (SECTOR==02), luego ventas (SECTOR!=02)
                # Alquileres: SECTOR == '02'
                alquileres = df[df['SECTOR'] == '02'].copy()
                alquileres = alquileres.sort_values(by=['FECHA DE LA FACTURA', 'Nº DE LA FACTURA'], ascending=[True, True])
                # Ventas: SECTOR != '02'
                ventas = df[df['SECTOR'] != '02'].copy()
                # Sucursal puede tener valores como '0', '5', '6', aseguramos tipo str->int->str para orden correcto
                ventas['SUCURSAL_ORD'] = ventas['SUCURSAL'].astype(str).str.lstrip('0').replace('', '0').astype(int)
                ventas = ventas.sort_values(by=['SUCURSAL_ORD', 'FECHA DE LA FACTURA', 'Nº DE LA FACTURA'], ascending=[True, True, True])
                ventas = ventas.drop(columns=['SUCURSAL_ORD'])
                # Concatenar
                df_ordenado = pd.concat([alquileres, ventas], ignore_index=True)
                # Renumerar la columna 'Nº' después de ordenar y antes de exportar
                if 'Nº' in df_ordenado.columns:
                    df_ordenado['Nº'] = range(1, len(df_ordenado) + 1)
                comparison_results['verificacion_completa'] = df_ordenado
            # Si falta alguna columna, exportar sin ordenar especial
            # Ensure NIT/CI and invoice number fields are string before export (remove .0)
            str_cols = [
                col for col in [
                    'nit_siat', 'nit_inv', 'NIT / CI CLIENTE', 'NIT',
                    'Nº DE LA FACTURA', 'nfactura_siat', 'nfactura_inv', 'nFactura'
                ] if col in comparison_results['verificacion_completa'].columns
            ]
            for col in str_cols:
                comparison_results['verificacion_completa'][col] = comparison_results['verificacion_completa'][col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
            verif_path = os.path.join(output_dir, f"verificacion_completa_{formatted_month}_{year}.csv")
            comparison_results['verificacion_completa'].to_csv(verif_path, index=False, sep=',')
            print(f"Archivo de verificación completa guardado en: {verif_path}")

        # Unificar discrepancias en un solo DataFrame SOLO desde el comparison_dataframe
        columns_to_export = [
            'autorizacion',
            'fecha_siat', 'fecha_inv',
            'nfactura_siat', 'nfactura_inv',
            'nit_siat', 'nit_inv',
            'importe_siat', 'importe_inv',
            'diferencia_importe',
            'estado_siat', 'estado_inv',
            'sucursal_siat', 'sucursal_inv',
            'sucursal_siat_norm', 'sucursal_inv_norm',
            'OBSERVACIONES'
        ]
        if 'comparison_dataframe' in comparison_results:
            comparison_df = comparison_results['comparison_dataframe']
            # Filtrar solo discrepancias (OBSERVACIONES no vacío)
            discrepancias_df = comparison_df[comparison_df['OBSERVACIONES'].astype(str).str.strip() != '']
            # Eliminar duplicados por autorizacion (mantener la fila más informativa)
            discrepancias_df = discrepancias_df.sort_values(
                by=['fecha_siat', 'nfactura_siat', 'nit_siat'], na_position='last'
            ).drop_duplicates(subset=['autorizacion'], keep='first')
            if not discrepancias_df.empty:
                # Ensure NIT/CI and invoice number fields are string before export (remove .0)
                str_cols = [
                    col for col in [
                        'nit_siat', 'nit_inv', 'NIT / CI CLIENTE', 'NIT',
                        'Nº DE LA FACTURA', 'nfactura_siat', 'nfactura_inv', 'nFactura'
                    ] if col in discrepancias_df.columns
                ]
                for col in str_cols:
                    discrepancias_df[col] = discrepancias_df[col].astype(str).str.replace(r'\.0$', '', regex=True).str.strip()
                discrepancias_path = os.path.join(output_dir, f"discrepancias_{formatted_month}_{year}.csv")
                discrepancias_df[columns_to_export].to_csv(discrepancias_path, index=False, sep=',')
                print(f"Archivo único de discrepancias guardado en: {discrepancias_path}")
            else:
                print("No se encontraron discrepancias para exportar.")
        else:
            print("No se encontraron discrepancias para exportar.")
        return comparison_results

def imprimir_discrepancias_consola(discrepancias_df):
    """
    Imprime en consola un resumen detallado y amigable de las discrepancias encontradas.
    """
    if discrepancias_df.empty:
        print("No se encontraron discrepancias relevantes.")
        return
    print("\n=== DETALLE DE DISCREPANCIAS ENCONTRADAS ===\n")
    for idx, row in discrepancias_df.iterrows():
        print(f"CUF: {row.get('autorizacion','')}")
        print(f"  Nº Factura: {row.get('nfactura_siat') or row.get('nfactura_inv') or ''}")
        print(f"  Fecha: {row.get('fecha_siat') or row.get('fecha_inv') or ''}")
        print(f"  Cliente (NIT): {row.get('nit_siat') or row.get('nit_inv') or ''}")
        print(f"  Monto: SIAT={row.get('importe_siat') if not pd.isna(row.get('importe_siat')) else '-'} | INV={row.get('importe_inv') if not pd.isna(row.get('importe_inv')) else '-'}")
        print(f"  Estado: SIAT={row.get('estado_siat') or '-'} | INV={row.get('estado_inv') or '-'}")
        print(f"  Sucursal: SIAT={row.get('sucursal_siat') or '-'} | INV={row.get('sucursal_inv') or '-'}")
        print(f"  Sector: {row.get('sucursal_siat_norm') or row.get('sucursal_inv_norm') or '-'}")
        print(f"  Observaciones: {row.get('OBSERVACIONES','')}")
        print("-"*60)

def generar_reporte_ventas(df):
    """
    Genera e imprime un reporte resumen de ventas a partir del DataFrame del SIAT.
    """
    def fmt(val):
        return f"{val:,.2f}" if isinstance(val, (int, float)) else val

    # === ALQUILERES ===
    df_alq = df[df["SECTOR"] == '02']
    total_alquileres = df_alq[df_alq["ESTADO"] == 'VALIDA']["IMPORTE TOTAL DE LA VENTA"].sum()
    facturas_alq_validas = len(df_alq[df_alq["ESTADO"] == 'VALIDA'])
    facturas_alq_anuladas = len(df_alq[df_alq["ESTADO"] == 'ANULADA'])

    # === TOTALES GENERALES ===
    df_validas = df[df["ESTADO"] == "VALIDA"]
    total_ventas_validas = df_validas["IMPORTE TOTAL DE LA VENTA"].sum()
    total_ventas_sin_alquiler = total_ventas_validas - total_alquileres

    # === SUCURSAL CENTRAL (0000) ===
    df_central = df[df['SUCURSAL'] == '0000']
    df_central_validas_cv = df_central[(df_central['ESTADO'] == 'VALIDA') & (df_central['SECTOR'] == '01')]
    df_central_validas_cvb = df_central[(df_central['ESTADO'] == 'VALIDA') & (df_central['SECTOR'] == '35')]
    df_central_anuladas = df_central[df_central['ESTADO'] == 'ANULADA']
    total_central = df_central_validas_cv["IMPORTE TOTAL DE LA VENTA"].sum() + df_central_validas_cvb["IMPORTE TOTAL DE LA VENTA"].sum()

    # === SUCURSAL POTOSÍ (0006) ===
    df_potosi = df[df['SUCURSAL'] == '0006']
    df_potosi_validas = df_potosi[(df_potosi['ESTADO'] == 'VALIDA') & (df_potosi['SECTOR'] == '01')]
    df_potosi_anuladas = df_potosi[(df_potosi['ESTADO'] == 'ANULADA') & (df_potosi['SECTOR'] == '01')]
    total_potosi = df_potosi_validas["IMPORTE TOTAL DE LA VENTA"].sum()

    # === SUCURSAL SANTA CRUZ (0005) ===
    df_scz = df[df['SUCURSAL'] == '0005']
    df_scz_validas = df_scz[(df_scz['ESTADO'] == 'VALIDA') & (df_scz['SECTOR'] == '01')]
    df_scz_anuladas = df_scz[(df_scz['ESTADO'] == 'ANULADA') & (df_scz['SECTOR'] == '01')]
    total_scz = df_scz_validas["IMPORTE TOTAL DE LA VENTA"].sum()

    # === RESUMEN DE FACTURAS ===
    total_facturas_validas = len(df[df['ESTADO'] == 'VALIDA'])
    total_facturas_anuladas = len(df[df['ESTADO'] == 'ANULADA'])
    total_facturas = len(df)

    print("\n--- REPORTE DE VENTAS ---\n")
    print("=== ALQUILERES ===")
    print(f"Total Alquileres: {fmt(total_alquileres)}")
    print(f"Facturas Válidas: {facturas_alq_validas}")
    print(f"Facturas Anuladas: {facturas_alq_anuladas}\n")

    print("=== TOTALES GENERALES ===")
    print(f"Total Ventas Válidas: {fmt(total_ventas_validas)}")
    print(f"Total Ventas sin Alquiler: {fmt(total_ventas_sin_alquiler)}\n")

    print("=== SUCURSAL CENTRAL (0000) ===")
    print(f"Total Ventas: {fmt(total_central)}")
    print(f"Facturas Válidas CV: {len(df_central_validas_cv)}")
    print(f"Facturas Válidas CVB: {len(df_central_validas_cvb)}")
    print(f"Facturas Anuladas: {len(df_central_anuladas)}\n")

    print("=== SUCURSAL POTOSÍ (0006) ===")
    print(f"Total Ventas: {fmt(total_potosi)}")
    print(f"Facturas Válidas: {len(df_potosi_validas)}")
    print(f"Facturas Anuladas: {len(df_potosi_anuladas)}\n")

    print("=== SUCURSAL SANTA CRUZ (0005) ===")
    print(f"Total Ventas: {fmt(total_scz)}")
    print(f"Facturas Válidas: {len(df_scz_validas)}")
    print(f"Facturas Anuladas: {len(df_scz_anuladas)}\n")

    print("=== RESUMEN DE FACTURAS ===")
    print(f"Total Facturas Válidas: {total_facturas_validas}")
    print(f"Total Facturas Anuladas: {total_facturas_anuladas}")
    print(f"Total Facturas: {total_facturas}\n")
    print("--- Ventas Application Finished ---\n")