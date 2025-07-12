# scripts/debug_lpb_parser.py
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
    
    # Champs à vérifier pour les investissements
    inv_required_fields = [
        'capital_repaid', 'remaining_capital', 'investment_date', 
        'signature_date', 'expected_end_date'
        # actual_end_date est optionnel et ne sera validé que pour les projets 'completed'
    ]
    
    # Champs à vérifier pour les flux de trésorerie
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
        # Valider uniquement les flux de remboursement pour la ventilation
        if cf.get('flow_type') == 'repayment':
            for field in cf_required_fields:
                # On tolère 0 mais pas None
                if cf.get(field) is None:
                    logging.warning(f"Flux de trésorerie #{i} ({cf.get('transaction_date')}): champ '{field}' est manquant ou None.")

def test_lpb_parser(file_path: str):
    """
    Fonction de test pour le parser La Première Brique (LPB).
    """
    print(f"--- Début du test du parser LPB pour le fichier : {file_path} ---")

    if not os.path.exists(file_path):
        print(f"ERREUR : Le fichier spécifié n'existe pas : {file_path}")
        return

    parser = UnifiedPortfolioParser(user_id="a1b2c3d4-e5f6-7890-1234-567890abcdef")

    try:
        # Exécuter le parsing pour obtenir les investissements et la map
        # Nous devons appeler _parse_lpb directement pour obtenir investment_map
        # Ou modifier parse_platform pour qu'elle retourne aussi investment_map
        # Pour le dbogage, nous allons appeler _parse_lpb directement
        parsed_data = parser._parse_lpb(file_path=file_path)
        
        investments = parser.investments # Accder directement aux investissements stocks
        cash_flows = parsed_data.get("cash_flows", [])

        print("\n--- INVESTISSEMENTS ({} trouvs) ---".format(len(investments)))
        if investments:
            pprint.pprint(investments[0])
        else:
            print("Aucun investissement trouv.")

        print("\n--- FLUX DE TRSORERIE ({} trouvs) ---".format(len(cash_flows)))
        if cash_flows:
            # Filtrer pour ne montrer que les remboursements pour le dbogage
            repayment_flows = [flow for flow in cash_flows if flow['flow_type'] == 'repayment']
            print(f"\n...Exemples de flux de REMBOURSEMENT ({len(repayment_flows)} trouvs)...")
            for flow in repayment_flows[:5]: # Afficher les 5 premiers remboursements
                pprint.pprint(flow)
        else:
            print("Aucun flux de trsorerie trouv.")
            
        # --- Validation ---
        validate_parsed_data(investments, cash_flows)

    except Exception as e:
        print(f"\n--- ERREUR CRITIQUE LORS DU PARSING ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    file_to_test = "C:/Users/culas/OneDrive/Documents/Finances/Projets/wealth-dashboard/data/raw/Portefeuille LPB.xlsx"
    test_lpb_parser(file_to_test)
