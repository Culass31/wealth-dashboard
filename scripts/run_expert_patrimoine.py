# ===== run_expert_patrimoine.py - SCRIPT PRINCIPAL EXPERT =====
"""
Script principal pour lancer l'application Expert Patrimoine
Coordonne le chargement des données et le lancement du dashboard

Usage:
    python run_expert_patrimoine.py [options]
    
Options:
    --user-id: ID utilisateur (défaut: 29dec51d-0772-4e3a-8e8f-1fece8fefe0e)
    --data-folder: Dossier des données (défaut: data/raw)
    --load-data: Charger les données avant lancement
    --dashboard-only: Lancer uniquement le dashboard
    --expert-only: Lancer uniquement le dashboard expert
    --validate-only: Valider uniquement les fichiers
    --port: Port pour Streamlit (défaut: 8501)
"""

import argparse
import subprocess
import sys
import os
from pathlib import Path
import time

# Ajouter le répertoire racine au path
sys.path.append(str(Path(__file__).parent))

def setup_environment():
    """Configuration de l'environnement"""
    print("🔧 Configuration de l'environnement...")
    
    # Vérifier Python >= 3.8
    if sys.version_info < (3, 8):
        print("❌ Python 3.8+ requis")
        sys.exit(1)
    
    # Vérifier présence .env
    env_file = Path(".env")
    if not env_file.exists():
        print("⚠️  Fichier .env non trouvé")
        print("Créez un fichier .env avec:")
        print("SUPABASE_URL=your_supabase_url")
        print("SUPABASE_KEY=your_supabase_key")
        response = input("Continuer sans .env ? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Créer dossiers nécessaires
    directories = ['data/raw', 'data/raw/pea', 'logs', 'exports']
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
    
    print("✅ Environnement configuré")

def validate_data_files(data_folder: str) -> bool:
    """Valider les fichiers de données"""
    print(f"🔍 Validation des fichiers dans {data_folder}...")
    
    try:
        from backend.data.data_loader import DataLoader
        
        loader = DataLoader()
        validation_report = loader.validate_all_files(data_folder)
        
        valid_count = validation_report['valid_count']
        total_count = validation_report['total_files']
        
        print(f"📊 Résultats validation: {valid_count}/{total_count} fichiers valides")
        
        if valid_count == 0:
            print("❌ Aucun fichier valide trouvé")
            print("Vérifiez que vos fichiers Excel sont dans le dossier:", data_folder)
            return False
        elif valid_count < total_count:
            print(f"⚠️  {total_count - valid_count} fichier(s) manquant(s)")
            missing = validation_report['missing_files']
            for file_info in missing:
                print(f"  - {file_info['platform']}: {file_info['filename']}")
        
        print("✅ Validation terminée")
        return True
        
    except Exception as e:
        print(f"❌ Erreur validation: {e}")
        return False

def load_user_data(user_id: str, data_folder: str) -> bool:
    """Charger les données utilisateur"""
    print(f"📥 Chargement des données pour {user_id}...")
    
    try:
        from backend.data.data_loader import load_user_data_auto
        
        success = load_user_data_auto(user_id, data_folder)
        
        if success:
            print("✅ Données chargées avec succès")
        else:
            print("❌ Échec du chargement")
        
        return success
        
    except Exception as e:
        print(f"❌ Erreur chargement: {e}")
        import traceback
        traceback.print_exc()
        return False

def test_database_connection() -> bool:
    """Tester la connexion à la base de données"""
    print("🔌 Test de la connexion base de données...")
    
    try:
        from backend.models.database import ExpertDatabaseManager
        
        db = ExpertDatabaseManager()
        if db.test_connection():
            print("✅ Connexion BDD réussie")
            return True
        else:
            print("❌ Échec connexion BDD")
            return False
            
    except Exception as e:
        print(f"❌ Erreur connexion BDD: {e}")
        return False

def run_dashboard(dashboard_type: str = "expert", port: int = 8501):
    """Lancer le dashboard Streamlit"""
    
    dashboard_files = {
        "expert": "frontend/expert_dashboard.py",
        "standard": "frontend/app.py",
    }
    
    dashboard_file = dashboard_files.get(dashboard_type, dashboard_files["expert"])
    
    if not os.path.exists(dashboard_file):
        print(f"❌ Fichier dashboard non trouvé: {dashboard_file}")
        return False
    
    print(f"🚀 Lancement dashboard {dashboard_type} sur port {port}...")
    print(f"📱 URL: http://localhost:{port}")
    print("🛑 Ctrl+C pour arrêter")
    
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", dashboard_file,
            "--server.port", str(port),
            "--server.address", "localhost",
            "--server.headless", "true"
        ])
    except KeyboardInterrupt:
        print("\n👋 Dashboard arrêté")
        return True
    except Exception as e:
        print(f"❌ Erreur lancement dashboard: {e}")
        return False

