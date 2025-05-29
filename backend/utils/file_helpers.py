import pandas as pd
import os
from datetime import datetime, date
from typing import Union, Dict, Any, List
import re
from dateutil import parser as date_parser

def standardize_date(date_input: Union[str, datetime, pd.Timestamp, date]) -> str:
    """
    Standardiser la date au format YYYY-MM-DD avec gestion robuste des formats
    """
    if pd.isna(date_input) or date_input is None or date_input == '':
        return None
    
    # Si c'est déjà une chaîne au bon format
    if isinstance(date_input, str) and re.match(r'^\d{4}-\d{2}-\d{2}$', date_input):
        return date_input
    
    try:
        # Cas des objets datetime Python
        if isinstance(date_input, (datetime, pd.Timestamp)):
            return date_input.strftime('%Y-%m-%d')
        
        # Cas des objets date Python
        if isinstance(date_input, date):
            return date_input.strftime('%Y-%m-%d')
        
        # Cas des chaînes de caractères
        if isinstance(date_input, str):
            # Nettoyer la chaîne
            date_str = str(date_input).strip()
            
            # Formats spécifiques à tester dans l'ordre
            formats_a_tester = [
                '%d/%m/%Y',      # 25/07/2022
                '%d/%m/%y',      # 25/07/22
                '%Y-%m-%d',      # 2022-07-25
                '%d-%m-%Y',      # 25-07-2022
                '%d.%m.%Y',      # 25.07.2022
                '%Y/%m/%d',      # 2022/07/25
            ]
            
            # Essayer chaque format
            for fmt in formats_a_tester:
                try:
                    parsed_date = datetime.strptime(date_str, fmt)
                    return parsed_date.strftime('%Y-%m-%d')
                except ValueError:
                    continue
            
            # Si les formats spécifiques échouent, utiliser dateutil (plus flexible)
            try:
                parsed_date = date_parser.parse(date_str, dayfirst=True)
                return parsed_date.strftime('%Y-%m-%d')
            except:
                pass
        
        # Cas des nombres (timestamps Excel par exemple)
        if isinstance(date_input, (int, float)):
            try:
                # Timestamp Excel (jours depuis 1900-01-01)
                if 10000 < date_input < 100000:  # Plage raisonnable pour les dates Excel
                    excel_date = datetime(1900, 1, 1) + pd.Timedelta(days=date_input-2)
                    return excel_date.strftime('%Y-%m-%d')
                # Timestamp Unix
                elif date_input > 1000000000:  # Timestamp Unix (secondes depuis 1970)
                    unix_date = datetime.fromtimestamp(date_input)
                    return unix_date.strftime('%Y-%m-%d')
            except:
                pass
    
    except Exception as e:
        print(f"⚠️  Erreur lors de la standardisation de la date '{date_input}': {e}")
    
    return None

def clean_amount(amount: Union[str, float, int]) -> float:
    """
    Nettoyer et convertir un montant en float avec gestion robuste
    """
    if pd.isna(amount) or amount is None or amount == '':
        return 0.0
    
    try:
        # Si c'est déjà un nombre
        if isinstance(amount, (int, float)):
            return float(amount)
        
        # Si c'est une chaîne
        if isinstance(amount, str):
            # Nettoyer la chaîne
            cleaned = str(amount).strip()
            
            # Supprimer symboles monétaires et espaces
            cleaned = re.sub(r'[€$£¥₹\s]', '', cleaned)
            
            # Gérer les parenthèses (montants négatifs)
            if cleaned.startswith('(') and cleaned.endswith(')'):
                cleaned = '-' + cleaned[1:-1]
            
            # Gérer les séparateurs de milliers et décimales
            # Ex: "1,234.56" ou "1 234,56" ou "1.234,56"
            
            # Si virgule comme séparateur décimal (format français)
            if ',' in cleaned and cleaned.count(',') == 1 and cleaned.rfind(',') > cleaned.rfind('.'):
                # Format: 1.234,56 -> 1234.56
                cleaned = cleaned.replace('.', '').replace(',', '.')
            elif ',' in cleaned and '.' not in cleaned:
                # Format: 1234,56 -> 1234.56
                cleaned = cleaned.replace(',', '.')
            elif ',' in cleaned:
                # Format: 1,234.56 -> 1234.56 (garder le point)
                cleaned = cleaned.replace(',', '')
            
            # Supprimer les caractères non numériques restants (sauf - et .)
            cleaned = re.sub(r'[^\d\-\.]', '', cleaned)
            
            # Convertir
            if cleaned and cleaned not in ['-', '.', '-.']:
                return float(cleaned)
    
    except Exception as e:
        print(f"⚠️  Erreur lors du nettoyage du montant '{amount}': {e}")
    
    return 0.0

