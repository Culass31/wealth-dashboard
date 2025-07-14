import pandas as pd
import os

file_path = "C:/Users/culas/OneDrive/Documents/Finances/Projets/wealth-dashboard/data/raw/Portefeuille PretUp.xlsx"
sheet_name = "Relevé compte"

if not os.path.exists(file_path):
    print(f"Erreur: Le fichier {file_path} n'existe pas.")
else:
    try:
        df = pd.read_excel(file_path, sheet_name=sheet_name)
        print("--- Noms des colonnes ---")
        print(df.columns.tolist())
        print("\n--- Premières 5 lignes ---")
        print(df.head().to_dict(orient='records'))
    except Exception as e:
        print(f"Erreur lors de la lecture du fichier Excel: {e}")
