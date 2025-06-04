"""
Funciones específicas para la normalización de códigos de sucursal.
"""

def normalize_branch_code(code):
    """
    Normaliza códigos de sucursal eliminando espacios, ceros a la izquierda y decimales.
    
    Args:
        code: Código de sucursal (string, int o None)
        
    Returns:
        str: Código normalizado
        
    Examples:
        >>> normalize_branch_code("5.0") == normalize_branch_code("5")    # True
        >>> normalize_branch_code(".0") == normalize_branch_code("0")     # True
        >>> normalize_branch_code("05") == normalize_branch_code("5")     # True
        >>> normalize_branch_code("5.00") == normalize_branch_code("5")   # True
        >>> normalize_branch_code(" 5 ") == normalize_branch_code("5")    # True
        >>> normalize_branch_code(5.0) == normalize_branch_code("5")      # True
        >>> normalize_branch_code(None) == ""                            # True
    """
    import pandas as pd
    
    # Handle None and NaN values
    if code is None or (hasattr(pd, 'isna') and pd.isna(code)):
        return ''
        
    # Convert input to string and clean it
    code_str = str(code).strip()
    
    # Handle special cases
    if code_str in ['.0', '0.0', '.00', '0.00']:
        return '0'
    
    try:
        # Remove trailing zeros after decimal point (e.g. 5.00 -> 5.0)
        if '.' in code_str:
            code_str = code_str.rstrip('0').rstrip('.')
            
        # Try converting to float first to handle decimal points
        float_val = float(code_str)
        # Convert to int to remove any decimals if it's a whole number
        if float_val.is_integer():
            return str(int(float_val))
        # If it has meaningful decimals, keep original format
        return code_str
    except (ValueError, TypeError):
        # If not numeric, strip spaces and leading zeros
        normalized = code_str.lstrip('0')
        if not normalized or normalized == '.':
            return '0'
        return normalized
