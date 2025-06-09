"""
Script principal de ventas-plus.
Este script procesa datos de ventas a partir de un archivo Excel comprimido en ZIP.
"""
import os
import sys
import pandas as pd
from datetime import datetime, timedelta
import argparse
from dotenv import load_dotenv
from ventas_plus.barra_progreso import barra_progreso
import time

from ventas_plus.core_logic import (
    process_zipped_sales_excel,
    process_sales_data,
    analyze_sales_data_basic,
    analyze_sales_data_detailed,
    verify_invoice_consistency,
    generar_reporte_ventas,
    mostrar_comparacion_siat_hergo
)
from ventas_plus.comparison import compare_siat_with_inventory, compare_sales_totals
from ventas_plus.hergo_api import get_hergo_sales_totals
from ventas_plus.ventas_processing import get_siat_sales_totals

# Cargar variables de entorno desde .env
load_dotenv()

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
        print(f"Recuperados con éxito {len(sales_data)} registros de ventas.")
        print("Procesando datos de ventas...")
        
        # Procesar los datos de ventas
        siat_df = process_sales_data(sales_data)
        
        # Solo mostrar el reporte resumen, no info de columnas ni análisis básico
        generar_reporte_ventas(siat_df)
        print("\n--- CONSULTANDO AL SISTEMA DE INVENTARIOS (HERGO) ---")
        # --- Comparar SIAT vs Hergo automáticamente ---
        comparar_con_hergo(project_root, int(year), int(month), siat_df)
        
    else:
        print("No se encontraron datos de ventas o hubo un error al procesar el archivo ZIP.")

def verify_invoices_consistency(project_root, month=None, year=None, print_discrepancias=True):
    """
    Verifica la consistencia entre las facturas del SIAT y el sistema de inventarios.
    Si el usuario lo desea, importa el archivo de verificación a la base contable.
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
    verify_invoice_consistency(project_root, config_file_path, month, year, print_discrepancias=print_discrepancias)
    
    # Mostrar cuadro comparativo SIAT vs Inventario
    from ventas_plus.core_logic import mostrar_cuadro_comparativo_verificacion
    import pandas as pd
    output_dir = os.path.join(project_root, 'data', 'output')
    formatted_month = f"{int(month):02d}"
    verif_path = os.path.join(output_dir, f"verificacion_completa_{formatted_month}_{year}.csv")
    if os.path.exists(verif_path):
        df_siat = pd.read_csv(verif_path)
        # Consultar inventario
        from ventas_plus.db_utils import get_db_config, get_inventory_system_invoices
        db_params = get_db_config(config_file_path)
        df_inv = get_inventory_system_invoices(db_params, int(year), int(month))
        if df_inv is not None and not df_inv.empty:
            mostrar_cuadro_comparativo_verificacion(df_siat, df_inv)
    # --- Integración de importación a contabilidad ---
    print("\n¿Desea importar el archivo de verificación a la base de datos contable? (s/N): ", end="")
    resp = input().strip().lower()
    if resp == 's':
        try:
            from ventas_plus.importar_verificacion_contabilidad import main_import
            main_import(int(month), int(year))
        except Exception as e:
            print(f"[ERROR] Falló la importación a contabilidad: {e}")

def comparar_con_hergo(project_root, year, month, siat_df):
    """
    Consulta Hergo, calcula totales SIAT, compara y muestra tabla.
    Si la consulta a Hergo falla, muestra un error pero continúa el flujo.
    """
    from ventas_plus.hergo_api import HergoAPI
    # Totales SIAT
    siat_totales = get_siat_sales_totals(siat_df)
    # Inicializar HergoAPI (usa env vars si existen)
    try:
        hergo_api = HergoAPI()
    except Exception as e:
        print(f"[ERROR] No se pudo inicializar conexión a Hergo: {e}")
        hergo_totales = {k: None for k in ['CENTRAL', 'SANTA CRUZ', 'POTOSI', 'GENERAL']}
        comparacion = compare_sales_totals(siat_totales, hergo_totales)
        mostrar_comparacion_siat_hergo(comparacion)
        return
    # Totales Hergo por sucursal
    hergo_totales = {}
    sucursales = list({'CENTRAL': 0, 'SANTA CRUZ': 5, 'POTOSI': 6}.items()) + [('GENERAL', None)]
    total = len(sucursales)
    barra_len = 60  # barra más grande
    # Mostrar barra de progreso desde el inicio
    for idx, (nombre, cod) in enumerate(sucursales, 1):
        barra = "█" * int(barra_len * idx / total) + "-" * (barra_len - int(barra_len * idx / total))
        sys.stdout.write(f"\rConsultando reporte de ventas Hergo |{barra}| {nombre:10s}   ")
        sys.stdout.flush()
        res = hergo_api.get_sales_totals(year, month, cod)
        if res.get('total') is None:
            print(f"\n[ERROR] Hergo: No se pudo obtener total para {nombre}: {res.get('error','Sin detalle')}")
        hergo_totales[nombre] = res.get('total')
        time.sleep(0.2)
    sys.stdout.write("\n")
    sys.stdout.flush()
    # Comparar
    print("Procesando comparación SIAT vs Hergo...")
    comparacion = compare_sales_totals(siat_totales, hergo_totales)
    mostrar_comparacion_siat_hergo(comparacion)

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
            args.year,
            print_discrepancias=True
        )
    else:
        # Procesar los datos de ventas con los parámetros especificados
        process_sales_data_basic(
            project_root,
            args.month,
            args.year
        )
    
    print("\n--- Ventas-Plus: Procesamiento Finalizado ---")
