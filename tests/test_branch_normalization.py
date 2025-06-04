import pytest
from ventas_plus.branch_normalization import normalize_branch_code

def test_normalize_branch_code_basic():
    assert normalize_branch_code("5") == "5"
    assert normalize_branch_code("05") == "5"
    assert normalize_branch_code("005") == "5"

def test_normalize_branch_code_decimal():
    assert normalize_branch_code("5.0") == "5"
    assert normalize_branch_code("5.00") == "5"
    assert normalize_branch_code(".0") == "0"
    assert normalize_branch_code("0.0") == "0"
    assert normalize_branch_code(".00") == "0"
    assert normalize_branch_code("0.00") == "0"

def test_normalize_branch_code_whitespace():
    assert normalize_branch_code(" 5 ") == "5"
    assert normalize_branch_code(" 5.0 ") == "5"
    assert normalize_branch_code(" .0 ") == "0"

def test_normalize_branch_code_types():
    assert normalize_branch_code(5) == "5"
    assert normalize_branch_code(5.0) == "5"
    assert normalize_branch_code(None) == ""
    import pandas as pd
    import numpy as np
    assert normalize_branch_code(pd.NA) == ""
    assert normalize_branch_code(np.nan) == ""

def test_normalize_branch_code_edge_cases():
    assert normalize_branch_code("") == "0"
    assert normalize_branch_code(".") == "0"
    assert normalize_branch_code("0") == "0"
    assert normalize_branch_code("00") == "0"
