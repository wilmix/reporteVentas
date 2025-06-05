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
