

# scripts/debug_patrimoine_calculator.py

import logging
import pandas as pd
import sys
from pathlib import Path

# Ajouter le répertoire racine du projet au sys.path
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from backend.analytics.patrimoine_calculator import PatrimoineCalculator

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def main():
    """
    Script de débogage pour valider les calculs de PatrimoineCalculator.
    """
    # Remplacez par votre user_id de test
    user_id = "e8bb01e2-454c-4edb-ba99-f1d2b7dcf4b9" 
    
    logging.info(f"Initialisation de PatrimoineCalculator pour l'utilisateur: {user_id}")
    
    try:
        # Initialiser le calculateur
        calculator = PatrimoineCalculator(user_id)
        
        # --- Validation 1: Afficher les plateformes détectées ---
        logging.info("\n" + "="*20 + " PLATEFORMES DÉTECTÉES " + "="*20)
        platforms = calculator.investments_df['platform'].unique().tolist()
        logging.info(f"Plateformes trouvées: {platforms}")
        
        # --- Validation 2: Calculer et afficher les détails par plateforme ---
        logging.info("\n" + "="*20 + " DÉTAILS PAR PLATEFORME " + "="*20)
        platform_details = calculator.get_platform_details()
        
        for platform, details in platform_details.items():
            logging.info(f"\n--- Plateforme: {platform} ---")
            logging.info(f"  Capital Investi / Encours: {details['capital_investi_encours'][0]:.2f} € / {details['capital_investi_encours'][1]:.2f} €")
            logging.info(f"  Plus-Value Réalisée (Nette): {details['plus_value_realisee_nette']:.2f} €")
            logging.info(f"  TRI Brut / Net: {details['tri_brut']:.2f}% / {details['tri_net']:.2f}%")
            logging.info(f"  Nombre de projets: {details['nombre_projets']}")
        
        # --- Validation 3: Calculer les KPIs globaux ---
        logging.info("\n" + "="*20 + " KPIs GLOBAUX " + "="*20)
        global_kpis = calculator.get_global_kpis()
        logging.info(f"  Patrimoine Total: {global_kpis['patrimoine_total']:.2f} €")
        logging.info(f"  Plus-Value Nette: {global_kpis['plus_value_nette']:.2f} €")
        logging.info(f"  TRI Global Brut / Net: {global_kpis['tri_global_brut']:.2f}% / {global_kpis['tri_global_net']:.2f}%")

    except Exception as e:
        logging.error(f"Une erreur est survenue lors de l'exécution du script de débogage: {e}", exc_info=True)

if __name__ == "__main__":
    main()

