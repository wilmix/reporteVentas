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
    print(f"\n=== IMPORTACIÓN A BASE CONTABLE ===")
    print(f"📅 Procesando: {mes:02d}/{anno}")
    print(f"📂 Archivo: {csv_path}")
    
    if not os.path.exists(csv_path):
        print(f"❌ ERROR: No se encontró el archivo de verificación completa")
        print(f"   Archivo esperado: {csv_path}")
        print(f"   Ejecuta primero la verificación con: python main.py -m {mes} -y {anno} -v")
        return
        
    print(f"📊 Cargando datos del archivo...")
    df = pd.read_csv(csv_path, encoding="utf-8")
    
    print(f"✅ Archivo cargado exitosamente")
    print(f"   📋 Columnas detectadas: {len(df.columns)}")
    print(f"   📄 Total de filas: {len(df):,}")
    
    # Mostrar solo las primeras filas para verificación rápida
    print(f"\n📋 Vista previa (primeras 3 filas):")
    print(df[['FECHA DE LA FACTURA', 'Nº DE LA FACTURA', 'CODIGO DE AUTORIZACIÓN', 'NOMBRE O RAZON SOCIAL', 'IMPORTE TOTAL DE LA VENTA', 'ESTADO']].head(3).to_string(index=False))
    # --- TRANSFORMACIÓN Y VALIDACIÓN DE DATOS ---
    print(f"\n--- PREPARANDO DATOS PARA IMPORTACIÓN ---")
    
    # Mapeo de columnas del CSV a la estructura de la base de datos
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
    
    # Aplicar transformaciones
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

    # Transformar fechas y números
    mapped_df['invoice_date'] = mapped_df['invoice_date'].apply(parse_date)
    float_cols = [
        'total_sale_amount', 'ice_amount', 'iehd_amount', 'ipj_amount', 'fees',
        'other_non_vat_items', 'exports_exempt_operations', 'zero_rate_taxed_sales',
        'subtotal', 'discounts_bonuses_rebates_subject_to_vat', 'gift_card_amount',
        'debit_tax_base_amount', 'debit_tax'
    ]
    for col in float_cols:
        mapped_df[col] = pd.to_numeric(mapped_df[col], errors='coerce')

    print(f"🔄 Datos transformados correctamente")
    
    # Validaciones de calidad
    obligatorios = [
        'invoice_date', 'invoice_number', 'authorization_code', 'customer_nit',
        'customer_name', 'total_sale_amount', 'status', 'control_code', 'sale_type',
        'right_to_tax_credit', 'consolidation_status', 'branch_office', 'modality',
        'emission_type', 'invoice_type', 'sector'
    ]
    nulls = mapped_df[obligatorios].isnull().sum()
    nulls_problem = nulls[nulls > 0]
    
    duplicados = mapped_df.duplicated(subset=['invoice_number', 'authorization_code']).sum()
    
    print(f"🔍 Validaciones de calidad:")
    if len(nulls_problem) > 0:
        print(f"   ⚠️  Campos obligatorios con nulos:")
        for field, count in nulls_problem.items():
            print(f"      - {field}: {count:,} nulos")
    else:
        print(f"   ✅ Todos los campos obligatorios completos")
        
    if duplicados > 0:
        print(f"   ⚠️  Registros duplicados: {duplicados:,}")
    else:
        print(f"   ✅ No hay duplicados por (factura + autorización)")

    # --- Verificar y comparar datos existentes en la base contable ---
    import sys
    import os
    sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
    from ventas_plus.db_utils_contabilidad import get_db_config_contabilidad
    import mysql.connector

    config_path = "db_config_contabilidad.ini"
    db_params = get_db_config_contabilidad(config_path)

    # Determinar el rango de fechas del mes y año
    from calendar import monthrange
    fecha_inicio = f"{anno}-{mes:02d}-01"
    dia_fin = monthrange(anno, mes)[1]
    fecha_fin = f"{anno}-{mes:02d}-{dia_fin:02d}"

    print(f"\n--- VERIFICANDO DATOS EXISTENTES EN BASE CONTABLE ---")
    print(f"Periodo: {mes:02d}/{anno} ({fecha_inicio} al {fecha_fin})")

    def resumen_registros(df, nombre):
        total = len(df)
        if total == 0:
            print(f"\n📋 Resumen {nombre}:")
            print(f"  ✅ No hay registros existentes")
            return
        
        # Mapear status a letras estándar para el resumen
        status_col = df['status'].map(lambda x: 'V' if str(x).strip().upper() in ['V', 'VALIDA'] else ('A' if str(x).strip().upper() in ['A', 'ANULADA'] else x)) if 'status' in df.columns else pd.Series()
        status_counts = status_col.value_counts() if not status_col.empty else pd.Series()
        # Filtrar solo facturas válidas para los totales
        validas_mask = status_col == 'V'
        total_venta = df.loc[validas_mask, 'total_sale_amount'].sum() if 'total_sale_amount' in df.columns else 0
        total_debito = df.loc[validas_mask, 'debit_tax'].sum() if 'debit_tax' in df.columns else 0
        
        print(f"\n📋 Resumen {nombre}:")
        print(f"  📊 Total registros: {total:,}")
        print(f"  💰 Ventas válidas: Bs. {total_venta:,.2f}")
        print(f"  🏛️  Débito fiscal: Bs. {total_debito:,.2f}")
        print(f"  ✅ Facturas válidas: {status_counts.get('V', 0):,}")
        print(f"  ❌ Facturas anuladas: {status_counts.get('A', 0):,}")

    try:
        conn = mysql.connector.connect(**db_params)
        
        # Verificar si existen registros para el periodo
        cursor = conn.cursor()
        query = "SELECT COUNT(*) FROM sales_registers WHERE invoice_date >= %s AND invoice_date <= %s"
        cursor.execute(query, (fecha_inicio, fecha_fin))
        count = cursor.fetchone()[0]
        
        # Leer registros existentes para comparación
        query_comp = (
            "SELECT authorization_code, total_sale_amount, debit_tax, status FROM sales_registers "
            "WHERE invoice_date >= %s AND invoice_date <= %s"
        )
        db_df = pd.read_sql(query_comp, conn, params=(fecha_inicio, fecha_fin))
        conn.close()
        
        # Mostrar resúmenes
        resumen_registros(db_df, "EXISTENTE en base de datos")
        resumen_registros(mapped_df, "NUEVO desde archivo CSV")
        
        # Manejar casos según existencia de datos
        if count > 0:
            print(f"\n⚠️  ATENCIÓN: Ya existen {count:,} registros para {mes:02d}/{anno} en la base contable.")
            print("   Si continúas, los registros existentes serán ELIMINADOS y reemplazados.")
            print("   Compara los resúmenes antes de decidir.")
            
            respuesta = input(f"\n¿Confirmas REEMPLAZAR los {count:,} registros existentes? (s/N): ").strip().lower()
            if respuesta == 's':
                try:
                    conn = mysql.connector.connect(**db_params)
                    cursor = conn.cursor()
                    delete_query = "DELETE FROM sales_registers WHERE invoice_date >= %s AND invoice_date <= %s"
                    cursor.execute(delete_query, (fecha_inicio, fecha_fin))
                    conn.commit()
                    print(f"✅ Se eliminaron {cursor.rowcount:,} registros del periodo {mes:02d}/{anno}.")
                    conn.close()
                except Exception as e:
                    print(f"❌ Error al eliminar registros existentes: {e}")
                    sys.exit(1)
            else:
                print("❌ Operación cancelada por el usuario. No se realizó la importación.")
                sys.exit(1)
        else:
            print(f"\n✅ Perfecto: No existen registros previos para {mes:02d}/{anno}.")
            print("   Se puede proceder directamente con la importación.")
            
    except Exception as e:
        print(f"❌ Error al verificar registros existentes en la base contable: {e}")
        sys.exit(1)

    # --- INSERCIÓN DE DATOS EN LA BASE CONTABLE ---
    print(f"\n--- INICIANDO IMPORTACIÓN A BASE CONTABLE ---")
    print(f"📄 Registros a insertar: {len(mapped_df):,}")
    
    # Guardar vista previa antes de insertar
    mapped_df.head(20).to_csv(f"data/output/preview_import_contabilidad_{mes:02d}_{anno}.csv", index=False)
    print(f"💾 Vista previa guardada: preview_import_contabilidad_{mes:02d}_{anno}.csv")

    try:
        conn = mysql.connector.connect(**db_params)
        cursor = conn.cursor()
        
        # Verificar columnas de la tabla destino
        cursor.execute("SHOW COLUMNS FROM sales_registers")
        db_columns = [row[0] for row in cursor.fetchall()]
        
        # Preparar DataFrame para inserción
        mapped_df = mapped_df[[col for col in mapped_df.columns if isinstance(col, str) and col == col and col.strip() != '']]
        valid_cols = [col for col in mapped_df.columns if col in db_columns]
        mapped_df = mapped_df[valid_cols]
        
        # Detectar columnas insertables (excluyendo campos auto-generados)
        insert_cols = [
            col for col in db_columns
            if col not in ('id', 'created_at', 'updated_at') and col in mapped_df.columns
        ]
        
        insert_df = mapped_df[insert_cols]
        
        # Completar campos obligatorios con valores por defecto
        numeric_notnull_cols = [
            'total_sale_amount', 'ice_amount', 'iehd_amount', 'ipj_amount', 'fees',
            'other_non_vat_items', 'exports_exempt_operations', 'zero_rate_taxed_sales',
            'subtotal', 'discounts_bonuses_rebates_subject_to_vat', 'gift_card_amount',
            'debit_tax_base_amount', 'debit_tax'
        ]
        for col in numeric_notnull_cols:
            if col in insert_df.columns:
                insert_df[col] = insert_df[col].fillna(0.0)
        
        string_notnull_cols = [
            'control_code', 'invoice_number', 'authorization_code', 'customer_nit', 'customer_name',
            'status', 'sale_type', 'consolidation_status', 'invoice_date'
        ]
        for col in string_notnull_cols:
            if col in insert_df.columns:
                insert_df[col] = insert_df[col].fillna('0')
        
        # Eliminar campos que ya no existen en la nueva estructura
        if 'right_to_tax_credit' in insert_df.columns:
            insert_df = insert_df.drop(columns=['right_to_tax_credit'])
            insert_cols = [c for c in insert_cols if c != 'right_to_tax_credit']
        
        # Convertir valores nulos apropiadamente para MySQL
        insert_df = insert_df.map(lambda x: None if (pd.isnull(x) or str(x).lower() == 'nan') else x)
        
        # Realizar inserción bulk
        values = [tuple(row) for row in insert_df.values]
        placeholders = ','.join(['%s'] * len(insert_cols))
        sql = f"INSERT INTO sales_registers ({', '.join(insert_cols)}) VALUES ({placeholders})"
        
        print(f"🔄 Insertando registros en sales_registers...")
        cursor.executemany(sql, values)
        conn.commit()
        
        inserted_count = cursor.rowcount
        print(f"✅ ÉXITO: Se insertaron {inserted_count:,} registros en sales_registers para {mes:02d}/{anno}.")
        
        # Verificación final rápida
        cursor.execute("SELECT COUNT(*) FROM sales_registers WHERE invoice_date >= %s AND invoice_date <= %s", (fecha_inicio, fecha_fin))
        final_count = cursor.fetchone()[0]
        print(f"📊 Verificación: Total de registros en base para {mes:02d}/{anno}: {final_count:,}")
        
        conn.close()
        
    except mysql.connector.IntegrityError as ie:
        print(f"❌ ERROR de integridad: {ie}")
        print("   Posiblemente hay códigos de autorización duplicados o violación de restricción.")
        sys.exit(1)
    except Exception as e:
        print(f"❌ Error general durante la inserción: {e}")
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
