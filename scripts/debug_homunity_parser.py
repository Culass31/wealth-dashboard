
# scripts/debug_homunity_parser.py
import sys
import os
import pprint

# Ajouter le répertoire racine du projet au sys.path
# pour permettre les imports relatifs (backend.data.unified_parser)
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from backend.data.unified_parser import UnifiedPortfolioParser

def test_homunity_parser(file_path: str):
    """
    Fonction de test pour le parser Homunity.
    - Initialise le parser.
    - Appelle la méthode de parsing pour Homunity.
    - Affiche les résultats de manière lisible.
    """
    print(f"--- Début du test du parser Homunity pour le fichier : {file_path} ---")

    if not os.path.exists(file_path):
        print(f"ERREUR : Le fichier spécifié n'existe pas : {file_path}")
        return

    # Initialisation du parser avec un UUID utilisateur factice
    parser = UnifiedPortfolioParser(user_id="a1b2c3d4-e5f6-7890-1234-567890abcdef")

    # Appel de la méthode de parsing principale
    try:
        parsed_data = parser.parse_platform(file_path=file_path, platform_name='Homunity')
        
        investments = parsed_data.get("investments", [])
        cash_flows = parsed_data.get("cash_flows", [])

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
            print("\n...Exemples de flux...")
            for flow in cash_flows[:3]: # 3 premiers flux
                pprint.pprint(flow)
            
            if len(cash_flows) > 3:
                print("\n...et les 3 derniers flux...")
                for flow in cash_flows[-3:]: # 3 derniers flux
                    pprint.pprint(flow)

        else:
            print("Aucun flux de trésorerie trouvé.")
            
        # Vérification spécifique de la liaison
        print("\n--- VÉRIFICATION DE LA LIAISON ---")
        linked_flows = [cf for cf in cash_flows if cf.get('investment_id')]
        unlinked_flows = [cf for cf in cash_flows if not cf.get('investment_id')]
        
        print(f"Flux liés à un investissement : {len(linked_flows)}")
        print(f"Flux non liés (dépôts/retraits) : {len(unlinked_flows)}")

        if linked_flows:
            print("\nExemple de flux lié :")
            pprint.pprint(linked_flows[0])


    except Exception as e:
        print(f"\n--- ERREUR CRITIQUE LORS DU PARSING ---")
        import traceback
        traceback.print_exc()

if __name__ == "__main__":
    # Chemin absolu vers le fichier de test
    file_to_test = "C:/Users/culas/OneDrive/Documents/Finances/Projets/wealth-dashboard/data/raw/Portefeuille Homunity.xlsx"
    test_homunity_parser(file_to_test)
