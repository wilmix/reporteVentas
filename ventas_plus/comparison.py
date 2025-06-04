"""
Módulo para comparación de facturas SIAT vs Inventario y reporte de discrepancias.
"""

import pandas as pd
from ventas_plus.branch_normalization import normalize_branch_code

def normalize_factura_num(val):
    """
    Normaliza números de factura eliminando espacios, ceros a la izquierda y decimales.
    """
    try:
        if pd.isna(val):
            return ''
            
        # Convertir a string y limpiar espacios
        val_str = str(val).strip()
        
        # Manejar caso especial de .0
        if val_str == '.0':
            return '0'
            
        # Si es un número decimal, convertirlo a entero
        if '.' in val_str:
            num = int(float(val_str))
            return str(num)
            
        # Para números enteros o strings numéricos
        # Quitar ceros a la izquierda
        normalized = val_str.lstrip('0')
        if normalized == '' or normalized == '.':
            return '0'
        return normalized
    except Exception:
        # Si no es numérico, quitar espacios y ceros a la izquierda
        normalized = str(val).strip().lstrip('0')
        if normalized == '' or normalized == '.':
            return '0'
        return normalized

def compare_siat_with_inventory(siat_data, inventory_data):
    """
    Comparar facturas del SIAT con las del sistema de inventarios.
    Args:
        siat_data (DataFrame): Datos de facturas del SIAT
        inventory_data (DataFrame): Datos de facturas del sistema de inventarios
    Returns:
        dict: Resultados de la comparación y DataFrame con detalles
    """
    results = {
        'total_siat': len(siat_data),
        'total_inventory': len(inventory_data),
        'matching_invoices': 0,
        'missing_in_inventory': [],
        'missing_in_siat': [],
        'amount_difference': 0.0,
        'amount_difference_details': [],
        'field_discrepancies': []
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

    # Verificar diferencias en campos específicos para facturas que coinciden
    if len(matching_auths) > 0:
        siat_matching = siat_no_alquileres[siat_no_alquileres['CODIGO DE AUTORIZACIÓN'].isin(matching_auths)]
        inventory_matching = inventory_data[inventory_data['autorizacion'].isin(matching_auths)]
        siat_compare = siat_matching[[
            'CODIGO DE AUTORIZACIÓN',
            'FECHA DE LA FACTURA',
            'Nº DE LA FACTURA',
            'NIT / CI CLIENTE',
            'NOMBRE O RAZON SOCIAL',
            'IMPORTE TOTAL DE LA VENTA',
            'ESTADO',
            'SUCURSAL'
        ]].copy()
        inventory_compare = inventory_matching[[
            'autorizacion',
            'fechaFac',
            'nFactura',
            'nit',
            'razonSocial',
            'importeTotal',
            'estado',
            'codigoSucursal'
        ]].copy()
        siat_compare.rename(columns={
            'CODIGO DE AUTORIZACIÓN': 'autorizacion',
            'FECHA DE LA FACTURA': 'fecha_siat',
            'Nº DE LA FACTURA': 'nfactura_siat',
            'NIT / CI CLIENTE': 'nit_siat',
            'NOMBRE O RAZON SOCIAL': 'razon_social_siat',
            'IMPORTE TOTAL DE LA VENTA': 'importe_siat',
            'ESTADO': 'estado_siat',
            'SUCURSAL': 'sucursal_siat'
        }, inplace=True)
        inventory_compare.rename(columns={
            'fechaFac': 'fecha_inv',
            'nFactura': 'nfactura_inv',
            'nit': 'nit_inv',
            'razonSocial': 'razon_social_inv',
            'importeTotal': 'importe_inv',
            'estado': 'estado_inv',
            'codigoSucursal': 'sucursal_inv'
        }, inplace=True)
        comparison = pd.merge(siat_compare, inventory_compare, on='autorizacion')
        comparison['OBSERVACIONES'] = ''
        comparison['nfactura_siat'] = pd.to_numeric(comparison['nfactura_siat'], errors='coerce')
        comparison['nfactura_inv'] = pd.to_numeric(comparison['nfactura_inv'], errors='coerce')
        comparison['nit_siat'] = comparison['nit_siat'].astype(str).str.strip()
        comparison['nit_inv'] = comparison['nit_inv'].astype(str).str.strip()        # Usando la función importada de branch_normalization.py
        comparison['sucursal_siat_norm'] = comparison['sucursal_siat'].apply(normalize_branch_code)
        comparison['sucursal_inv_norm'] = comparison['sucursal_inv'].apply(normalize_branch_code)
        comparison['estado_inv'] = comparison['estado_inv'].replace({'V': 'VALIDA', 'A': 'ANULADA'})
        for i, row in comparison.iterrows():
            observaciones = []
            if row['fecha_siat'] != row['fecha_inv']:
                observaciones.append(f"Fecha: SIAT={row['fecha_siat']}, INV={row['fecha_inv']}")
            if row['nfactura_siat'] != row['nfactura_inv']:
                observaciones.append(f"Nº Factura: SIAT={row['nfactura_siat']}, INV={row['nfactura_inv']}")
            if row['nit_siat'] != row['nit_inv']:
                observaciones.append(f"NIT: SIAT={row['nit_siat']}, INV={row['nit_inv']}")
            if abs(row['importe_siat'] - row['importe_inv']) > 0.01:
                observaciones.append(f"Importe: SIAT={row['importe_siat']}, INV={row['importe_inv']}")
            if row['estado_siat'] != row['estado_inv']:
                observaciones.append(f"Estado: SIAT={row['estado_siat']}, INV={row['estado_inv']}")
            if row['sucursal_siat_norm'] != row['sucursal_inv_norm']:
                observaciones.append(f"Sucursal: SIAT={row['sucursal_siat']}, INV={row['sucursal_inv']}")
            if observaciones:
                comparison.at[i, 'OBSERVACIONES'] = "; ".join(observaciones)
                results['field_discrepancies'].append({
                    'autorizacion': row['autorizacion'],
                    'observaciones': "; ".join(observaciones)
                })
        comparison['diferencia_importe'] = comparison['importe_siat'] - comparison['importe_inv']
        differences = comparison[abs(comparison['diferencia_importe']) > 0.01]
        if len(differences) > 0:
            results['amount_differences_count'] = len(differences)
            results['amount_difference'] = differences['diferencia_importe'].sum()
            results['amount_difference_details'] = differences.to_dict('records')
        results['comparison_dataframe'] = comparison
    # --- NUEVO: Generar DataFrame de verificación completa ---
    # Unir SIAT con inventario (left join, todas las del SIAT)
    siat_full = siat_data.copy()
    siat_full['autorizacion'] = siat_full['CODIGO DE AUTORIZACIÓN'].astype(str).str.strip()
    inventory_data['autorizacion'] = inventory_data['autorizacion'].astype(str).str.strip()
    merged = pd.merge(
        siat_full,
        inventory_data,
        on='autorizacion',
        how='left',
        suffixes=('_siat', '_inv')
    )
    merged['OBSERVACIONES'] = ''
    # Marcar facturas de alquiler
    merged['OBSERVACIONES'] = merged.apply(
        lambda row: 'Factura de alquiler (SECTOR 02)' if str(row.get('SECTOR', '')) == '02' else '', axis=1)
    # Marcar facturas no encontradas en inventario
    merged['OBSERVACIONES'] = merged.apply(
        lambda row: (row['OBSERVACIONES'] + '; ' if row['OBSERVACIONES'] else '') + 'No existe en inventarios' if pd.isna(row.get('fechaFac')) else row['OBSERVACIONES'], axis=1)
    # Marcar discrepancias en campos (solo si existe en inventario y no es alquiler)
    def check_discrepancias(row):
        if pd.isna(row.get('fechaFac')) or str(row.get('SECTOR', '')) == '02':
            return row['OBSERVACIONES']
        obs = []
        # Normalizar número de factura para comparar como string sin decimales
        nfact_siat = normalize_factura_num(row.get('Nº DE LA FACTURA', None))
        nfact_inv = normalize_factura_num(row.get('nFactura', None))
        if nfact_siat != nfact_inv:
            obs.append(f"Nº Factura: SIAT={nfact_siat}, INV={nfact_inv}")
        # Normalizar sucursal para comparar (sin decimales, sin ceros a la izquierda)
        suc_siat = normalize_branch_code(row.get('SUCURSAL', ''))
        suc_inv = normalize_branch_code(row.get('codigoSucursal', ''))
        if suc_siat != suc_inv:
            obs.append(f"Sucursal: SIAT={suc_siat}, INV={suc_inv}")
        # Comparar fecha
        if str(row.get('FECHA DE LA FACTURA', '')) != str(row.get('fechaFac', '')):
            obs.append(f"Fecha: SIAT={row.get('FECHA DE LA FACTURA','')}, INV={row.get('fechaFac','')}")
        # Comparar NIT
        if str(row.get('NIT / CI CLIENTE', '')).strip() != str(row.get('nit', '')).strip():
            obs.append(f"NIT: SIAT={row.get('NIT / CI CLIENTE','')}, INV={row.get('nit','')}")
        # Comparar importe
        siat_importe = pd.to_numeric(row.get('IMPORTE TOTAL DE LA VENTA', 0), errors='coerce')
        inv_importe = pd.to_numeric(row.get('importeTotal', 0), errors='coerce')
        if abs(siat_importe - inv_importe) > 0.01:
            obs.append(f"Importe: SIAT={siat_importe}, INV={inv_importe}")
        # Comparar estado
        siat_estado = str(row.get('ESTADO', ''))
        inv_estado = str(row.get('estado', ''))
        if inv_estado in ['V', 'A']:
            inv_estado = 'VALIDA' if inv_estado == 'V' else 'ANULADA'
        if siat_estado != inv_estado:
            obs.append(f"Estado: SIAT={siat_estado}, INV={inv_estado}")
        if obs:
            return (row['OBSERVACIONES'] + '; ' if row['OBSERVACIONES'] else '') + '; '.join(obs)
        return row['OBSERVACIONES']
    merged['OBSERVACIONES'] = merged.apply(check_discrepancias, axis=1)
    results['verificacion_completa'] = merged
    return results
