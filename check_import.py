#!/usr/bin/env python3
"""
Script rapide pour diagnostiquer le problème d'import clean_string_operation
"""

import sys
import os

def quick_diagnosis():
    """Diagnostic rapide du problème"""
    
    print("🔍 DIAGNOSTIC RAPIDE IMPORT PROBLEM")
    print("=" * 45)
    
    # Test 1 : Import direct
    print("1. Test import direct...")
    try:
        sys.path.append(os.path.dirname(__file__))
        from backend.utils.file_helpers import clean_string_operation
        print("   ✅ Import réussi!")
        
        # Test fonction
        result = clean_string_operation(123)
        print(f"   ✅ Test fonction: clean_string_operation(123) = '{result}'")
        
    except ImportError as e:
        print(f"   ❌ Erreur import: {e}")
        
        # Vérifier si file_helpers existe
        file_path = "backend/utils/file_helpers.py"
        if os.path.exists(file_path):
            print(f"   📁 Fichier {file_path} existe")
            
            # Vérifier le contenu
            with open(file_path, 'r', encoding='utf-8') as f:
                content = f.read()
                
            if 'def clean_string_operation(' in content:
                print("   ✅ Fonction clean_string_operation trouvée dans le fichier")
            else:
                print("   ❌ Fonction clean_string_operation MANQUE dans le fichier")
                return "FUNCTION_MISSING"
        else:
            print(f"   ❌ Fichier {file_path} introuvable")
            return "FILE_MISSING"
        
        return "IMPORT_ERROR"
    
    except Exception as e:
        print(f"   ❌ Autre erreur: {e}")
        return "OTHER_ERROR"
    
    # Test 2 : Vérifier l'import dans unified_parser
    print("\n2. Vérification import dans unified_parser...")
    try:
        parser_path = "backend/data/unified_parser.py"
        if os.path.exists(parser_path):
            with open(parser_path, 'r', encoding='utf-8') as f:
                content = f.read()
            
            # Chercher les imports
            lines = content.split('\n')
            import_lines = [line for line in lines if 'from backend.utils.file_helpers import' in line]
            
            print(f"   📋 Lignes d'import trouvées:")
            for line in import_lines:
                print(f"      {line.strip()}")
                
                if 'clean_string_operation' in line:
                    print("      ✅ clean_string_operation est importée")
                    return "OK"
            
            print("   ❌ clean_string_operation N'EST PAS dans l'import")
            return "MISSING_IN_IMPORT"
        else:
            print(f"   ❌ Fichier {parser_path} introuvable")
            return "PARSER_FILE_MISSING"
            
    except Exception as e:
        print(f"   ❌ Erreur vérification: {e}")
        return "CHECK_ERROR"

def provide_solution(problem_type):
    """Fournir la solution selon le problème détecté"""
    
    print(f"\n🔧 SOLUTION POUR: {problem_type}")
    print("=" * 45)
    
    if problem_type == "FUNCTION_MISSING":
        print("La fonction clean_string_operation manque dans file_helpers.py")
        print("\n➤ Ajoutez cette fonction à la fin de backend/utils/file_helpers.py:")
        print("""
def clean_string_operation(value: Any, default: str = '') -> str:
    \"\"\"Nettoyer une valeur pour l'utiliser comme string d'opération\"\"\"
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
        print("La fonction existe mais n'est pas importée.")
        print("\n➤ Dans backend/data/unified_parser.py, modifiez la ligne d'import:")
        print("\n# ACTUEL:")
        print("from backend.utils.file_helpers import standardize_date, clean_amount, safe_get")
        print("\n# MODIFIER EN:")
        print("from backend.utils.file_helpers import standardize_date, clean_amount, safe_get, clean_string_operation")
    
    elif problem_type == "OK":
        print("L'import semble correct. Le problème est ailleurs.")
        print("\n➤ Solutions alternatives:")
        print("1. Redémarrer votre environnement Python")
        print("2. Ou remplacer par une solution simple:")
        print("   type_operation = str(type_operation_raw).lower() if type_operation_raw is not None else ''")
    
    else:
        print("Problème non identifié.")
        print("\n➤ Solution de secours:")
        print("Remplacez dans _parse_assurance_vie:")
        print("   type_operation = str(type_operation_raw).lower() if type_operation_raw is not None else ''")

def main():
    """Script principal"""
    try:
        problem_type = quick_diagnosis()
        provide_solution(problem_type)
        
        print(f"\n🎯 ÉTAPES SUIVANTES:")
        print(f"1. Appliquer la solution proposée")
        print(f"2. Relancer: python load_sample_data.py")
        print(f"3. Si problème persiste, utiliser la solution de secours")
        
    except Exception as e:
        print(f"❌ Erreur diagnostic: {e}")
        print("\n🆘 SOLUTION DE SECOURS:")
        print("Dans backend/data/unified_parser.py, méthode _parse_assurance_vie:")
        print("Remplacer:")
        print("   type_operation = clean_string_operation(type_operation_raw).lower()")
        print("Par:")
        print("   type_operation = str(type_operation_raw).lower() if type_operation_raw is not None else ''")

if __name__ == "__main__":
    main()