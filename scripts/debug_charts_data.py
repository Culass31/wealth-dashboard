import sys
import os
import pandas as pd
from pathlib import Path
from datetime import datetime

# Ajouter le répertoire racine du projet au PYTHONPATH
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from backend.analytics.patrimoine_calculator import PatrimoineCalculator

def debug_charts_data():
    print("--- Démarrage du script de débogage des données de graphique ---")
    
    # Charger les variables d'environnement si nécessaire (pour user_id)
    from dotenv import load_dotenv
    load_dotenv()
    user_id = os.getenv("DEFAULT_USER_ID")
    
    if not user_id:
        print("Erreur: DEFAULT_USER_ID non défini dans .env. Veuillez le configurer.")
        return

    try:
        calculator = PatrimoineCalculator(user_id)
        charts_data = calculator.get_charts_data()

        patrimoine_total_evolution = charts_data['evolution_data']['patrimoine_total_evolution']
        benchmark = charts_data['evolution_data']['benchmark']

        print("\n--- Informations sur patrimoine_total_evolution ---")
        print(f"Type: {type(patrimoine_total_evolution)}")
        if patrimoine_total_evolution.empty:
            print("La série patrimoine_total_evolution est vide.")
        else:
            patrimoine_total_evolution.info()
            print("\nHead de patrimoine_total_evolution:")
            print(patrimoine_total_evolution.head())
            print("\nTail de patrimoine_total_evolution:")
            print(patrimoine_total_evolution.tail())
            print(f"Nombre de valeurs NaN dans patrimoine_total_evolution: {patrimoine_total_evolution.isnull().sum()}")
            print(f"Index est DatetimeIndex: {isinstance(patrimoine_total_evolution.index, pd.DatetimeIndex)}")
            print(f"Index a des doublons: {patrimoine_total_evolution.index.duplicated().any()}")
            print(f"Index min: {patrimoine_total_evolution.index.min()}")
            print(f"Index max: {patrimoine_total_evolution.index.max()}")
            first_valid_date = patrimoine_total_evolution.first_valid_index()
            print(f"First valid index: {first_valid_date}")
            if first_valid_date is not None:
                val_at_first_valid = patrimoine_total_evolution.loc[first_valid_date]
                print(f"Value at first valid index: {val_at_first_valid}")
                print(f"Is NaN at first valid index: {pd.isna(val_at_first_valid)}")


        print("\n--- Informations sur benchmark ---")
        print(f"Type: {type(benchmark)}")
        if benchmark.empty:
            print("La série benchmark est vide.")
        else:
            benchmark.info()
            print("\nHead de benchmark:")
            print(benchmark.head())
            print("\nTail de benchmark:")
            print(benchmark.tail())
            print(f"Nombre de valeurs NaN dans benchmark: {benchmark.isnull().sum()}")
            print(f"Index est DatetimeIndex: {isinstance(benchmark.index, pd.DatetimeIndex)}")
            print(f"Index a des doublons: {benchmark.index.duplicated().any()}")
            print(f"Index min: {benchmark.index.min()}")
            print(f"Index max: {benchmark.index.max()}")
            if first_valid_date is not None and first_valid_date in benchmark.index:
                val_at_first_valid_benchmark = benchmark.loc[first_valid_date]
                print(f"Value at first valid index (benchmark): {val_at_first_valid_benchmark}")
                print(f"Is NaN at first valid index (benchmark): {pd.isna(val_at_first_valid_benchmark)}")

    except Exception as e:
        print(f"Une erreur est survenue lors du débogage: {e}")

if __name__ == "__main__":
    debug_charts_data()