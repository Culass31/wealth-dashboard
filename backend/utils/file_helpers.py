import pandas as pd
import os
from datetime import datetime
from typing import Union, Dict, Any

def standardize_date(date_input: Union[str, datetime, pd.Timestamp]) -> str:
    """Standardize date to YYYY-MM-DD format"""
    if pd.isna(date_input) or date_input is None:
        return None
    
    if isinstance(date_input, str):
        # Try different date formats
        for fmt in ['%d/%m/%Y', '%Y-%m-%d', '%d/%m/%y']:
            try:
                return datetime.strptime(date_input, fmt).strftime('%Y-%m-%d')
            except ValueError:
                continue
    elif isinstance(date_input, (datetime, pd.Timestamp)):
        return date_input.strftime('%Y-%m-%d')
    
    return None

def clean_amount(amount: Union[str, float, int]) -> float:
    """Clean and convert amount to float"""
    if pd.isna(amount) or amount is None:
        return 0.0
    
    if isinstance(amount, str):
        # Remove currency symbols, spaces, and convert comma to dot
        cleaned = amount.replace('€', '').replace(' ', '').replace(',', '.')
        try:
            return float(cleaned)
        except ValueError:
            return 0.0
    
    return float(amount)

def safe_get(row: pd.Series, column: Union[str, int], default: Any = None) -> Any:
    """Safely get value from pandas Series"""
    try:
        if isinstance(column, int):
            return row.iloc[column] if column < len(row) else default
        else:
            return row.get(column, default)
    except:
        return default