def run_analysis_only(user_id: str) -> bool:
    """Exécuter uniquement les analyses sans dashboard"""
    print(f"📊 Analyse des données pour {user_id}...")
    
    try:
        from backend.models.database import ExpertDatabaseManager
        from backend.analytics.expert_metrics import ExpertPatrimoineCalculator
        
        # Charger données
        db = ExpertDatabaseManager()
        calculator = ExpertPatrimoineCalculator()
        
        investissements_df = db.get_user_investments(user_id)
        flux_tresorerie_df = db.get_user_cash_flows(user_id)
        
        if investissements_df.empty:
            print("❌ Aucune donnée trouvée")
            return False
        
        print(f"📈 Données trouvées:")
        print(f"  - Investissements: {len(investissements_df)}")
        print(f"  - Flux de trésorerie: {len(flux_tresorerie_df)}")
        
        # Générer rapport expert
        print("🧮 Calcul des métriques expertes...")
        rapport_expert = calculator.generate_expert_report(investissements_df, flux_tresorerie_df)
        
        # Afficher résumé
        if 'tri_expert' in rapport_expert:
            print("\n🎯 TRI par plateforme:")
            for platform, data in rapport_expert['tri_expert'].items():
                tri = data.get('tri_annuel', 0)
                print(f"  {platform}: {tri:.2f}%")
        
        if 'capital_en_cours' in rapport_expert:
            print("\n💰 Capital en cours:")
            total_capital = sum(data.get('capital_en_cours', 0) for data in rapport_expert['capital_en_cours'].values())
            print(f"  Total: {total_capital:,.0f} €")
        
        if 'recommandations' in rapport_expert:
            print("\n💡 Recommandations:")
            for rec in rapport_expert['recommandations'][:3]:  # Top 3
                print(f"  {rec}")
        
        print("\n✅ Analyse terminée")
        return True
        
    except Exception as e:
        print(f"❌ Erreur analyse: {e}")
        import traceback
        traceback.print_exc()
        return False

def show_help():
    """Afficher l'aide complète"""
    print("""
💎 EXPERT PATRIMOINE - Guide d'utilisation

🚀 DÉMARRAGE RAPIDE:
   python run_expert_patrimoine.py --load-data --expert-only

📋 COMMANDES PRINCIPALES:

1. CHARGEMENT INITIAL:
   python run_expert_patrimoine.py --validate-only
   python run_expert_patrimoine.py --load-data

2. LANCEMENT DASHBOARDS:
   python run_expert_patrimoine.py --expert-only      # Dashboard expert
   python run_expert_patrimoine.py --dashboard-only   # Dashboard standard
   
3. ANALYSE SEULE:
   python run_expert_patrimoine.py --analysis-only

🔧 OPTIONS:
   --user-id USER_ID           ID utilisateur (défaut: auto)
   --data-folder FOLDER        Dossier données (défaut: data/raw)
   --port PORT                 Port Streamlit (défaut: 8501)
   --load-data                 Charger données avant dashboard
   --validate-only             Valider fichiers uniquement
   --analysis-only             Analyses sans interface
   
📁 STRUCTURE FICHIERS ATTENDUS:
   data/raw/
   ├── Portefeuille LPB.xlsx
   ├── Portefeuille PretUp.xlsx  
   ├── Portefeuille BienPreter.xlsx
   ├── Portefeuille Homunity.xlsx
   ├── Portefeuille Linxea.xlsx
   └── pea/
       ├── releve_pea.pdf
       └── evaluation_pea.pdf

🔑 CONFIGURATION:
   Créez un fichier .env avec:
   SUPABASE_URL=your_supabase_url
   SUPABASE_KEY=your_supabase_key

💡 MÉTRIQUES CALCULÉES:
   ✅ TRI par plateforme (dates réelles)
   ✅ Capital en cours vs remboursé  
   ✅ Taux de réinvestissement
   ✅ Duration et immobilisation
   ✅ Concentration par émetteur
   ✅ Stress test portefeuille
   ✅ Performance vs benchmarks
   
📧 Support: Consultez la documentation dans /docs/
""")

