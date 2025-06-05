"""
Script para leer y mostrar el contenido del archivo de verificación completa generado por Ventas-Plus.
Permite validar la lectura y el formato antes de avanzar con la importación a la base de datos contable.
"""
import pandas as pd
import sys
import os

# Parámetros: mes y año
if len(sys.argv) != 3:
    print("Uso: python importar_verificacion_contabilidad.py <mes> <año>")
    print("Ejemplo: python importar_verificacion_contabilidad.py 1 2025")
    sys.exit(1)

mes = int(sys.argv[1])
anno = int(sys.argv[2])

# Formato de nombre de archivo según README
csv_path = os.path.join(
    "data", "output", f"verificacion_completa_{mes:02d}_{anno}.csv"
)

if not os.path.exists(csv_path):
    print(f"No se encontró el archivo: {csv_path}")
    sys.exit(1)

print(f"Leyendo archivo: {csv_path}\n")
df = pd.read_csv(csv_path, encoding="utf-8")

print("Columnas detectadas:")
print(list(df.columns))
print("\nPrimeras filas:")
print(df.head(5))

print(f"\nTotal de filas: {len(df)}")

# --- Validación y transformación de datos para mapeo a la base contable ---

# Mapeo de columnas CSV → DB (ajustar según sales_register_field_mapping.md)
column_map = {
    'FECHA DE LA FACTURA': 'invoice_date',
    'Nº DE LA FACTURA': 'invoice_number',
    'CODIGO DE AUTORIZACIÓN': 'authorization_code',
    'NIT / CI CLIENTE': 'customer_nit',
    'COMPLEMENTO': 'complement',
    'NOMBRE O RAZON SOCIAL': 'customer_name',
    'IMPORTE TOTAL DE LA VENTA': 'total_sale_amount',
    'IMPORTE ICE': 'ice_amount',
    'IMPORTE IEHD': 'iehd_amount',
    'IMPORTE IPJ': 'ipj_amount',
    'TASAS': 'fees',
    'OTROS NO SUJETOS AL IVA': 'other_non_vat_items',
    'EXPORTACIONES Y OPERACIONES EXENTAS': 'exports_exempt_operations',
    'VENTAS GRAVADAS A TASA CERO': 'zero_rate_taxed_sales',
    'SUBTOTAL': 'subtotal',
    'DESCUENTOS, BONIFICACIONES Y REBAJAS SUJETAS AL IVA': 'discounts_bonuses_rebates_subject_to_vat',
    'IMPORTE GIFT CARD': 'gift_card_amount',
    'IMPORTE BASE PARA DEBITO FISCAL': 'debit_tax_base_amount',
    'DEBITO FISCAL': 'debit_tax',
    'ESTADO': 'status',
    'CODIGO DE CONTROL': 'control_code',
    'TIPO DE VENTA': 'sale_type',
    'CON DERECHO A CREDITO FISCAL': 'right_to_tax_credit',
    'ESTADO CONSOLIDACION': 'consolidation_status',
    'SUCURSAL': 'branch_office',
    'MODALIDAD': 'modality',
    'TIPO EMISION': 'emission_type',
    'TIPO FACTURA': 'invoice_type',
    'SECTOR': 'sector',
    '_obs': 'obs',
    '_autor': 'author',
    'OBSERVACIONES': 'observations',
}

# Renombrar columnas
mapped_df = df.rename(columns=column_map)

# Seleccionar solo las columnas que existen en la tabla destino
expected_cols = list(column_map.values())
missing_cols = [col for col in expected_cols if col not in mapped_df.columns]
for col in missing_cols:
    mapped_df[col] = None  # Rellenar con None si no existe en el CSV

# Convertir tipos de datos
import numpy as np
from datetime import datetime

def parse_date(val):
    try:
        return datetime.strptime(str(val), '%d/%m/%Y').date()
    except Exception:
        return None

