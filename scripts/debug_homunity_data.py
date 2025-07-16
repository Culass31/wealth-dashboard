import pandas as pd
import os
import sys
from datetime import datetime
from dateutil.relativedelta import relativedelta
import re

# Ajouter le rpertoire racine du projet au chemin Python
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.utils.file_helpers import standardize_date, clean_amount, normalize_text

# Chemin du fichier Excel Homunity
HOMUNITY_EXCEL_FILE = "C:/Users/culas/OneDrive/Documents/Finances/Projets/wealth-dashboard/data/raw/Portefeuille Homunity.xlsx"

def normalize_homunity_key(promoter: str, project: str) -> str:
    promoter_clean = str(promoter if pd.notna(promoter) else '').strip().lower()
    project_clean = str(project if pd.notna(project) else '').strip().lower()
    project_clean = project_clean.replace("investissement sur le projet", "").replace("remboursement de projet", "").strip()
    return f"{promoter_clean}|{project_clean}"

def debug_homunity_data():
    print("--- Analyse du fichier Portefeuille Homunity.xlsx ---")
    if not os.path.exists(HOMUNITY_EXCEL_FILE):
        print(f"Fichier non trouvé : {HOMUNITY_EXCEL_FILE}")
        return

    try:
        xls = pd.ExcelFile(HOMUNITY_EXCEL_FILE)
        sheet_names = xls.sheet_names
        print(f"Onglets disponibles : {sheet_names}")

        # --- Analyse de l'onglet 'Projets' ---
        projects_sheet_name = None
        for name in sheet_names:
            if "Projets" in name or "projets" in name:
                projects_sheet_name = name
                break
        
        if projects_sheet_name:
            df_projects = pd.read_excel(xls, sheet_name=projects_sheet_name)
            print(f"\nColonnes de l'onglet '{projects_sheet_name}' : {df_projects.columns.tolist()}")

            # --- Analyse de l'onglet 'Relevé compte' ---
            account_sheet_name = None
            for name in sheet_names:
                if "Relevé compte" in name or "releve compte" in name:
                    account_sheet_name = name
                    break
            
            df_account = pd.DataFrame()
            if account_sheet_name:
                df_account = pd.read_excel(xls, sheet_name=account_sheet_name)
                print(f"\nColonnes de l'onglet '{account_sheet_name}' : {df_account.columns.tolist()}")

            print("\n--- Vérification des dates de souscription et d'investissement ---")
            for index, row in df_projects.iterrows():
                promoter = row.get('Promoteur', '')
                project = row.get('Projet', '')
                signature_date_raw = row.get('Date de souscription')
                expected_end_date_raw = row.get('Date de remb projet')

                if not promoter or not project or "Promoteur" in promoter: # Ignorer les lignes d'en-tête ou vides
                    continue

                signature_date = standardize_date(signature_date_raw)
                expected_end_date = standardize_date(expected_end_date_raw)

                duration_months = None
                if signature_date and expected_end_date:
                    try:
                        start_date = datetime.strptime(signature_date, '%Y-%m-%d')
                        end_date = datetime.strptime(expected_end_date, '%Y-%m-%d')
                        delta = relativedelta(end_date, start_date)
                        duration_months = delta.years * 12 + delta.months
                        if delta.days > 0: # Arrondir au mois supérieur si des jours restants
                            duration_months += 1
                    except Exception as e:
                        print(f"Erreur de calcul de durée pour {promoter} - {project}: {e}")

                print(f"Projet: {promoter} - {project}")
                print(f"  Signature Date (Projets): {signature_date_raw} -> {signature_date}")
                print(f"  Expected End Date (Projets): {expected_end_date_raw} -> {expected_end_date}")
                print(f"  Duration (calculée): {duration_months} mois")

                # Rechercher la date d'investissement dans le relevé de compte
                if not df_account.empty:
                    # Créer une colonne temporaire pour la clé normalisée dans df_account
                    df_account['normalized_key'] = df_account.apply(
                        lambda x: normalize_homunity_key(x.get('Nom du promoteur'), x.get('Message')),
                        axis=1
                    )
                    
                    current_project_lookup_key = normalize_homunity_key(promoter, project)

                    investment_transactions = df_account[
                        (df_account['Type de mouvement'].str.contains('transfert', na=False, case=False)) &
                        (df_account['Message'].str.contains('investissement', na=False, case=False)) &
                        (df_account['normalized_key'] == current_project_lookup_key)
                    ]
                    
                    if not investment_transactions.empty:
                        # Prendre la première date d'investissement trouvée
                        investment_date_from_account = standardize_date(investment_transactions['Date'].min())
                        print(f"  Investment Date (Relevé): {investment_date_from_account}")
                    else:
                        print("  Aucune transaction d'investissement trouvée dans le relevé pour ce projet.")
                print("-" * 30)

        else:
            print("Onglet 'Projets' non trouvé dans le fichier Excel.")

    except Exception as e:
        print(f"Erreur lors de la lecture ou de l'analyse de {HOMUNITY_EXCEL_FILE} : {e}")

if __name__ == "__main__":
    debug_homunity_data()
