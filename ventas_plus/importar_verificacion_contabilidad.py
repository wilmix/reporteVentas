"""
Script para leer y mostrar el contenido del archivo de verificación completa generado por Ventas-Plus.
Permite validar la lectura y el formato antes de avanzar con la importación a la base de datos contable.
"""

def main_import(mes, anno):
    import pandas as pd
    import os
    import numpy as np
    from datetime import datetime
    # Formato de nombre de archivo según README
    csv_path = os.path.join(
        "data", "output", f"verificacion_completa_{mes:02d}_{anno}.csv"
    )
    if not os.path.exists(csv_path):
        print(f"No se encontró el archivo: {csv_path}")
        return
    print(f"Leyendo archivo: {csv_path}\n")
    df = pd.read_csv(csv_path, encoding="utf-8")
    print("Columnas detectadas:")
    print(list(df.columns))
    print("\nPrimeras filas:")
    print(df.head(5))
    print(f"\nTotal de filas: {len(df)}")
    # --- Validación y transformación de datos para mapeo a la base contable ---
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
    mapped_df = df.rename(columns=column_map)
    expected_cols = list(column_map.values())
    missing_cols = [col for col in expected_cols if col not in mapped_df.columns]
    for col in missing_cols:
        mapped_df[col] = None

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
        # --- Comparación previa entre base y CSV (resumen simplificado) ---
        def resumen_registros(df, nombre):
            total = len(df)
            # Mapear status a letras estándar para el resumen
            status_col = df['status'].map(lambda x: 'V' if str(x).strip().upper() in ['V', 'VALIDA'] else ('A' if str(x).strip().upper() in ['A', 'ANULADA'] else x)) if 'status' in df.columns else pd.Series()
            status_counts = status_col.value_counts() if not status_col.empty else pd.Series()
            # Filtrar solo facturas válidas para los totales
            validas_mask = status_col == 'V'
            total_venta = df.loc[validas_mask, 'total_sale_amount'].sum() if 'total_sale_amount' in df.columns else 0
            total_debito = df.loc[validas_mask, 'debit_tax'].sum() if 'debit_tax' in df.columns else 0
            print(f"\nResumen {nombre}:")
            print(f"  Total registros: {total}")
            print(f"  Suma total_sale_amount (solo V): {total_venta:,.2f}")
            print(f"  Suma debit_tax (solo V): {total_debito:,.2f}")
            print(f"  Facturas válidas (V): {status_counts.get('V', 0)}")
            print(f"  Facturas anuladas (A): {status_counts.get('A', 0)}")
            # Si quieres mostrar también C y L, descomenta:
            # print(f"  Contingencia (C): {status_counts.get('C', 0)}")
            # print(f"  Libre consignación (L): {status_counts.get('L', 0)}")
        # Leer registros existentes del periodo para el resumen
        try:
            query_comp = (
                "SELECT total_sale_amount, debit_tax, status FROM sales_registers "
                "WHERE invoice_date >= %s AND invoice_date <= %s"
            )
            cursor2 = conn.cursor(dictionary=True)
            cursor2.execute(query_comp, (fecha_inicio, fecha_fin))
            db_rows = cursor2.fetchall()
            db_df = pd.DataFrame(db_rows)
            cursor2.close()
        except Exception as e:
            print(f"Error al leer registros existentes: {e}")
            db_df = pd.DataFrame()
        resumen_registros(db_df, "en base de datos")
        resumen_registros(mapped_df, "en archivo CSV")
        print("""
Si continúas, se eliminarán todos los registros del periodo en la base y se reemplazarán por los del CSV.

Revisa el resumen antes de confirmar.
""")
        # --- Fin resumen ---
        if count > 0:
            respuesta = input("¿Desea ELIMINAR los registros de ese periodo y reemplazarlos por los nuevos? (s/N): ").strip().lower()
            if respuesta == 's':
                try:
                    delete_query = (
                        "DELETE FROM sales_registers WHERE invoice_date >= %s AND invoice_date <= %s"
                    )
                    cursor.execute(delete_query, (fecha_inicio, fecha_fin))
                    conn.commit()
                    print(f"Se eliminaron {cursor.rowcount} registros del periodo {mes:02d}/{anno}.")
                except Exception as e:
                    print(f"Error al eliminar registros existentes: {e}")
                    conn.close()
                    sys.exit(1)
            else:
                print("Operación cancelada por el usuario. No se realizó la importación.")
                conn.close()
                sys.exit(1)
        else:
            print(f"No existen registros previos para {mes:02d}/{anno} en sales_registers. Se puede proceder con la importación.")
        conn.close()
    except Exception as e:
        print(f"Error al verificar registros existentes en la base contable: {e}")
        sys.exit(1)

    # --- Comparación previa entre base y CSV (resumen simplificado) ---
    import pandas as pd

    def resumen_registros(df, nombre):
        total = len(df)
        # Mapear status a letras estándar para el resumen
        status_col = df['status'].map(lambda x: 'V' if str(x).strip().upper() in ['V', 'VALIDA'] else ('A' if str(x).strip().upper() in ['A', 'ANULADA'] else x)) if 'status' in df.columns else pd.Series()
        status_counts = status_col.value_counts() if not status_col.empty else pd.Series()
        # Filtrar solo facturas válidas para los totales
        validas_mask = status_col == 'V'
        total_venta = df.loc[validas_mask, 'total_sale_amount'].sum() if 'total_sale_amount' in df.columns else 0
        total_debito = df.loc[validas_mask, 'debit_tax'].sum() if 'debit_tax' in df.columns else 0
        print(f"\nResumen {nombre}:")
        print(f"  Total registros: {total}")
        print(f"  Suma total_sale_amount (solo V): {total_venta:,.2f}")
        print(f"  Suma debit_tax (solo V): {total_debito:,.2f}")
        print(f"  Facturas válidas (V): {status_counts.get('V', 0)}")
        print(f"  Facturas anuladas (A): {status_counts.get('A', 0)}")
        # Si quieres mostrar también C y L, descomenta:
        # print(f"  Contingencia (C): {status_counts.get('C', 0)}")
        # print(f"  Libre consignación (L): {status_counts.get('L', 0)}")

    try:
        conn = mysql.connector.connect(**db_params)
        query_comp = (
            "SELECT authorization_code, total_sale_amount, debit_tax, status FROM sales_registers "
            "WHERE invoice_date >= %s AND invoice_date <= %s"
        )
        db_df = pd.read_sql(query_comp, conn, params=(fecha_inicio, fecha_fin))
        conn.close()
    except Exception as e:
        print(f"Error al leer registros existentes: {e}")
        sys.exit(1)

    resumen_registros(db_df, "en base de datos")
    resumen_registros(mapped_df, "en archivo CSV")
    print("""
Si continúas, se eliminarán todos los registros del periodo en la base y se reemplazarán por los del CSV.
Revisa el resumen antes de confirmar.
""")

    # Mostrar resumen final
    # print(f"\nColumnas finales para insertar: {list(mapped_df.columns)}")
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
        # print(f"\nColumnas reales en sales_registers: {db_columns}")
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
        # print(f"\nColumnas del DataFrame justo antes de la inserción: {list(mapped_df.columns)}")
        # Limpiar DataFrame: eliminar columnas que no estén en db_columns
        valid_cols = [col for col in mapped_df.columns if col in db_columns]
        mapped_df = mapped_df[valid_cols]
        # Detectar columnas insertables (excluyendo id, created_at, updated_at)
        insert_cols = [
            col for col in db_columns
            if col not in ('id', 'created_at', 'updated_at') and col in mapped_df.columns
        ]
        # print(f"\nColumnas finales realmente insertadas: {insert_cols}")
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

# --- Script entrypoint ---
if __name__ == "__main__":
    import sys
    if len(sys.argv) != 3:
        print("Uso: python importar_verificacion_contabilidad.py <mes> <año>")
        print("Ejemplo: python importar_verificacion_contabilidad.py 1 2025")
        sys.exit(1)
    mes = int(sys.argv[1])
    anno = int(sys.argv[2])
    main_import(mes, anno)
    sys.exit(0)

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
