"""
Módulo para generar y mostrar cuadros comparativos de totales y conteos entre SIAT y sistema de inventarios.
"""
import pandas as pd

def resumen_totales_y_cantidades(df, nombre, campo_importe, campo_estado, campo_sector, campo_sucursal):
    """
    Calcula totales y conteos de facturas válidas, anuladas y alquileres para un DataFrame dado.
    """
    resumen = {}
    # Totales generales
    df_validas = df[df[campo_estado] == 'VALIDA']
    df_anuladas = df[df[campo_estado] == 'ANULADA']
    resumen['total'] = df_validas[campo_importe].sum()
    resumen['validas'] = len(df_validas)
    resumen['anuladas'] = len(df_anuladas)
    resumen['alquileres'] = df[(df[campo_sector] == '02') & (df[campo_estado] == 'VALIDA')][campo_importe].sum()
    # Por sucursal
    sucursales = df[campo_sucursal].unique()
    resumen['sucursales'] = {}
    for suc in sucursales:
        if pd.isna(suc) or suc == '':
            continue
        sub = df[df[campo_sucursal] == suc]
        resumen['sucursales'][suc] = {
            'total': sub[sub[campo_estado] == 'VALIDA'][campo_importe].sum(),
            'validas': len(sub[sub[campo_estado] == 'VALIDA']),
            'anuladas': len(sub[sub[campo_estado] == 'ANULADA'])
        }
    return resumen

def mostrar_cuadro_comparativo_siatsysinv(res_siat, res_inv, suc_map=None, df_siat_original=None):
    """
    Muestra un cuadro comparativo de totales y cantidades SIAT vs Inventario.
    Incluye una fila especial para ALQUILERES (SECTOR 02 en SIAT), y totales ordenados como en el ejemplo del usuario.
    """
    print("\n--- CUADRO COMPARATIVO SIAT vs INVENTARIO ---\n")
    print(f"{'Sucursal':<12} | {'Total SIAT':>15} | {'Total INV':>15} | {'Validas SIAT':>12} | {'Validas INV':>12} | {'Anuladas SIAT':>12} | {'Anuladas INV':>12} | {'CONCILIACIÓN':^13}")
    print("-"*104)
    # --- Fila especial para ALQUILERES (robusto a formato de SECTOR) ---
    if df_siat_original is not None:
        df_alq = df_siat_original[df_siat_original['SECTOR'].astype(str).str.zfill(2) == '02']
        alquileres = df_alq[df_alq['ESTADO'] == 'VALIDA']['IMPORTE TOTAL DE LA VENTA'].sum()
        alquileres_validas = len(df_alq[df_alq['ESTADO'] == 'VALIDA'])
        alquileres_anuladas = len(df_alq[df_alq['ESTADO'] == 'ANULADA'])
    else:
        alquileres = res_siat.get('alquileres', 0)
        alquileres_validas = res_siat.get('alquileres_validas', 0)
        alquileres_anuladas = res_siat.get('alquileres_anuladas', 0)
        if 'ALQUILERES' in res_siat.get('sucursales', {}):
            alq = res_siat['sucursales']['ALQUILERES']
            alquileres = alq.get('total', 0)
            alquileres_validas = alq.get('validas', 0)
            alquileres_anuladas = alq.get('anuladas', 0)
    # --- Sucursales normales (sin ALQUILERES) ---
    sucursales = set(res_siat['sucursales'].keys()) | set(res_inv['sucursales'].keys())
    sucursales = [str(s) for s in sucursales if s not in ('ALQUILERES',)]
    sucursales = sorted(sucursales)
    total_siat = 0
    total_inv = 0
    total_validas_siat = 0
    total_validas_inv = 0
    total_anuladas_siat = 0
    total_anuladas_inv = 0
    for suc in sucursales:
        nom = suc_map.get(suc, suc) if suc_map else suc
        t_siat = res_siat['sucursales'].get(suc, {}).get('total', 0)
        t_inv = res_inv['sucursales'].get(suc, {}).get('total', 0)
        v_siat = res_siat['sucursales'].get(suc, {}).get('validas', 0)
        v_inv = res_inv['sucursales'].get(suc, {}).get('validas', 0)
        a_siat = res_siat['sucursales'].get(suc, {}).get('anuladas', 0)
        a_inv = res_inv['sucursales'].get(suc, {}).get('anuladas', 0)
        # Comparación
        check = '✔' if (abs(t_siat-t_inv)<0.01 and v_siat==v_inv and a_siat==a_inv) else '❌'
        print(f"{nom:<12} | {t_siat:>15,.2f} | {t_inv:>15,.2f} | {v_siat:>12} | {v_inv:>12} | {a_siat:>12} | {a_inv:>12} |   {check:^11}")
        total_siat += t_siat
        total_inv += t_inv
        total_validas_siat += v_siat
        total_validas_inv += v_inv
        total_anuladas_siat += a_siat
        total_anuladas_inv += a_inv
    print("-"*104)
    # Comparación totales inventario
    check_inv = '✔' if (abs(total_siat-total_inv)<0.01 and total_validas_siat==total_validas_inv and total_anuladas_siat==total_anuladas_inv) else '❌'
    print(f"{'TOTAL INV':<12} | {total_siat:>15,.2f} | {total_inv:>15,.2f} | {total_validas_siat:>12} | {total_validas_inv:>12} | {total_anuladas_siat:>12} | {total_anuladas_inv:>12} |   {check_inv:^11}")
    print("-"*104)
    # --- Fila ALQUILERES debajo de totales ---
    print(f"{'ALQUILERES':<12} | {alquileres:>15,.2f} | {0:>15,.2f} | {alquileres_validas:>12} | {0:>12} | {alquileres_anuladas:>12} | {0:>12} |   {'':^11}")
    print("-"*104)
    # --- TOTAL GENERAL (suma de totales + alquileres) ---
    total_general_siat = total_siat + alquileres
    total_general_inv = total_inv  # inventario no suma alquileres
    total_general_validas_siat = total_validas_siat + alquileres_validas
    total_general_validas_inv = total_validas_inv
    total_general_anuladas_siat = total_anuladas_siat + alquileres_anuladas
    total_general_anuladas_inv = total_anuladas_inv
    # No check para TOTAL GENERAL porque nunca serán iguales por el tema de alquileres
    print(f"{'TOTAL GENERAL':<12} | {total_general_siat:>15,.2f} | {total_general_inv:>15,.2f} | {total_general_validas_siat:>12} | {total_general_validas_inv:>12} | {total_general_anuladas_siat:>12} | {total_general_anuladas_inv:>12} |   {'':^11}")
    print("-"*104)
