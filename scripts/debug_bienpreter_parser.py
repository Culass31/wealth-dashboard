

# scripts/debug_bienpreter_parser.py
import sys
import os
import pprint
import logging

# Configuration du logging pour la validation
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Ajouter le répertoire racine du projet au sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data.unified_parser import UnifiedPortfolioParser

def validate_parsed_data(investments: list, cash_flows: list):
    """
    Valide les données parsées pour s'assurer que les colonnes critiques ne sont pas vides.
    """
    print("\n--- VALIDATION DES DONNÉES PARSÉES ---")
    
    inv_required_fields = [
        'capital_repaid', 'remaining_capital', 'investment_date', 
        'signature_date', 'expected_end_date'
    ]
    cf_required_fields = [
        'gross_amount', 'net_amount', 'tax_amount', 
        'capital_amount', 'interest_amount'
    ]

    print("\nValidating Investments...")
    for i, inv in enumerate(investments):
        for field in inv_required_fields:
            if inv.get(field) is None:
                logging.warning(f"Investissement #{i} ({inv.get('project_name')}): champ '{field}' est manquant ou None.")
        
        if inv.get('status') == 'completed' and inv.get('actual_end_date') is None:
            logging.warning(f"Investissement #{i} ({inv.get('project_name')}): statut 'completed' mais 'actual_end_date' est None.")

    print("\nValidating Cash Flows...")
    for i, cf in enumerate(cash_flows):
        if cf.get('flow_type') == 'repayment':
            for field in cf_required_fields:
                if cf.get(field) is None:
                    logging.warning(f"Flux de trésorerie #{i} ({cf.get('transaction_date')}): champ '{field}' est manquant ou None.")

def test_bienpreter_parser(file_path: str):
    """
    Fonction de test pour le parser BienPrêter.
    """
    print(f"--- Début du test du parser BienPrêter pour le fichier : {file_path} ---")

    if not os.path.exists(file_path):
        print(f"ERREUR : Le fichier spécifié n'existe pas : {file_path}")
        return

    parser = UnifiedPortfolioParser(user_id="a1b2c3d4-e5f6-7890-1234-567890abcdef")

    try:
        parsed_data = parser.parse_platform(file_path=file_path, platform_name='BienPrêter')
        
        investments = parsed_data.get("investments", [])
        cash_flows = parsed_data.get("cash_flows", [])

        print("\n--- INVESTISSEMENTS ({} trouvés) ---".format(len(investments)))
        if investments:
            pprint.pprint(investments[0])
            completed_inv = next((inv for inv in investments if inv.get('status') == 'completed'), None)
            if completed_inv:
                print("\nExemple d'investissement complété :\n")
                pprint.pprint(completed_inv)
        else:
            print("Aucun investissement trouvé.")

        print("\n--- FLUX DE TRÉSORERIE ({} trouvés) ---".format(len(cash_flows)))
        if cash_flows:
            cash_flows.sort(key=lambda x: x.get('transaction_date', ''))
            print("\n...Exemples de flux...")
            for flow in cash_flows[:5]:
                pprint.pprint(flow)
            if len(cash_flows) > 5:
                print("\n...et les 5 derniers flux...")
                for flow in cash_flows[-5:]:
                    pprint.pprint(flow)
        else:
            print("Aucun flux de trésorerie trouvé.")
            
        # --- Validation ---
        validate_parsed_data(investments, cash_flows)

    except Exception as e:
        print(f"\n--- ERREUR CRITIQUE LORS DU PARSING ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    file_to_test = "C:/Users/culas/OneDrive/Documents/Finances/Projets/wealth-dashboard/data/raw/Portefeuille BienPreter.xlsx"
    test_bienpreter_parser(file_to_test)

