import pandas as pd
import re
from unidecode import unidecode
import os

# Chemin du fichier Excel unique
PRETUP_EXCEL_FILE = "C:/Users/culas/OneDrive/Documents/Finances/Projets/wealth-dashboard/data/raw/Portefeuille PretUp.xlsx"

def clean_amount(amount_str):
    if pd.isna(amount_str) or amount_str == '':
        return 0.0
    try:
        # Convertir en string, remplacer la virgule par un point, supprimer les espaces
        cleaned = str(amount_str).replace(',', '.').replace(' ', '')
        # Supprimer tout sauf chiffres et points
        cleaned = re.sub(r'[^\d.]', '', cleaned)
        return float(cleaned)
    except ValueError:
        return 0.0

def normalize_text(text: str) -> str:
    return unidecode(str(text)).strip().lower().replace(" ", "")

def debug_pretup_data():
    print("--- Analyse du fichier Portefeuille PretUp.xlsx ---")
    if not os.path.exists(PRETUP_EXCEL_FILE):
        print(f"Fichier non trouvé : {PRETUP_EXCEL_FILE}")
        return

    try:
        xls = pd.ExcelFile(PRETUP_EXCEL_FILE)
        sheet_names = xls.sheet_names
        print(f"Onglets disponibles : {sheet_names}")

        # --- Analyse de l'onglet 'Relevé compte' ---
        releve_sheet_name = None
        for name in sheet_names:
            if "Relevé compte" in name or "releve compte" in name or "Relevé" in name or "releve" in name:
                releve_sheet_name = name
                break

        if not releve_sheet_name:
            print("Onglet 'Relevé compte' non trouvé dans le fichier Excel.")
            return

        df_releve = pd.read_excel(xls, sheet_name=releve_sheet_name)
        print(f"\nColonnes de l'onglet '{releve_sheet_name}' : {df_releve.columns.tolist()}")

        # --- Vérification des taxes pour les transactions de remboursement ---
        repayment_transactions = df_releve[
            df_releve['Type'].str.contains('Echéance|Remboursement Anticipé', na=False, regex=True)
        ]

        if not repayment_transactions.empty:
            print("\n--- Vérification des montants de taxes pour les remboursements ---")
            for index, row in repayment_transactions.iterrows():
                libelle = row['Libellé']
                cotisations_sociales = clean_amount(row.get('Retenue à la source (Cotisations sociales)', 0))
                prelevement_forfaitaire = clean_amount(row.get('Retenue à la source (Prélèvement forfaitaire)', 0))
                
                print(f"Libellé: {libelle[:70]}...")
                print(f"  Cotisations sociales: {cotisations_sociales}")
                print(f"  Prélèvement forfaitaire: {prelevement_forfaitaire}")
                print(f"  Total taxes (calculé): {cotisations_sociales + prelevement_forfaitaire}")
        else:
            print("Aucune transaction de remboursement trouvée dans l'onglet Relevé compte.")

        # --- Vérification de la date d'investissement pour les transactions 'Offre' ---
        offre_transactions = df_releve[
            df_releve['Type'].str.contains('Offre', na=False, regex=True)
        ]

        if not offre_transactions.empty:
            print("\n--- Vérification des dates d'investissement pour les transactions 'Offre' ---")
            for index, row in offre_transactions.iterrows():
                libelle = row['Libellé']
                transaction_date = row['Date']
                
                print(f"Libellé: {libelle[:70]}...")
                print(f"  Date de transaction: {transaction_date}")

                if "CLS IMMO-PRESTIGE #3" in libelle:
                    print(f"  >>> CLS IMMO-PRESTIGE #3 - Date d'offre: {transaction_date}")

                # Extraire company_name et project_name du libellé pour former le lookup_key
                match = re.search(r'-\s*(.+?)\s*/\s*(.+?)(?:Part|Prélèvement|$)', libelle)
                if not match:
                    match = re.search(r'(.+?)\s*/\s*(.+)', libelle)
                
                if match:
                    company_name, project_name = match.groups()[0], match.groups()[1]
                    lookup_key_from_releve = normalize_text(company_name) + normalize_text(project_name.strip())
                    print(f"  Lookup Key (Relevé): {lookup_key_from_releve}")
        else:
            print("Aucune transaction 'Offre' trouvée dans l'onglet Relevé compte.")

        # --- Vérification de la présence de CLS IMMO-PRESTIGE #3 dans les onglets Offres ---
        print("\n--- Vérification de la présence de CLS IMMO-PRESTIGE #3 dans les onglets Offres ---")
        offer_sheet_names = {
            'Projet Sains - Offres': 'offres_sains',
            'Procdures - Offres': 'offres_procedures',
            'Perdu - Offres': 'offres_perdus'
        }

        for sheet_display_name, sheet_key in offer_sheet_names.items():
            if sheet_display_name in sheet_names:
                df_offers = pd.read_excel(xls, sheet_name=sheet_display_name)
                project_name_col = None
                for col in df_offers.columns:
                    if 'Nom du Projet' in col or 'Nom du projet' in col:
                        project_name_col = col
                        break
                
                if project_name_col:
                    cls_immo_prestige_in_offers = df_offers[df_offers[project_name_col].str.contains("CLS IMMO-PRESTIGE #3", na=False)]
                    if not cls_immo_prestige_in_offers.empty:
                        company_name_in_offers = cls_immo_prestige_in_offers.iloc[0].get('Entreprise', '')
                        project_name_in_offers = cls_immo_prestige_in_offers.iloc[0].get(project_name_col, '')
                        lookup_key_from_offers = normalize_text(company_name_in_offers) + normalize_text(project_name_in_offers)
                        print(f"  Trouvé dans '{sheet_display_name}': Nom du Projet='{project_name_in_offers}', Entreprise='{company_name_in_offers}', Lookup Key='{lookup_key_from_offers}'")
                    else:
                        print(f"  Non trouvé dans '{sheet_display_name}'.")
                else:
                    print(f"  Colonne 'Nom du Projet' non trouvée dans '{sheet_display_name}'.")
            else:
                print(f"  Onglet '{sheet_display_name}' non trouvé.")

    except Exception as e:
        print(f"Erreur lors de la lecture ou de l'analyse de {PRETUP_EXCEL_FILE} : {e}")

if __name__ == "__main__":
    debug_pretup_data()