def safe_get(row: pd.Series, column: Union[str, int], default: Any = None) -> Any:
    """
    Récupérer une valeur de façon sécurisée depuis une Series pandas
    """
    try:
        if isinstance(column, int):
            # Accès par index
            if column < len(row) and column >= 0:
                value = row.iloc[column]
                # Gérer les valeurs NaN pandas
                if pd.isna(value):
                    return default
                return value
            else:
                return default
        else:
            # Accès par nom de colonne
            if column in row.index:
                value = row[column]
                if pd.isna(value):
                    return default
                return value
            else:
                return default
    except Exception as e:
        print(f"⚠️  Erreur lors de l'accès à la colonne '{column}': {e}")
        return default

def validate_required_columns(df: pd.DataFrame, required_columns: List[str], sheet_name: str = "") -> bool:
    """
    Valider que les colonnes requises sont présentes dans le DataFrame
    """
    missing_columns = []
    
    for col in required_columns:
        if isinstance(col, int):
            if col >= len(df.columns):
                missing_columns.append(f"Colonne index {col}")
        else:
            if col not in df.columns:
                missing_columns.append(col)
    
    if missing_columns:
        sheet_info = f" dans l'onglet '{sheet_name}'" if sheet_name else ""
        print(f"⚠️  Colonnes manquantes{sheet_info}: {', '.join(missing_columns)}")
        return False
    
    return True

def detect_header_row(df: pd.DataFrame, expected_headers: List[str] = None) -> int:
    """
    Détecter automatiquement la ligne d'en-tête dans un DataFrame
    """
    for i in range(min(10, len(df))):  # Chercher dans les 10 premières lignes
        row = df.iloc[i]
        
        # Compter les cellules non vides avec du texte
        text_cells = sum(1 for cell in row if isinstance(cell, str) and cell.strip())
        
        # Si on a au moins 3 cellules avec du texte, c'est probablement l'en-tête
        if text_cells >= 3:
            # Si des en-têtes spécifiques sont attendus, vérifier la correspondance
            if expected_headers:
                matches = sum(1 for header in expected_headers 
                            if any(header.lower() in str(cell).lower() 
                                 for cell in row if isinstance(cell, str)))
                if matches >= len(expected_headers) * 0.5:  # Au moins 50% de correspondance
                    return i
            else:
                return i
    
    return 0  # Retourner 0 par défaut

def clean_dataframe(df: pd.DataFrame, skip_rows: int = None) -> pd.DataFrame:
    """
    Nettoyer un DataFrame en supprimant les lignes vides et en détectant les en-têtes
    """
    # Détecter la ligne d'en-tête si pas spécifiée
    if skip_rows is None:
        skip_rows = detect_header_row(df)
    
    # Utiliser la ligne détectée comme en-tête
    if skip_rows > 0:
        df = df.iloc[skip_rows:].reset_index(drop=True)
        # Promouvoir la première ligne comme en-tête si elle contient du texte
        if not df.empty and df.iloc[0].dtype == 'object':
            df.columns = df.iloc[0]
            df = df.iloc[1:].reset_index(drop=True)
    
    # Supprimer les lignes complètement vides
    df = df.dropna(how='all')
    
    # Supprimer les colonnes complètement vides
    df = df.dropna(axis=1, how='all')
    
    return df

def format_currency(amount: float, currency: str = "€") -> str:
    """
    Formater un montant en devise
    """
    if pd.isna(amount) or amount is None:
        return "N/A"
    
    try:
        return f"{amount:,.2f} {currency}".replace(',', ' ')
    except:
        return f"{amount} {currency}"

def format_percentage(rate: float) -> str:
    """
    Formater un taux en pourcentage
    """
    if pd.isna(rate) or rate is None:
        return "N/A"
    
    try:
        return f"{rate:.2f}%"
    except:
        return f"{rate}%"

def validate_file_exists(file_path: str) -> bool:
    """
    Valider qu'un fichier existe et est accessible
    """
    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé: {file_path}")
        return False
    
    if not os.path.isfile(file_path):
        print(f"❌ Le chemin n'est pas un fichier: {file_path}")
        return False
    
    try:
        # Tester l'accès en lecture
        with open(file_path, 'rb') as f:
            f.read(1)
        return True
    except Exception as e:
        print(f"❌ Impossible de lire le fichier {file_path}: {e}")
        return False

# Tests unitaires pour les fonctions utilitaires
if __name__ == "__main__":
    print("🧪 Tests des utilitaires de fichiers...")
    
    # Test standardize_date
    test_dates = [
        "25/07/2022",
        "2022-07-25", 
        "25-07-2022",
        None,
        "",
        datetime(2022, 7, 25)
    ]
    
    print("\nTest standardize_date:")
    for test_date in test_dates:
        result = standardize_date(test_date)
        print(f"  {test_date} -> {result}")
    
    # Test clean_amount
    test_amounts = [
        "1,234.56",
        "1 234,56",
        "€500",
        "1.000,50",
        "(100.00)",
        None,
        500.75
    ]
    
    print("\nTest clean_amount:")
    for test_amount in test_amounts:
        result = clean_amount(test_amount)
        print(f"  {test_amount} -> {result}")
    
    print("\n✅ Tests terminés")