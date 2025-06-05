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
    Muestra dos cuadros comparativos SIAT vs Inventario:
    1. Totales en montos (por sucursal, alquileres, totales)
    2. Totales de número de facturas (válidas y anuladas)
    Cada uno con su respectivo check de conciliación.
    """
    # --- CUADRO 1: TOTALES EN MONTOS ---
    print("\n--- CUADRO COMPARATIVO SIAT vs INVENTARIO (MONTOS) ---\n")
    # Alquileres
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
    sucursales = set(res_siat['sucursales'].keys()) | set(res_inv['sucursales'].keys())
    sucursales = [str(s) for s in sucursales if s not in ('ALQUILERES',)]
    sucursales = sorted(sucursales)
    total_siat = 0
    total_inv = 0
    diferencias = []
    for suc in sucursales:
        t_siat = res_siat['sucursales'].get(suc, {}).get('total', 0)
        t_inv = res_inv['sucursales'].get(suc, {}).get('total', 0)
        diferencia = t_siat - t_inv
        diferencias.append(diferencia)
    total_diferencia = sum(diferencias)
    mostrar_diferencia = any(abs(d) >= 0.01 for d in diferencias) or abs(total_diferencia) >= 0.01
    # Header
    if mostrar_diferencia:
        print(f"{'Sucursal':<12} | {'Total SIAT':>15} | {'Total INV':>15} | {'DIFERENCIA':>12} | {'CONCILIACIÓN':^13}")
    else:
        print(f"{'Sucursal':<12} | {'Total SIAT':>15} | {'Total INV':>15} | {'CONCILIACIÓN':^13}")
    print("-"*(77 if mostrar_diferencia else 61))
    # Rows
    for idx, suc in enumerate(sucursales):
        nom = suc_map.get(suc, suc) if suc_map else suc
        t_siat = res_siat['sucursales'].get(suc, {}).get('total', 0)
        t_inv = res_inv['sucursales'].get(suc, {}).get('total', 0)
        diferencia = t_siat - t_inv
        check = '✔' if abs(diferencia)<0.01 else '❌'
        diferencia_str = f"{diferencia:,.2f}" if abs(diferencia) >= 0.01 else "0.00"
        if mostrar_diferencia:
            print(f"{nom:<12} | {t_siat:>15,.2f} | {t_inv:>15,.2f} | {diferencia_str:>12} |   {check:^11}")
        else:
            print(f"{nom:<12} | {t_siat:>15,.2f} | {t_inv:>15,.2f} |   {check:^11}")
        total_siat += t_siat
        total_inv += t_inv
    print("-"*(77 if mostrar_diferencia else 61))
    total_diferencia = total_siat - total_inv
    check_inv = '✔' if abs(total_diferencia)<0.01 else '❌'
    total_diferencia_str = f"{total_diferencia:,.2f}" if abs(total_diferencia) >= 0.01 else "0.00"
    if mostrar_diferencia:
        print(f"{'TOTAL INV':<12} | {total_siat:>15,.2f} | {total_inv:>15,.2f} | {total_diferencia_str:>12} |   {check_inv:^11}")
    else:
        print(f"{'TOTAL INV':<12} | {total_siat:>15,.2f} | {total_inv:>15,.2f} |   {check_inv:^11}")
    print("-"*(77 if mostrar_diferencia else 61))
    if mostrar_diferencia:
        print(f"{'ALQUILERES':<12} | {alquileres:>15,.2f} | {0:>15,.2f} | {'0.00':>12} |   {'':^11}")
    else:
        print(f"{'ALQUILERES':<12} | {alquileres:>15,.2f} | {0:>15,.2f} |   {'':^11}")
    print("-"*(77 if mostrar_diferencia else 61))
    total_general_siat = total_siat + alquileres
    total_general_inv = total_inv
    total_general_diferencia = total_general_siat - total_general_inv
    total_general_diferencia_str = f"{total_general_diferencia:,.2f}" if abs(total_general_diferencia) >= 0.01 else "0.00"
    if mostrar_diferencia:
        print(f"{'TOTAL GENERAL':<12} | {total_general_siat:>15,.2f} | {total_general_inv:>15,.2f} | {total_general_diferencia_str:>12} |   {'':^11}")
    else:
        print(f"{'TOTAL GENERAL':<12} | {total_general_siat:>15,.2f} | {total_general_inv:>15,.2f} |   {'':^11}")
    print("-"*(77 if mostrar_diferencia else 61))

    # --- CUADRO 2: TOTALES DE NÚMERO DE FACTURAS ---
    print("\n--- CUADRO COMPARATIVO SIAT vs INVENTARIO (CANTIDAD DE FACTURAS) ---\n")
    # Precompute differences for columns
    dif_val_list = []
    dif_anu_list = []
    total_validas_siat = 0
    total_validas_inv = 0
    total_anuladas_siat = 0
    total_anuladas_inv = 0
    for suc in sucursales:
        v_siat = res_siat['sucursales'].get(suc, {}).get('validas', 0)
        v_inv = res_inv['sucursales'].get(suc, {}).get('validas', 0)
        a_siat = res_siat['sucursales'].get(suc, {}).get('anuladas', 0)
        a_inv = res_inv['sucursales'].get(suc, {}).get('anuladas', 0)
        dif_val = v_siat - v_inv
        dif_anu = a_siat - a_inv
        dif_val_list.append(dif_val)
        dif_anu_list.append(dif_anu)
        total_validas_siat += v_siat
        total_validas_inv += v_inv
        total_anuladas_siat += a_siat
        total_anuladas_inv += a_inv
    mostrar_dif_val = any(d != 0 for d in dif_val_list) or (total_validas_siat - total_validas_inv) != 0
    mostrar_dif_anu = any(d != 0 for d in dif_anu_list) or (total_anuladas_siat - total_anuladas_inv) != 0
    # Header
    header = f"{'Sucursal':<12} | {'Validas SIAT':>12} | {'Validas INV':>12}"
    if mostrar_dif_val:
        header += f" | {'DIF VAL':>8}"
    header += f" | {'Anuladas SIAT':>12} | {'Anuladas INV':>12}"
    if mostrar_dif_anu:
        header += f" | {'DIF ANU':>8}"
    header += f" | {'CONCILIACIÓN':^13}"
    print(header)
    ancho = 100
    if not mostrar_dif_val:
        ancho -= 10
    if not mostrar_dif_anu:
        ancho -= 10
    print("-"*ancho)
    # Rows
    for idx, suc in enumerate(sucursales):
        nom = suc_map.get(suc, suc) if suc_map else suc
        v_siat = res_siat['sucursales'].get(suc, {}).get('validas', 0)
        v_inv = res_inv['sucursales'].get(suc, {}).get('validas', 0)
        a_siat = res_siat['sucursales'].get(suc, {}).get('anuladas', 0)
        a_inv = res_inv['sucursales'].get(suc, {}).get('anuladas', 0)
        dif_val = v_siat - v_inv
        dif_anu = a_siat - a_inv
        check = '✔' if (v_siat==v_inv and a_siat==a_inv) else '❌'
        row = f"{nom:<12} | {v_siat:>12} | {v_inv:>12}"
        if mostrar_dif_val:
            row += f" | {dif_val:>8}"
        row += f" | {a_siat:>12} | {a_inv:>12}"
        if mostrar_dif_anu:
            row += f" | {dif_anu:>8}"
        row += f" |   {check:^11}"
        print(row)
    print("-"*ancho)
    dif_val_total = total_validas_siat - total_validas_inv
    dif_anu_total = total_anuladas_siat - total_anuladas_inv
    check_inv = '✔' if (total_validas_siat==total_validas_inv and total_anuladas_siat==total_anuladas_inv) else '❌'
    row = f"{'TOTAL INV':<12} | {total_validas_siat:>12} | {total_validas_inv:>12}"
    if mostrar_dif_val:
        row += f" | {dif_val_total:>8}"
    row += f" | {total_anuladas_siat:>12} | {total_anuladas_inv:>12}"
    if mostrar_dif_anu:
        row += f" | {dif_anu_total:>8}"
    row += f" |   {check_inv:^11}"
    print(row)
    print("-"*ancho)
    row = f"{'ALQUILERES':<12} | {alquileres_validas:>12} | {0:>12}"
    if mostrar_dif_val:
        row += f" | {alquileres_validas:>8}"
    row += f" | {alquileres_anuladas:>12} | {0:>12}"
    if mostrar_dif_anu:
        row += f" | {alquileres_anuladas:>8}"
    row += f" |   {'':^11}"
    print(row)
    print("-"*ancho)
    total_general_validas_siat = total_validas_siat + alquileres_validas
    total_general_validas_inv = total_validas_inv
    total_general_anuladas_siat = total_anuladas_siat + alquileres_anuladas
    total_general_anuladas_inv = total_anuladas_inv
    dif_val_gen = total_general_validas_siat - total_general_validas_inv
    dif_anu_gen = total_general_anuladas_siat - total_general_anuladas_inv
    row = f"{'TOTAL GENERAL':<12} | {total_general_validas_siat:>12} | {total_general_validas_inv:>12}"
    if mostrar_dif_val:
        row += f" | {dif_val_gen:>8}"
    row += f" | {total_general_anuladas_siat:>12} | {total_general_anuladas_inv:>12}"
    if mostrar_dif_anu:
        row += f" | {dif_anu_gen:>8}"
    row += f" |   {'':^11}"
    print(row)
    print("-"*ancho)
