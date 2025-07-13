# scripts/debug_pretup_parser.py
import sys
import os
import pprint
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(levelname)s: %(message)s')

# Ajouter le répertoire racine du projet au sys.path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data.unified_parser import UnifiedPortfolioParser

def test_pretup_parser(file_path: str):
    """
    Fonction de test pour le parser PretUp.
    """
    print(f"--- Début du test du parser PretUp pour le fichier : {file_path} ---")

    if not os.path.exists(file_path):
        print(f"ERREUR : Le fichier spécifié n'existe pas : {file_path}")
        return

    parser = UnifiedPortfolioParser(user_id="a1b2c3d4-e5f6-7890-1234-567890abcdef")

    try:
        parsed_data = parser.parse_platform(file_path=file_path, platform_name='PretUp')
        
        investments = parsed_data.get("investments", [])
        cash_flows = parsed_data.get("cash_flows", [])
        liquidity_balances = parsed_data.get("liquidity_balances", [])

        print("\n--- INVESTISSEMENTS ({} trouvés) ---".format(len(investments)))
        if investments:
            pprint.pprint(investments[0]) # Affiche le premier pour la lisibilité
        else:
            print("Aucun investissement trouvé.")

        print("\n--- FLUX DE TRÉSORERIE ({} trouvés) ---".format(len(cash_flows)))
        if cash_flows:
            # Trier les flux par date pour une meilleure lisibilité
            cash_flows.sort(key=lambda x: x.get('transaction_date', ''))
            
            # Afficher quelques flux clés pour vérification
            print("\n...Exemples de flux (5 premiers)... ")
            for flow in cash_flows[:5]: 
                pprint.pprint(flow)
            
            if len(cash_flows) > 5:
                print("\n...et les 5 derniers flux... ")
                for flow in cash_flows[-5:]: 
                    pprint.pprint(flow)

        else:
            print("Aucun flux de trésorerie trouvé.")

        print("\n--- SOLDES DE LIQUIDITÉS ({} trouvés) ---".format(len(liquidity_balances)))
        if liquidity_balances:
            pprint.pprint(liquidity_balances)
        else:
            print("Aucun solde de liquidités trouvé.")

    except Exception as e:
        print(f"\n--- ERREUR CRITIQUE LORS DU PARSING ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Chemin absolu vers le fichier de test PretUp
    file_to_test = "C:/Users/culas/OneDrive/Documents/Finances/Projets/wealth-dashboard/data/raw/Portefeuille PretUp.xlsx"
    test_pretup_parser(file_to_test)
