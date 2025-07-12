#!/usr/bin/env python3
"""
Diagnostic rapide des contraintes de base de données
"""

import sys
import os
import logging

# Ajouter de la racine du project au chemin Python
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.models.database import DatabaseManager

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def check_flow_types():
    """Vérifier quels flow_types sont autorisés"""
    
    db = DatabaseManager()
    
    logging.info("🔍 TEST DES FLOW_TYPES AUTORISÉS")
    logging.info("=" * 40)
    
    # Flow types à tester
    test_types = [
        'deposit', 'withdrawal', 'investment', 'repayment', 
        'interest', 'dividend', 'fee', 'sale', 'purchase', 
        'adjustment', 'other', 'bonus', 'cancellation'
    ]
    
    valid_types = []
    invalid_types = []
    
    for flow_type in test_types:
        try:
            # Test d'insertion minimal
            test_flow = {
                'id': f'test-{flow_type}',
                'user_id': '29dec51d-0772-4e3a-8e8f-1fece8fefe0e',
                'platform': 'Test',
                'flow_type': flow_type,
                'flow_direction': 'in',
                'gross_amount': 100.0,
                'net_amount': 100.0,
                'transaction_date': '2024-01-01',
                'status': 'completed',
                'description': f'Test {flow_type}'
            }
            
            # Tenter l'insertion
            result = db.supabase.table('cash_flows').insert(test_flow).execute()
            
            if result.data:
                # Supprimer immédiatement le test
                db.supabase.table('cash_flows').delete().eq('id', f'test-{flow_type}').execute()
                valid_types.append(flow_type)
                logging.info(f"✅ {flow_type}")
            else:
                invalid_types.append(flow_type)
                logging.error(f"❌ {flow_type}")
                
        except Exception as e:
            invalid_types.append(flow_type)
            error_msg = str(e)
            if 'chk_flow_type' in error_msg:
                logging.error(f"❌ {flow_type} - CONTRAINTE CHECK")
            else:
                logging.error(f"❌ {flow_type} - {error_msg[:50]}...")
    
    logging.info(f"\n📊 RÉSULTATS:")
    logging.info(f"✅ Types valides: {', '.join(valid_types)}")
    logging.info(f"❌ Types invalides: {', '.join(invalid_types)}")
    
    return valid_types, invalid_types

def check_integer_fields():
    """Vérifier les champs INTEGER"""
    
    db = DatabaseManager()
    
    logging.info("\n🔢 TEST DES CHAMPS INTEGER")
    logging.info("=" * 40)
    
    try:
        # Test avec duration_months FLOAT
        test_investment = {
            'id': 'test-duration',
            'user_id': '29dec51d-0772-4e3a-8e8f-1fece8fefe0e',
            'platform': 'Test',
            'investment_type': 'test',
            'project_name': 'Test Duration',
            'invested_amount': 1000.0,
            'duration_months': 42.5,  # FLOAT
            'investment_date': '2024-01-01',
            'status': 'active'
        }
        
        result = db.supabase.table('investments').insert(test_investment).execute()
        
        if result.data:
            db.supabase.table('investments').delete().eq('id', 'test-duration').execute()
            logging.info("✅ duration_months accepte les FLOAT")
        else:
            logging.error("❌ duration_months rejette les FLOAT")
            
    except Exception as e:
        if '22P02' in str(e):
            logging.error("❌ duration_months DOIT être INTEGER")
            logging.info("   💡 Solution: utiliser round() sans décimales")
        else:
            logging.error(f"❌ Erreur: {str(e)[:100]}")

def main():
    logging.info("🧪 DIAGNOSTIC CONTRAINTES BASE DE DONNÉES")
    logging.info("=" * 50)
    
    try:
        # Test connexion
        db = DatabaseManager()
        if not db.test_connection():
            logging.error("❌ Impossible de se connecter à la BDD")
            return
        
        logging.info("✅ Connexion BDD OK\n")
        
        # Tests
        valid_flow_types, invalid_flow_types = check_flow_types()
        check_integer_fields()
        
        # Recommandations
        logging.info("\n💡 RECOMMANDATIONS:")
        
        if 'withdrawal' in invalid_flow_types:
            logging.info("1. Remplacer 'withdrawal' par 'adjustment' dans le parser")
        
        if 'cancellation' in invalid_flow_types:
            logging.info("2. Remplacer 'cancellation' par 'adjustment' dans le parser")
        
        logging.info("3. Convertir duration_months en INTEGER avec round()")
        
        # Mapping recommandé
        if invalid_flow_types:
            logging.info(f"\n🔧 MAPPING FLOW_TYPES RECOMMANDÉ:")
            mapping = {
                'withdrawal': 'adjustment',
                'cancellation': 'adjustment',
                'bonus': 'interest',
                'cashback': 'interest'
            }
            
            for invalid, valid in mapping.items():
                if invalid in invalid_flow_types and valid in valid_flow_types:
                    logging.info(f"   {invalid} → {valid}")
        
    except Exception as e:
        logging.error(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()
