import pandas as pd
import os
from datetime import datetime, date
from typing import Union, Dict, Any, List, Optional
import re
from unidecode import unidecode
from dateutil import parser as date_parser
import logging

def standardize_date(date_input: Union[str, datetime, pd.Timestamp, date]) -> Optional[str]:
    """
    Standardiser la date au format YYYY-MM-DD avec gestion robuste des formats.
    """
    if pd.isna(date_input) or date_input is None or date_input == '':
        return None
    
    if isinstance(date_input, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', date_input):
        return date_input
    
    try:
        if isinstance(date_input, (datetime, pd.Timestamp)):
            return date_input.strftime('%Y-%m-%d')
        if isinstance(date_input, date):
            return date_input.strftime('%Y-%m-%d')
        if isinstance(date_input, str):
            date_str = str(date_input).strip()
            # Utiliser dateutil pour une analyse flexible
            parsed_date = date_parser.parse(date_str, dayfirst=True)
            return parsed_date.strftime('%Y-%m-%d')
    except (ValueError, TypeError, date_parser.ParserError) as e:
        logging.warning(f"Erreur lors de la standardisation de la date '{date_input}': {e}")
    
    return None

def clean_amount(amount: Union[str, float, int]) -> float:
    """
    Nettoie et convertit une chaîne de caractères ou un nombre en float.
    Gère les formats français ("," comme décimal) et les espaces.
    """
    if pd.isna(amount) or amount is None or amount == '':
        return 0.0

    if isinstance(amount, (int, float)):
        return float(amount)
    
    if isinstance(amount, str):
        cleaned = str(amount).strip()
        if not cleaned:
            return 0.0
        
        # Gérer les parenthèses pour les négatifs
        if cleaned.startswith('(') and cleaned.endswith(')'):
            cleaned = '-' + cleaned[1:-1]

        # Supprimer les symboles monétaires
        cleaned = re.sub(r'[€$£¥₹\s]', '', cleaned)
        
        # Remplacer la virgule décimale par un point
        if ',' in cleaned:
            cleaned = cleaned.replace('.', '').replace(',', '.')
            
        try:
            return float(cleaned)
        except (ValueError, TypeError):
            logging.warning(f"Impossible de convertir le montant '{amount}' en float.")
            return 0.0
    
    return 0.0

def clean_string_operation(value: Any, default: str = '') -> str:
    if value is None or pd.isna(value):
        return default
    str_value = str(value).strip()
    return str_value if str_value not in ['nan', 'NaN', 'None', ''] else default

def safe_get(row: Union[Dict, pd.Series], column: str, default: Any = None) -> Any:
    """Accède en toute sécurité à une valeur dans un dictionnaire ou une ligne de DataFrame."""
    try:
        if isinstance(row, dict):
            value = row.get(column, default)
        elif isinstance(row, pd.Series):
            value = row.get(column, default)
        else:
            return default
        
        if pd.isna(value):
            return default
        
        return value
    except Exception as e:
        logging.warning(f"Erreur lors de l'accès à la colonne '{column}': {e}")
        return default

def normalize_text(text: str) -> str:
    """Normalise le texte pour la comparaison : minuscules, sans accents, sans espaces ni caractères spéciaux."""
    if not isinstance(text, str):
        return ""
    # Translitérer les accents (ex: "é" -> "e")
    text = unidecode(text)
    text = text.lower()
    # Supprimer tout ce qui n'est pas alphanumérique
    text = re.sub(r'[^a-z0-9]', '', text)
    return text

def get_column_by_normalized_name(df: pd.DataFrame, normalized_name: str) -> Optional[str]:
    """Trouve le nom de colonne original correspondant à un nom normalisé."""
    for col in df.columns:
        if normalize_text(col) == normalized_name:
            return col
    return None