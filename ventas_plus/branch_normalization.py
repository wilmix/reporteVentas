"""
Funciones específicas para la normalización de códigos de sucursal.
"""

def normalize_branch_code(code):
    """
    Normaliza códigos de sucursal eliminando espacios y ceros a la izquierda.
    
    Args:
        code: Código de sucursal (string, int o None)
        
    Returns:
        str: Código normalizado
    """
    if code is None or pd.isna(code):
        return ''
        
    # Convertir a string, quitar espacios, quitar ceros a la izquierda
    normalized = str(code).strip().lstrip('0')
    
    # Si quedó vacío después de quitar los ceros, era un "0" o "00", etc.
    if normalized == '':
        return '0'
        
    return normalized
