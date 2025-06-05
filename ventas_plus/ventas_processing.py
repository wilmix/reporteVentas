"""
Módulo para el procesamiento y análisis de los datos de ventas.
"""
import pandas as pd

def process_sales_data(sales_data):
    df = sales_data.copy()
    numeric_columns = ['IMPORTE TOTAL DE LA VENTA'] if 'IMPORTE TOTAL DE LA VENTA' in df.columns else []
    for col in numeric_columns:
        df[col] = pd.to_numeric(df[col], errors='coerce')
    df = df.dropna(how='all')
    if 'CODIGO DE AUTORIZACIÓN' in df.columns:
        df['SUCURSAL'] = ''
        df['MODALIDAD'] = ''
        df['TIPO EMISION'] = ''
        df['TIPO FACTURA'] = ''
        df['SECTOR'] = ''
        df['NUM FACTURA'] = ''
        df['PV'] = ''
        df['CODIGO AUTOVERIFICADOR'] = ''
        for index, row in df.iterrows():
            try:
                codigo = row['CODIGO DE AUTORIZACIÓN']
                if isinstance(codigo, str) and len(codigo) >= 42:
                    hexadecimal = codigo[:42]
                    decimal = int(hexadecimal, 16)
                    cadena = str(decimal)
                    if len(cadena) > 27:
                        cadena = cadena[27:]
                        if len(cadena) >= 24:
                            sucursal = cadena[:4]
                            modalidad = cadena[4:5] if len(cadena) > 4 else ''
                            tipo_emision = cadena[5:6] if len(cadena) > 5 else ''
                            tipo_factura = cadena[6:7] if len(cadena) > 6 else ''
                            tipo_documento_sector = cadena[7:9] if len(cadena) > 8 else ''
                            num_factura = cadena[9:19] if len(cadena) > 18 else ''
                            pv = cadena[19:23] if len(cadena) > 22 else ''
                            codigo_autoverificador = cadena[23:24] if len(cadena) > 23 else ''
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
    results = {
        "total_records": len(df),
        "columns": list(df.columns),
    }
    if 'IMPORTE TOTAL DE LA VENTA' in df.columns:
        results['total_ventas'] = df['IMPORTE TOTAL DE LA VENTA'].sum()
        results['promedio_venta'] = df['IMPORTE TOTAL DE LA VENTA'].mean()
        results['venta_maxima'] = df['IMPORTE TOTAL DE LA VENTA'].max()
    if 'ESTADO' in df.columns:
        results['conteo_estados'] = df['ESTADO'].value_counts().to_dict()
    if 'SUCURSAL' in df.columns:
        results['conteo_sucursales'] = df['SUCURSAL'].value_counts().to_dict()
    if 'TIPO EMISION' in df.columns:
        results['conteo_tipo_emision'] = df['TIPO EMISION'].value_counts().to_dict()
    if 'SECTOR' in df.columns:
        results['conteo_sector'] = df['SECTOR'].value_counts().to_dict()
    return results

def analyze_sales_data_detailed(df):
    # Puedes copiar aquí la función completa si lo deseas
    pass

def get_siat_sales_totals(df):
    """
    Calcula los totales de ventas SIAT por sucursal y general, usando la misma lógica que el reporte principal:
    - CENTRAL: suma sector 01 y 35
    - SANTA CRUZ y POTOSI: solo sector 01
    - GENERAL: suma todas las ventas válidas excepto sector 02 (alquileres)
    Retorna: dict con claves por sucursal y 'GENERAL'.
    """
    sucursales = {
        'CENTRAL': '0000',
        'SANTA CRUZ': '0005',
        'POTOSI': '0006',
    }
    totales = {}
    # CENTRAL: sector 01 y 35
    cod = sucursales['CENTRAL']
    total_central = df[(df['SUCURSAL'] == cod) & (df['ESTADO'] == 'VALIDA') & (df['SECTOR'].isin(['01', '35']))]['IMPORTE TOTAL DE LA VENTA'].sum()
    totales['CENTRAL'] = float(total_central)
    # SANTA CRUZ y POTOSI: solo sector 01
    for nombre in ['SANTA CRUZ', 'POTOSI']:
        cod = sucursales[nombre]
        total = df[(df['SUCURSAL'] == cod) & (df['ESTADO'] == 'VALIDA') & (df['SECTOR'] == '01')]['IMPORTE TOTAL DE LA VENTA'].sum()
        totales[nombre] = float(total)
    # GENERAL: todas las ventas válidas excepto sector 02
    total_general = df[(df['ESTADO'] == 'VALIDA') & (df['SECTOR'] != '02')]['IMPORTE TOTAL DE LA VENTA'].sum()
    totales['GENERAL'] = float(total_general)
    return totales