mapped_df['invoice_date'] = mapped_df['invoice_date'].apply(parse_date)
float_cols = [
    'total_sale_amount', 'ice_amount', 'iehd_amount', 'ipj_amount', 'fees',
    'other_non_vat_items', 'exports_exempt_operations', 'zero_rate_taxed_sales',
    'subtotal', 'discounts_bonuses_rebates_subject_to_vat', 'gift_card_amount',
    'debit_tax_base_amount', 'debit_tax'
]
for col in float_cols:
    mapped_df[col] = pd.to_numeric(mapped_df[col], errors='coerce')

# Validar nulos en campos obligatorios
obligatorios = [
    'invoice_date', 'invoice_number', 'authorization_code', 'customer_nit',
    'customer_name', 'total_sale_amount', 'status', 'control_code', 'sale_type',
    'right_to_tax_credit', 'consolidation_status', 'branch_office', 'modality',
    'emission_type', 'invoice_type', 'sector'
]
nulls = mapped_df[obligatorios].isnull().sum()
print("\nNulos en campos obligatorios:")
print(nulls[nulls > 0])

# Validar duplicados por (invoice_number, authorization_code)
duplicados = mapped_df.duplicated(subset=['invoice_number', 'authorization_code']).sum()
print(f"\nRegistros duplicados por (invoice_number, authorization_code): {duplicados}")

# --- Paso previo: Verificar si ya existen registros para el mes y año en la base contable ---
from ventas_plus.db_utils_contabilidad import get_db_config_contabilidad
import mysql.connector

config_path = "db_config_contabilidad.ini"
db_params = get_db_config_contabilidad(config_path)

# Determinar el rango de fechas del mes y año
from calendar import monthrange
fecha_inicio = f"{anno}-{mes:02d}-01"
dia_fin = monthrange(anno, mes)[1]
fecha_fin = f"{anno}-{mes:02d}-{dia_fin:02d}"

try:
    conn = mysql.connector.connect(**db_params)
    cursor = conn.cursor()
    query = (
        "SELECT COUNT(*) FROM sales_registers "
        "WHERE invoice_date >= %s AND invoice_date <= %s"
    )
    cursor.execute(query, (fecha_inicio, fecha_fin))
    count = cursor.fetchone()[0]
    if count > 0:
        print(f"\nADVERTENCIA: Ya existen {count} registros en sales_registers para {mes:02d}/{anno}.")
        print("Por seguridad, no se realizará la importación. Elimine primero los registros de ese periodo si desea reimportar.")
        conn.close()
        sys.exit(1)
    else:
        print(f"No existen registros previos para {mes:02d}/{anno} en sales_registers. Se puede proceder con la importación.")
    conn.close()
except Exception as e:
    print(f"Error al verificar registros existentes en la base contable: {e}")
    sys.exit(1)

# Mostrar resumen final
print(f"\nColumnas finales para insertar: {list(mapped_df.columns)}")
print(f"Total de filas listas para insertar: {len(mapped_df)}")

# Guardar DataFrame transformado temporalmente para revisión (opcional)
mapped_df.head(20).to_csv(f"data/output/preview_import_contabilidad_{mes:02d}_{anno}.csv", index=False)
print(f"\nSe guardó una vista previa de los primeros 20 registros transformados en data/output/preview_import_contabilidad_{mes:02d}_{anno}.csv")

# --- Verificar columnas reales en la tabla destino antes de insertar ---
try:
    conn = mysql.connector.connect(**db_params)
    cursor = conn.cursor()
    cursor.execute("SHOW COLUMNS FROM sales_registers")
    db_columns = [row[0] for row in cursor.fetchall()]
    print(f"\nColumnas reales en sales_registers: {db_columns}")
    conn.close()
except Exception as e:
    print(f"Error al consultar columnas de la tabla sales_registers: {e}")
    sys.exit(1)

