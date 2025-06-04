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
