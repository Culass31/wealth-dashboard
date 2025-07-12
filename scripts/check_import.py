#!/usr/bin/env python3
"""
Script rapide pour diagnostiquer le problème d'import clean_string_operation
"""

import sys
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ajouter de la racine du project au chemin Python
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def quick_diagnosis():
    """Diagnostic rapide du problème"""
    
    logging.info("🔍 DIAGNOSTIC RAPIDE IMPORT PROBLEM")
    logging.info("=" * 45)
    
    # Test 1 : Import direct
    logging.info("1. Test import direct...")
    try:
        sys.path.append(os.path.dirname(__file__))
        from backend.utils.file_helpers import clean_string_operation
        logging.info("   ✅ Import réussi!")
        
        # Test fonction
        result = clean_string_operation(123)
        logging.info(f"   ✅ Test fonction: clean_string_operation(123) = '{result}'")
        
    except ImportError as e:
        logging.error(f"   ❌ Erreur import: {e}")
        
        # Vérifier si file_helpers existe
        file_path = os.path.join(project_root, "backend", "utils", "file_helpers.py")
        if os.path.exists(file_path):
            logging.info(f"   📁 Fichier {file_path} existe")
            
            # Vérifier le contenu
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'def clean_string_operation(' in content:
                logging.info("   ✅ Fonction clean_string_operation trouvée dans le fichier")
            else:
                logging.error("   ❌ Fonction clean_string_operation MANQUE dans le fichier")
                return "FUNCTION_MISSING"
        else:
            logging.error(f"   ❌ Fichier {file_path} introuvable")
            return "FILE_MISSING"
        
        return "IMPORT_ERROR"
    
    except Exception as e:
        logging.error(f"   ❌ Autre erreur: {e}")
        return "OTHER_ERROR"
    
    # Test 2 : Vérifier l'import dans unified_parser
    logging.info("\n2. Vérification import dans unified_parser...")
    try:
        parser_path = os.path.join(project_root, "backend", "data", "unified_parser.py")
        if os.path.exists(parser_path):
            with open(parser_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Chercher les imports
            lines = content.split('\n')
            import_lines = [line for line in lines if 'from backend.utils.file_helpers import' in line]
            
            logging.info(f"   📋 Lignes d'import trouvées:")
            for line in import_lines:
                logging.info(f"      {line.strip()}")
                
                if 'clean_string_operation' in line:
                    logging.info("      ✅ clean_string_operation est importée")
                    return "OK"
            
            logging.error("   ❌ clean_string_operation N'EST PAS dans l'import")
            return "MISSING_IN_IMPORT"
        else:
            logging.error(f"   ❌ Fichier {parser_path} introuvable")
            return "PARSER_FILE_MISSING"
            
    except Exception as e:
        logging.error(f"   ❌ Erreur vérification: {e}")
        return "CHECK_ERROR"

def provide_solution(problem_type):
    """Fournir la solution selon le problème détecté"""
    
    logging.info(f"\n🔧 SOLUTION POUR: {problem_type}")
    logging.info("=" * 45)
    
    if problem_type == "FUNCTION_MISSING":
        logging.info("La fonction clean_string_operation manque dans file_helpers.py")
        logging.info("\n➤ Ajoutez cette fonction à la fin de backend/utils/file_helpers.py:")
        logging.info("""
def clean_string_operation(value: Any, default: str = '') -> str:
    """Nettoyer une valeur pour l'utiliser comme string d'opération"""
    if value is None or pd.isna(value):
        return default
    
    str_value = str(value).strip()
    
    if str_value in ['nan', 'NaN', 'None', '']:
        return default
    
    if str_value.isdigit():
        operation_codes = {
            '1': 'versement',
            '2': 'arbitrage', 
            '3': 'dividende',
            '4': 'frais',
            '5': 'arrêté annuel'
        }
        return operation_codes.get(str_value, f'operation_{str_value}')
    
    return str_value
        """)
    
    elif problem_type == "MISSING_IN_IMPORT":
        logging.info("La fonction existe mais n'est pas importée.")
        logging.info("\n➤ Dans backend/data/unified_parser.py, modifiez la ligne d'import:")
        logging.info("\n# ACTUEL:")
        logging.info("from backend.utils.file_helpers import standardize_date, clean_amount, safe_get")
        logging.info("\n# MODIFIER EN:")
        logging.info("from backend.utils.file_helpers import standardize_date, clean_amount, safe_get, clean_string_operation")
    
    elif problem_type == "OK":
        logging.info("L'import semble correct. Le problème est ailleurs.")
        logging.info("\n➤ Solutions alternatives:")
        logging.info("1. Redémarrer votre environnement Python")
        logging.info("2. Ou remplacer par une solution simple:")
        logging.info("   type_operation = str(type_operation_raw).lower() if type_operation_raw is not None else ''")
    
    else:
        logging.info("Problème non identifié.")
        logging.info("\n➤ Solution de secours:")
        logging.info("Remplacez dans _parse_assurance_vie:")
        logging.info("   type_operation = str(type_operation_raw).lower() if type_operation_raw is not None else ''")

def main():
    """Script principal"""
    try:
        problem_type = quick_diagnosis()
        provide_solution(problem_type)
        
        logging.info(f"\n🎯 ÉTAPES SUIVANTES:")
        logging.info(f"1. Appliquer la solution proposée")
        logging.info(f"2. Relancer: python load_sample_data.py")
        logging.info(f"3. Si problème persiste, utiliser la solution de secours")
        
    except Exception as e:
        logging.error(f"❌ Erreur diagnostic: {e}")
        logging.info("\n🆘 SOLUTION DE SECOURS:")
        logging.info("Dans backend/data/unified_parser.py, méthode _parse_assurance_vie:")
        logging.info("Remplacer:")
        logging.info("   type_operation = clean_string_operation(type_operation_raw).lower()")
        logging.info("Par:")
        logging.info("   type_operation = str(type_operation_raw).lower() if type_operation_raw is not None else ''")

if __name__ == "__main__":
    main()
