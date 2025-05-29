"""
Script de test et chargement complet avec débogage détaillé
"""
import os
import sys
from datetime import datetime
import traceback

# Ajouter le répertoire courant au PATH
sys.path.insert(0, os.getcwd())

from backend.models.database import DatabaseManager
from backend.data.data_loader import DataLoader

# ID utilisateur de test (à remplacer par le vôtre)
USER_ID_TEST = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e"

def test_database_connection():
    """Tester la connexion à la base de données"""
    print("🔍 Test de connexion à la base de données...")
    
    try:
        db = DatabaseManager()
        if db.test_connection():
            print("✅ Connexion à la base de données réussie")
            return True
        else:
            print("❌ Test de connexion échoué")
            return False
    except Exception as e:
        print(f"❌ Erreur de connexion: {e}")
        return False

def clear_existing_data():
    """Vider les données existantes pour les tests"""
    print(f"\n🗑️  Suppression des données existantes pour l'utilisateur {USER_ID_TEST}")
    
    try:
        db = DatabaseManager()
        success = db.clear_user_data(USER_ID_TEST)
        if success:
            print("✅ Données existantes supprimées")
        else:
            print("⚠️  Problème lors de la suppression (peut-être aucune donnée à supprimer)")
        return success
    except Exception as e:
        print(f"❌ Erreur lors de la suppression: {e}")
        return False

def test_individual_platform(platform: str, file_path: str):
    """Tester le chargement d'une plateforme individuelle"""
    print(f"\n📊 Test de {platform.upper()}")
    print("=" * 50)
    
    if not os.path.exists(file_path):
        print(f"❌ Fichier non trouvé: {file_path}")
        return False
    
    try:
        loader = DataLoader()
        
        print(f"📂 Chargement du fichier: {file_path}")
        success = loader.load_platform_data(file_path, platform, USER_ID_TEST)
        
        if success:
            print(f"✅ {platform.upper()} chargé avec succès")
            
            # Vérifier les données chargées
            db = DatabaseManager()
            investments_df = db.get_user_investments(USER_ID_TEST, platform.upper())
            cash_flows_df = db.get_user_cash_flows(USER_ID_TEST)
            
            print(f"📈 Investissements chargés: {len(investments_df)}")
            print(f"💰 Flux de trésorerie chargés: {len(cash_flows_df[cash_flows_df['description'].str.contains(platform.upper(), case=False, na=False)] if not cash_flows_df.empty else cash_flows_df)}")
            
            if not investments_df.empty:
                total_invested = investments_df['invested_amount'].sum()
                print(f"💸 Montant total investi: {total_invested:,.2f} €")
                
                # Afficher quelques exemples
                print("\n📋 Échantillon des investissements:")
                for idx, row in investments_df.head(3).iterrows():
                    print(f"  - {row.get('project_name', 'N/A')}: {row.get('invested_amount', 0):,.0f} € ({row.get('status', 'N/A')})")
            
            return True
        else:
            print(f"❌ Échec du chargement de {platform.upper()}")
            return False
            
    except Exception as e:
        print(f"❌ Erreur lors du test de {platform}: {e}")
        traceback.print_exc()
        return False

def test_all_platforms():
    """Tester toutes les plateformes disponibles"""
    print("\n🎯 TEST DE TOUTES LES PLATEFORMES")
    print("=" * 60)
    
    # Configuration des fichiers
    plateformes_config = {
        'lbp': 'data/raw/Portefeuille LPB 20250529.xlsx',
        'pretup': 'data/raw/Portefeuille PretUp 20250529.xlsx', 
        'bienpreter': 'data/raw/Portefeuille BienPreter 20250529.xlsx',
        'homunity': 'data/raw/Portefeuille Homunity 20250529.xlsx'
    }
    
    success_count = 0
    total_count = len(plateformes_config)
    
    for platform, file_path in plateformes_config.items():
        if test_individual_platform(platform, file_path):
            success_count += 1
    
    print(f"\n📊 RÉSUMÉ DES TESTS")
    print("=" * 30)
    print(f"Plateformes testées: {total_count}")
    print(f"Succès: {success_count}")
    print(f"Échecs: {total_count - success_count}")
    
    return success_count, total_count

def generate_summary_report():
    """Générer un rapport de résumé des données chargées"""
    print(f"\n📈 RAPPORT DE RÉSUMÉ DES DONNÉES")
    print("=" * 50)
    
    try:
        db = DatabaseManager()
        summary = db.get_platform_summary(USER_ID_TEST)
        
        if summary:
            print(f"💰 Total investi: {summary.get('total_investi', 0):,.2f} €")
            print(f"🏗️  Total projets: {summary.get('total_projets', 0)}")
            print(f"💸 Total entrées: {summary.get('total_entrees', 0):,.2f} €")
            print(f"📊 Performance nette: {summary.get('performance_nette', 0):,.2f} €")
            
            if 'plateformes' in summary:
                print("\n📋 Par plateforme:")
                for platform, stats in summary['plateformes'].items():
                    if isinstance(stats, dict) and ('invested_amount', 'sum') in stats:
                        montant = stats[('invested_amount', 'sum')]
                        nombre = stats[('invested_amount', 'count')]
                        print(f"  - {platform}: {montant:,.0f} € ({nombre} projets)")
        else:
            print("⚠️  Aucune donnée trouvée pour générer le résumé")
            
    except Exception as e:
        print(f"❌ Erreur lors de la génération du rapport: {e}")