def main():
    """Fonction principale"""
    parser = argparse.ArgumentParser(description="Expert Patrimoine - Analyse avancée de portefeuille")
    
    parser.add_argument("--user-id", default="29dec51d-0772-4e3a-8e8f-1fece8fefe0e", 
                       help="ID utilisateur")
    parser.add_argument("--data-folder", default="data/raw", 
                       help="Dossier contenant les fichiers de données")
    parser.add_argument("--port", type=int, default=8501, 
                       help="Port pour Streamlit")
    
    # Actions
    parser.add_argument("--load-data", action="store_true", 
                       help="Charger les données avant lancement")
    parser.add_argument("--validate-only", action="store_true", 
                       help="Valider uniquement les fichiers")
    parser.add_argument("--dashboard-only", action="store_true", 
                       help="Lancer uniquement le dashboard standard")
    parser.add_argument("--expert-only", action="store_true", 
                       help="Lancer uniquement le dashboard expert")
    parser.add_argument("--analysis-only", action="store_true", 
                       help="Exécuter uniquement les analyses")
    parser.add_argument("--help-full", action="store_true", 
                       help="Afficher l'aide complète")
    
    args = parser.parse_args()
    
    # Affichage aide complète
    if args.help_full:
        show_help()
        return
    
    # Header
    print("=" * 60)
    print("💎 EXPERT PATRIMOINE - Analyse Avancée de Portefeuille")
    print("=" * 60)
    
    # Configuration environnement
    setup_environment()
    
    # Test connexion BDD
    if not test_database_connection():
        print("⚠️  Continuer sans BDD peut limiter les fonctionnalités")
        response = input("Continuer ? (y/N): ")
        if response.lower() != 'y':
            sys.exit(1)
    
    # Actions selon arguments
    if args.validate_only:
        success = validate_data_files(args.data_folder)
        sys.exit(0 if success else 1)
    
    if args.analysis_only:
        success = run_analysis_only(args.user_id)
        sys.exit(0 if success else 1)
    
    # Chargement données si demandé
    if args.load_data:
        if not validate_data_files(args.data_folder):
            print("⚠️  Validation échouée, continuer le chargement ?")
            response = input("Continuer ? (y/N): ")
            if response.lower() != 'y':
                sys.exit(1)
        
        if not load_user_data(args.user_id, args.data_folder):
            print("❌ Échec du chargement des données")
            sys.exit(1)
    
    # Lancement dashboard
    if args.expert_only:
        dashboard_type = "expert"
    elif args.dashboard_only:
        dashboard_type = "standard"
    else:
        # Par défaut, demander à l'utilisateur
        print("\n📊 Quel dashboard lancer ?")
        print("1. Dashboard Expert (recommandé)")
        print("2. Dashboard Standard")
        
        choice = input("Choix (1-3) [1]: ").strip() or "1"
        
        dashboard_map = {
            "1": "expert",
            "2": "standard",
        }
        
        dashboard_type = dashboard_map.get(choice, "expert")
    
    print(f"\n🚀 Préparation du lancement...")
    time.sleep(1)
    
    success = run_dashboard(dashboard_type, args.port)
    
    if success:
        print("\n✅ Application terminée avec succès")
    else:
        print("\n❌ Erreur lors de l'exécution")
        sys.exit(1)

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        print("\n👋 Arrêt demandé par l'utilisateur")
    except Exception as e:
        print(f"\n❌ Erreur inattendue: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)