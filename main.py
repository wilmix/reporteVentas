"""
Script principal de ventas-plus.
Este script procesa datos de ventas a partir de un archivo Excel comprimido en ZIP.
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import argparse
from ventas_plus.core_logic import (
    process_zipped_sales_excel,
    process_sales_data,
    analyze_sales_data_basic,
    analyze_sales_data_detailed,
    verify_invoice_consistency
)
from ventas_plus.comparison import compare_siat_with_inventory

def get_month_year_input(month=None, year=None):
    """
    Obtener mes y año desde la entrada del usuario si no se proporcionan.
    
    Args:
        month (str, optional): Mes en formato '01', '02', etc.
        year (int, optional): Año a procesar
        
    Returns:
        tuple: (month_str, year_int)
    """
    # Si ambos parámetros están proporcionados, validar y retornar
    if month and year:
        return month, int(year)
        
    # Obtener fecha actual
    current_date = datetime.now()
    # Obtener mes anterior restando un mes
    prev_date = current_date.replace(day=1) - timedelta(days=1)
    
    # Formatear mes y año anteriores
    default_month = prev_date.strftime('%m')
    default_year = prev_date.year
    
    if not month:
        while True:
            month_input = input(f"\nIntroduce el mes (1-12) [default: {default_month}]: ").strip()
            if month_input == "":
                month = default_month
                break
            try:
                month_int = int(month_input)
                if 1 <= month_int <= 12:
                    month = f"{month_int:02d}"
                    break
                else:
                    print("Error: El mes debe estar entre 1 y 12")
            except ValueError:
                print("Error: Por favor introduce un número válido")
    
    if not year:
        while True:
            year_input = input(f"Introduce el año [default: {default_year}]: ").strip()
            if year_input == "":
                year = default_year
                break
            try:
                year = int(year_input)
                if 2000 <= year <= 2100:  # Rango razonable de años
                    break
                else:
                    print("Error: El año debe estar entre 2000 y 2100")
            except ValueError:
                print("Error: Por favor introduce un año válido")
                
    return month, year

def process_sales_data_basic(project_root, month=None, year=None):
    """
    Procesa datos básicos de ventas desde un archivo ZIP.
    
    Args:
        project_root (str): Directorio raíz del proyecto
        month (str, optional): Mes a procesar en formato '01', '02', etc.
        year (int, optional): Año a procesar
    """
    print("\n--- Procesando datos de ventas ---")
    
    # Obtener mes y año a través de entrada interactiva si no se proporcionan
    month, year = get_month_year_input(month, year)
    
    # Ruta a la carpeta del año y al archivo ZIP
    year_folder = os.path.join(project_root, "data", str(year))
    # Formatear mes con cero a la izquierda para meses de un dígito
    formatted_month = f"{int(month):02d}"
    zip_file_name = f"{formatted_month}VentasXlsx.zip"
    zip_file_path = os.path.join(year_folder, zip_file_name)
    
    # Verificar si el archivo existe
    if not os.path.exists(zip_file_path):
        print(f"\nError: No se encontró el archivo {zip_file_name} en la carpeta {year_folder}")
        print("Por favor, verifica que:")
        print(f"1. Existe la carpeta para el año {year} en data/")
        print(f"2. El archivo {zip_file_name} está en la carpeta del año")
        return
    
    # Procesar el archivo ZIP y obtener los datos de ventas
    print(f"Leyendo datos de ventas del mes: {month} y año: {year}")
    print(f"Archivo: {zip_file_path}")
    sales_data = process_zipped_sales_excel(zip_file_path, sheet_name="hoja1")
    
    if sales_data is not None and not sales_data.empty:
        # Definir directorio de salida
        output_dir = os.path.join(project_root, "data", "output")
        os.makedirs(output_dir, exist_ok=True)
        
        print(f"Recuperados con éxito {len(sales_data)} registros de ventas.")
        print("Procesando datos de ventas...")
        
        # Procesar los datos de ventas
        df_processed = process_sales_data(sales_data)
        
        # Mostrar información básica del DataFrame
        print("\n=== INFORMACIÓN DEL DATAFRAME ===")
        print(f"Filas: {df_processed.shape[0]}, Columnas: {df_processed.shape[1]}")
        print("\nColumnas disponibles:")
        for col in df_processed.columns:
            print(f"  • {col}")
        
        # Mostrar muestra de los datos
        print("\n=== MUESTRA DE DATOS (5 primeros registros) ===")
        pd.set_option('display.max_columns', None)  # Mostrar todas las columnas
        pd.set_option('display.width', None)        # Ancho automático
        print(df_processed.head())
        
        # Realizar análisis básico
        results = analyze_sales_data_basic(df_processed)
        
        # Mostrar resultados básicos
        print("\n=== ANÁLISIS BÁSICO ===")
        if 'total_ventas' in results:
            print(f"Total de ventas: {results['total_ventas']:,.2f}")
        if 'promedio_venta' in results:
            print(f"Promedio por venta: {results['promedio_venta']:,.2f}")
        if 'conteo_estados' in results:
            print("\nDistribución por estado:")
            for estado, conteo in results['conteo_estados'].items():
                print(f"  • {estado}: {conteo}")
        
        # Mostrar información de las columnas extraídas del código de autorización
        if 'conteo_sucursales' in results:
            print("\nDistribución por sucursal:")
            for sucursal, conteo in results['conteo_sucursales'].items():
                if sucursal:  # Solo mostrar si hay un valor
                    print(f"  • {sucursal}: {conteo}")
        
        if 'conteo_tipo_emision' in results:
            print("\nDistribución por tipo de emisión:")
            for tipo, conteo in results['conteo_tipo_emision'].items():
                if tipo:  # Solo mostrar si hay un valor
                    print(f"  • {tipo}: {conteo}")
        
        if 'conteo_sector' in results:
            print("\nDistribución por sector:")
            for sector, conteo in results['conteo_sector'].items():
                if sector:  # Solo mostrar si hay un valor
                    print(f"  • {sector}: {conteo}")
        
        # Realizar análisis detallado
        detailed_results = analyze_sales_data_detailed(df_processed)
        
        # Mostrar el análisis detallado
        print("\n\n=== ANÁLISIS DETALLADO DE VENTAS ===")
        
        # Análisis de Alquileres
        if 'alquileres' in detailed_results:
            alq = detailed_results['alquileres']
            print("\n--- ALQUILERES (SECTOR 02) ---")
            print(f"Total facturado en alquileres: {alq['total_facturado']:,.2f}")
            print(f"Cantidad de facturas válidas: {alq['cantidad_validas']}")
            print(f"Cantidad de facturas anuladas: {alq['cantidad_anuladas']}")
        
        # Análisis General
        if 'general' in detailed_results:
            general = detailed_results['general']
            print("\n--- FACTURACIÓN GENERAL ---")
            print(f"Total facturado (estado VALIDA): {general['total_facturado_valida']:,.2f}")
            print(f"Total facturado sin alquileres: {general['total_facturado_sin_alquiler']:,.2f}")
            print(f"Cantidad de facturas válidas: {general['cantidad_validas']}")
            print(f"Cantidad de facturas anuladas: {general['cantidad_anuladas']}")
        
        # Análisis Central (La Paz)
        if 'central' in detailed_results:
            central = detailed_results['central']
            print("\n--- CENTRAL LA PAZ (SUCURSAL 0000) ---")
            print(f"Total facturado: {central['total_facturado']:,.2f}")
            print(f"Cantidad de facturas válidas (CV - Sector 01): {central['cantidad_validas_cv']}")
            print(f"Cantidad de facturas válidas (CVB - Sector 35): {central['cantidad_validas_cvb']}")
            print(f"Cantidad de facturas anuladas: {central['cantidad_anuladas']}")
        
        # Análisis Potosí
        if 'potosi' in detailed_results:
            potosi = detailed_results['potosi']
            print("\n--- POTOSÍ (SUCURSAL 0006) ---")
            print(f"Total facturado: {potosi['total_facturado']:,.2f}")
            print(f"Cantidad de facturas válidas: {potosi['cantidad_validas']}")
            print(f"Cantidad de facturas anuladas: {potosi['cantidad_anuladas']}")
        
        # Análisis Santa Cruz
        if 'santa_cruz' in detailed_results:
            scz = detailed_results['santa_cruz']
            print("\n--- SANTA CRUZ (SUCURSAL 0005) ---")
            print(f"Total facturado: {scz['total_facturado']:,.2f}")
            print(f"Cantidad de facturas válidas: {scz['cantidad_validas']}")
            print(f"Cantidad de facturas anuladas: {scz['cantidad_anuladas']}")
        
        # Resumen total de facturas
        if 'total_facturas_desglosado' in detailed_results:
            print("\n--- RESUMEN TOTAL DE FACTURAS ---")
            print(f"Total de facturas (desglosado): {detailed_results['total_facturas_desglosado']}")
            print(f"Total de facturas (general): {detailed_results['general']['total_facturas']}")
            
        # Guardar una copia del DataFrame procesado para uso futuro
        output_file = os.path.join(output_dir, f"ventas_procesadas_{month}_{year}.csv")
        df_processed.to_csv(output_file, index=False)
        print(f"\nDatos procesados guardados en: {output_file}")
        
    else:
        print("No se encontraron datos de ventas o hubo un error al procesar el archivo ZIP.")

def verify_invoices_consistency(project_root, month=None, year=None):
    """
    Verifica la consistencia entre las facturas del SIAT y el sistema de inventarios.
    
    Args:
        project_root (str): Directorio raíz del proyecto
        month (str, optional): Mes a procesar en formato '01', '02', etc.
        year (int, optional): Año a procesar
    """
    # Obtener mes y año a través de entrada interactiva si no se proporcionan
    month, year = get_month_year_input(month, year)
    
    # Ruta al archivo de configuración de la BD
    config_file_path = os.path.join(project_root, "db_config.ini")
    
    # Verificar que el archivo de configuración existe
    if not os.path.exists(config_file_path):
        print(f"\nError: No se encontró el archivo de configuración {config_file_path}")
        print("Por favor, crea el archivo con la configuración de la base de datos.")
        return
        
    # Ejecutar la verificación de consistencia
    verify_invoice_consistency(project_root, config_file_path, month, year)

if __name__ == "__main__":
    print("""
╔══════════════════════════════════════╗
║         VENTAS-PLUS SISTEMA          ║
╚══════════════════════════════════════╝
""")
    
    # Configurar argumentos de línea de comandos
    parser = argparse.ArgumentParser(description="Procesar datos de ventas desde un archivo Excel comprimido.")
    parser.add_argument('-m', '--month', help='Mes a procesar en formato 01, 02, etc.', default=None)
    parser.add_argument('-y', '--year', help='Año a procesar (ej. 2025)', default=None)
    parser.add_argument('-v', '--verify', action='store_true', help='Verificar consistencia con sistema de inventarios')
    args = parser.parse_args()
    
    project_root = os.path.dirname(os.path.abspath(__file__))
    
    if args.verify:
        # Verificar consistencia entre SIAT y sistema de inventarios
        verify_invoices_consistency(
            project_root,
            args.month,
            args.year
        )
    else:
        # Procesar los datos de ventas con los parámetros especificados
        process_sales_data_basic(
            project_root,
            args.month,
            args.year
        )
    
    print("\n--- Ventas-Plus: Procesamiento Finalizado ---")