# --- Inserción bulk en la base de datos contable ---
try:
    conn = mysql.connector.connect(**db_params)
    cursor = conn.cursor()
    # Limpiar DataFrame: eliminar columnas con nombre NaN o no-string
    mapped_df = mapped_df[[col for col in mapped_df.columns if isinstance(col, str) and col == col and col.strip() != '']]
    print(f"\nColumnas del DataFrame justo antes de la inserción: {list(mapped_df.columns)}")
    # Limpiar DataFrame: eliminar columnas que no estén en db_columns
    valid_cols = [col for col in mapped_df.columns if col in db_columns]
    mapped_df = mapped_df[valid_cols]
    # Detectar columnas insertables (excluyendo id, created_at, updated_at)
    insert_cols = [
        col for col in db_columns
        if col not in ('id', 'created_at', 'updated_at') and col in mapped_df.columns
    ]
    print(f"\nColumnas finales realmente insertadas: {insert_cols}")
    # Reordenar DataFrame
    insert_df = mapped_df[insert_cols]
    # Rellenar con 0.0 los campos numéricos NOT NULL si están vacíos
    numeric_notnull_cols = [
        'total_sale_amount', 'ice_amount', 'iehd_amount', 'ipj_amount', 'fees',
        'other_non_vat_items', 'exports_exempt_operations', 'zero_rate_taxed_sales',
        'subtotal', 'discounts_bonuses_rebates_subject_to_vat', 'gift_card_amount',
        'debit_tax_base_amount', 'debit_tax'
    ]
    for col in numeric_notnull_cols:
        if col in insert_df.columns:
            insert_df[col] = insert_df[col].fillna(0.0)
    # Rellenar con '0' los campos string NOT NULL si están vacíos (por ejemplo, control_code)
    string_notnull_cols = [
        'control_code', 'invoice_number', 'authorization_code', 'customer_nit', 'customer_name',
        'status', 'sale_type', 'consolidation_status', 'invoice_date'
    ]
    for col in string_notnull_cols:
        if col in insert_df.columns:
            insert_df[col] = insert_df[col].fillna('0')
    # Eliminar columna right_to_tax_credit si existe (ya no está en la BBDD)
    if 'right_to_tax_credit' in insert_df.columns:
        insert_df = insert_df.drop(columns=['right_to_tax_credit'])
        insert_cols = [c for c in insert_cols if c != 'right_to_tax_credit']
    # Convertir NaN y 'nan' string a None para MySQL en el resto
    insert_df = insert_df.applymap(lambda x: None if (pd.isnull(x) or str(x).lower() == 'nan') else x)
    # Preparar tuplas de valores
    values = [tuple(row) for row in insert_df.values]
    placeholders = ','.join(['%s'] * len(insert_cols))
    sql = f"""
        INSERT INTO sales_registers ({', '.join(insert_cols)})
        VALUES ({placeholders})
    """
    cursor.executemany(sql, values)
    conn.commit()
    print(f"\nSe insertaron {cursor.rowcount} registros en sales_registers para {mes:02d}/{anno}.")
    conn.close()
except mysql.connector.IntegrityError as ie:
    print(f"\nERROR de integridad al insertar: {ie}")
    print("Posiblemente hay un código de autorización duplicado o violación de restricción.")
    sys.exit(1)
except Exception as e:
    print(f"\nError general al insertar en la base contable: {e}")
    sys.exit(1)

'''
DOCUMENTACIÓN DEL FLUJO DE IMPORTACIÓN (resumen):

1. El script lee el archivo CSV de verificación completa generado por Ventas-Plus para el mes y año indicados.
2. Valida y transforma los datos:
   - Renombra columnas y ajusta tipos de datos.
   - Valida nulos en campos obligatorios y duplicados clave.
   - Prepara el DataFrame para coincidir con la estructura de la tabla sales_registers.
3. Antes de insertar, verifica si ya existen registros para ese mes y año en la base contable. Si existen, advierte y detiene el proceso para evitar duplicados.
4. Si no existen registros previos, realiza un bulk insert eficiente de todos los datos en la tabla sales_registers.
5. Maneja errores de integridad (por ejemplo, códigos de autorización duplicados) y reporta la cantidad de registros insertados.
6. Guarda una vista previa de los primeros 20 registros transformados para revisión manual.

Este flujo garantiza integridad, evita duplicados y permite pruebas seguras en entornos locales o de desarrollo.
'''