def verify_data_integrity():
    """Vérifier l'intégrité des données chargées"""
    print(f"\n🔍 VÉRIFICATION DE L'INTÉGRITÉ DES DONNÉES")
    print("=" * 50)
    
    try:
        db = DatabaseManager()
        investments_df = db.get_user_investments(USER_ID_TEST)
        cash_flows_df = db.get_user_cash_flows(USER_ID_TEST)
        
        print(f"📊 Total investissements: {len(investments_df)}")
        print(f"💰 Total flux de trésorerie: {len(cash_flows_df)}")
        
        # Vérifications d'intégrité
        issues = []
        
        if not investments_df.empty:
            # Vérifier les dates nulles
            null_dates = investments_df['investment_date'].isnull().sum()
            if null_dates > 0:
                issues.append(f"{null_dates} investissements avec date nulle")
            
            # Vérifier les montants négatifs ou nuls
            invalid_amounts = (investments_df['invested_amount'] <= 0).sum()
            if invalid_amounts > 0:
                issues.append(f"{invalid_amounts} investissements avec montant invalide")
            
            # Vérifier les noms de projets vides
            empty_names = investments_df['project_name'].isnull().sum()
            if empty_names > 0:
                issues.append(f"{empty_names} investissements sans nom de projet")
        
        if not cash_flows_df.empty:
            # Vérifier les dates de transaction nulles
            null_transaction_dates = cash_flows_df['transaction_date'].isnull().sum()
            if null_transaction_dates > 0:
                issues.append(f"{null_transaction_dates} flux avec date de transaction nulle")
            
            # Vérifier les montants invalides
            invalid_cf_amounts = (cash_flows_df['gross_amount'] <= 0).sum()
            if invalid_cf_amounts > 0:
                issues.append(f"{invalid_cf_amounts} flux avec montant invalide")
        
        if issues:
            print("⚠️  Problèmes détectés:")
            for issue in issues:
                print(f"  - {issue}")
        else:
            print("✅ Aucun problème d'intégrité détecté")
            
        return len(issues) == 0
        
    except Exception as e:
        print(f"❌ Erreur lors de la vérification: {e}")
        return False

def test_dashboard_data():
    """Tester que les données sont compatibles avec le dashboard"""
    print(f"\n📊 TEST DE COMPATIBILITÉ DASHBOARD")
    print("=" * 40)
    
    try:
        # Simuler le chargement des données comme le fait le dashboard
        sys.path.append('frontend')
        from frontend.app import charger_donnees_utilisateur, calculer_metriques
        
        investments_df, cash_flows_df = charger_donnees_utilisateur(USER_ID_TEST)
        
        if investments_df.empty and cash_flows_df.empty:
            print("❌ Aucune donnée disponible pour le dashboard")
            return False
        
        print(f"✅ Données chargées: {len(investments_df)} investissements, {len(cash_flows_df)} flux")
        
        # Tester le calcul des métriques
        metrics = calculer_metriques(investments_df, cash_flows_df)
        
        print("📈 Métriques calculées:")
        print(f"  - Total investi: {metrics.get('total_investi', 0):,.0f} €")
        print(f"  - Performance nette: {metrics.get('performance_nette', 0):,.0f} €")
        print(f"  - Taux réinvestissement: {metrics.get('taux_reinvestissement', 0):.1f}%")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur lors du test dashboard: {e}")
        return False

def main():
    """Fonction principale de test"""
    print("🚀 SUITE DE TESTS COMPLÈTE - WEALTH DASHBOARD")
    print("=" * 60)
    print(f"Utilisateur de test: {USER_ID_TEST}")
    print(f"Heure de début: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("=" * 60)
    
    # Liste des tests
    tests = [
        ("Connexion base de données", test_database_connection),
        ("Suppression données existantes", clear_existing_data),
        ("Chargement plateformes", test_all_platforms),
        ("Intégrité des données", verify_data_integrity),
        ("Compatibilité dashboard", test_dashboard_data),
        ("Rapport de résumé", lambda: (generate_summary_report(), True)[1])
    ]
    
    results = []
    
    for test_name, test_func in tests:
        print(f"\n🧪 {test_name.upper()}")
        print("-" * 40)
        
        try:
            if test_name == "Chargement plateformes":
                success_count, total_count = test_func()
                result = success_count > 0
                results.append((test_name, result, f"{success_count}/{total_count}"))
            else:
                result = test_func()
                results.append((test_name, result, "OK" if result else "ÉCHEC"))
        except Exception as e:
            print(f"❌ Erreur lors du test '{test_name}': {e}")
            results.append((test_name, False, f"ERREUR: {e}"))
    
    # Rapport final
    print(f"\n🎯 RAPPORT FINAL")
    print("=" * 50)
    print(f"Heure de fin: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print("\nRésultats des tests:")
    
    passed = 0
    for test_name, success, details in results:
        status = "✅" if success else "❌"
        print(f"  {status} {test_name}: {details}")
        if success:
            passed += 1
    
    print(f"\nScore: {passed}/{len(results)} tests réussis")
    
    if passed == len(results):
        print("\n🎉 TOUS LES TESTS SONT PASSÉS!")
        print("Vous pouvez maintenant lancer le dashboard avec: python run_app.py")
    else:
        print(f"\n⚠️  {len(results) - passed} test(s) ont échoué")
        print("Veuillez corriger les problèmes avant de continuer")
    
    return passed == len(results)

if __name__ == "__main__":
    try:
        success = main()
        sys.exit(0 if success else 1)
    except KeyboardInterrupt:
        print("\n\n⚠️  Test interrompu par l'utilisateur")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        traceback.print_exc()
        sys.exit(1)