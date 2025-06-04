"""
Módulo para la carga y procesamiento inicial de archivos (Excel, ZIP, etc).
"""
import os
import pandas as pd
import zipfile
import tempfile
import warnings
import contextlib

@contextlib.contextmanager
def suppress_openpyxl_warnings():
    with warnings.catch_warnings():
        warnings.filterwarnings("ignore", category=UserWarning, module="openpyxl")
        yield

def process_zipped_sales_excel(zip_file_path, sheet_name="hoja1"):
    try:
        with tempfile.TemporaryDirectory() as temp_dir:
            with zipfile.ZipFile(zip_file_path, 'r') as zip_ref:
                zip_ref.extractall(temp_dir)
            excel_files = [f for f in os.listdir(temp_dir) if f.endswith('.xlsx')]
            if not excel_files:
                print(f"No se encontraron archivos Excel en {zip_file_path}")
                return None
            excel_path = os.path.join(temp_dir, excel_files[0])
            with suppress_openpyxl_warnings():
                return pd.read_excel(excel_path, sheet_name=sheet_name)
    except Exception as e:
        print(f"Error al procesar el archivo ZIP: {e}")
        return None
