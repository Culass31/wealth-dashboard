import os
import sys
import logging

# Configuration du logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.DEBUG)

# Ajouter de la racine du project au chemin Python
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.data.unified_parser import UnifiedPortfolioParser # Correction: unified_parser au lieu de unified_parser_bug

def test_pea_parsing():
    """Test spécifique du parsing PEA pour le débogage"""
    logging.info("🧪 Test du parsing PEA...")
    
    # Chercher fichiers de test
    test_files = {'releve': None, 'evaluation': None}
    
    pea_dir = os.path.join(project_root, 'data', 'raw', 'pea')
    if os.path.isdir(pea_dir):
        for file in os.listdir(pea_dir):
            if file.lower().endswith('.pdf'):
                if 'releve' in file.lower():
                    test_files['releve'] = os.path.join(pea_dir, file)
                elif 'evaluation' in file.lower() or 'portefeuille' in file.lower():
                    test_files['evaluation'] = os.path.join(pea_dir, file)
    
    logging.info(f"📂 Fichiers de test :")
    for key, file in test_files.items():
        logging.info(f"  {key} : {file or 'Non trouvé'}")
    
    if not any(test_files.values()):
        logging.error("❌ Aucun fichier PEA trouvé pour les tests")
        return False
    
    try:
        # Test parsing
        parser = UnifiedPortfolioParser("test-user")
        # Correction: _parse_pea retourne un dictionnaire, pas deux listes
        parsed_data = parser.parse_platform(file_path=test_files['releve'], platform='pea')
        cash_flows = parsed_data.get("cash_flows", [])
        positions = parsed_data.get("portfolio_positions", [])
        
        logging.info(f"📊 Résultats du test :")
        logging.info(f"  Flux de trésorerie : {len(cash_flows)}")
        logging.info(f"  Positions de portefeuille : {len(positions)}")
        
        # Afficher échantillon
        if cash_flows:
            logging.info(f"\n💰 Échantillon de flux de trésorerie :")
            for i, cf in enumerate(cash_flows[:3]):
                logging.info(f"  {i+1}. {cf.get('transaction_date')} - {cf.get('flow_type')} - {cf.get('gross_amount')}€")
        
        if positions:
            logging.info(f"\n📊 Échantillon de positions :")
            for i, pos in enumerate(positions[:3]):
                logging.info(f"  {i+1}. {pos.get('isin')} - {pos.get('asset_name')[:30]}... - {pos.get('market_value')}€")
        
        logging.info("✅ Test du parsing PEA réussi")
        return True
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du test de parsing PEA : {e}", exc_info=True)
        return False

if __name__ == "__main__":
    test_pea_parsing()
