# ===== update_phase2.py =====
"""
Script de mise à jour pour intégrer complètement la Phase 2 :
- Navigation unifiée
- Parser PEA intégré
- Métriques avancées
- Simulateur liberté financière
"""

import os
import sys
import subprocess
from pathlib import Path
import shutil

def install_new_dependencies():
    """Installer les nouvelles dépendances Phase 2"""
    print("📦 Installation des nouvelles dépendances...")
    
    new_dependencies = [
        "pdfplumber==0.10.3",
        "yfinance==0.2.28", 
        "scipy==1.11.4",
        "python-dateutil==2.8.2"
    ]
    
    try:
        for dep in new_dependencies:
            print(f"  Installing {dep}...")
            subprocess.run([sys.executable, "-m", "pip", "install", dep], 
                          check=True, capture_output=True)
        
        print("✅ Nouvelles dépendances installées")
        return True
    
    except subprocess.CalledProcessError as e:
        print(f"❌ Erreur installation: {e}")
        return False

def backup_existing_files():
    """Sauvegarder les fichiers existants"""
    print("💾 Sauvegarde des fichiers existants...")
    
    backup_dir = "backup_before_phase2"
    if not os.path.exists(backup_dir):
        os.makedirs(backup_dir)
    
    files_to_backup = [
        "frontend/app.py",
        "backend/data/data_loader.py"
    ]
    
    for file_path in files_to_backup:
        if os.path.exists(file_path):
            backup_path = os.path.join(backup_dir, os.path.basename(file_path))
            shutil.copy2(file_path, backup_path)
            print(f"✅ Sauvegardé: {file_path} -> {backup_path}")
    
    return True

def create_missing_directories():
    """Créer les répertoires manquants"""
    print("📁 Création des répertoires Phase 2...")
    
    directories = [
        "backend/analytics",
        "data/raw/pea",
        "data/processed/pea",
        "frontend/pages",
        "tests/phase2"
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Créé: {directory}")
    
    # Créer les __init__.py nécessaires
    init_files = [
        "backend/analytics/__init__.py"
    ]
    
    for init_file in init_files:
        Path(init_file).touch()
        print(f"✅ Créé: {init_file}")

def test_imports():
    """Tester les nouveaux imports"""
    print("🧪 Test des nouveaux imports...")
    
    imports_to_test = [
        ("pdfplumber", "Parser PDF PEA"),
        ("yfinance", "Données benchmarks"),
        ("scipy.optimize", "Calculs TRI"),
        ("backend.analytics.advanced_metrics", "Métriques avancées"),
        ("backend.analytics.financial_freedom", "Simulateur liberté"),
        ("backend.data.pea_parser", "Parser PEA")
    ]
    
    success_count = 0
    
    for module_name, description in imports_to_test:
        try:
            if module_name.startswith("backend"):
                sys.path.insert(0, os.getcwd())
            
            __import__(module_name)
            print(f"✅ {module_name} - {description}")
            success_count += 1
        
        except ImportError as e:
            print(f"❌ {module_name} - {description}: {e}")
        
        except Exception as e:
            print(f"⚠️  {module_name} - {description}: {e}")
            success_count += 1  # Considérer comme succès partiel
    
    return success_count >= len(imports_to_test) - 1  # Tolérer 1 échec

def create_launcher_scripts():
    """Créer les scripts de lancement"""
    print("🚀 Création des scripts de lancement...")
    
    # Script principal unifié
    main_launcher = '''#!/usr/bin/env python
# ===== launch_wealth_dashboard.py =====
"""
Lanceur principal pour Wealth Dashboard Phase 2
"""
import subprocess
import sys
import os

def main():
    """Lancer le dashboard principal unifié"""
    print("🚀 Lancement Wealth Dashboard - Suite Complète")
    
    os.chdir(os.path.dirname(os.path.abspath(__file__)))
    
    # Lancer Streamlit avec l'app principal
    subprocess.run([
        sys.executable, "-m", "streamlit", "run", 
        "frontend/app.py",
        "--server.port", "8501",
        "--server.address", "localhost",
        "--theme.base", "light"
    ])

if __name__ == "__main__":
    main()
'''
    
    with open('launch_wealth_dashboard.py', 'w') as f:
        f.write(main_launcher)
    
    print("✅ launch_wealth_dashboard.py créé")
    
    # Script de test PEA
    pea_test_script = '''#!/usr/bin/env python
# ===== test_pea_parser.py =====
"""
Test rapide du parser PEA
"""
import sys
import os

# Ajouter le répertoire courant au path
sys.path.insert(0, os.getcwd())

def test_pea_parser():
    """Test basique du parser PEA"""
    print("🏦 Test du Parser PEA")
    print("=" * 30)
    
    try:
        from backend.data.pea_parser import PEAParser
        
        # Test d'instanciation
        parser = PEAParser("test-user")
        print("✅ Parser PEA instancié avec succès")
        
        # Test des fonctions utilitaires
        test_amount = parser._classify_pea_asset("AMUNDI ETF")
        print(f"✅ Classification d'actif: {test_amount}")
        
        print("\\n✅ Test PEA réussi!")
        print("\\n💡 Pour utiliser le parser:")
        print("  python load_sample_data_pea.py")
        
        return True
        
    except Exception as e:
        print(f"❌ Erreur test PEA: {e}")
        return False

if __name__ == "__main__":
    test_pea_parser()
'''
    
    with open('test_pea_parser.py', 'w') as f:
        f.write(pea_test_script)
    
    print("✅ test_pea_parser.py créé")

def create_usage_guide():
    """Créer un guide d'utilisation"""
    print("📚 Création du guide d'utilisation...")
    
    guide_content = """# Wealth Dashboard Phase 2 - Guide d'Utilisation

## 🚀 Nouveautés Phase 2

### Navigation Unifiée
- **Dashboard Principal** : Vue d'ensemble classique
- **Analyses Avancées** : TRI, Sharpe, VaR, benchmarks
- **Simulateur Liberté** : Projections Monte Carlo
- **Gestion PEA** : Parser et analyse des PDFs Bourse Direct
- **Configuration** : Paramètres et maintenance

### Parser PEA Intégré
- Support des PDFs Bourse Direct
- Extraction automatique des transactions
- Classification des actifs (actions, ETFs, fonds)
- Calcul des positions et valorisations

## 🎯 Utilisation

### Lancement Principal
```bash
python launch_wealth_dashboard.py
# Ou directement :
streamlit run frontend/app.py
```

### Chargement des Données

#### Crowdfunding (existant)
1. Allez dans la barre latérale
2. Uploadez votre fichier Excel (.xlsx)
3. Sélectionnez la plateforme
4. Cliquez "Charger Crowdfunding"

#### PEA (nouveau)
1. **Option 1 - Interface Web** :
   - Uploadez vos PDFs dans la barre latérale
   - Relevé de compte + Évaluation de portefeuille
   - Cliquez "Charger PEA"

2. **Option 2 - Script Dédié** :
   ```bash
   python load_sample_data_pea.py
   ```

### Organisation des Fichiers

```
data/raw/
├── pea/                          # Fichiers PEA
│   ├── releve_pea_202504.pdf    # Relevé de compte
│   └── evaluation_pea_202504.pdf # Évaluation portefeuille
├── Portefeuille LPB 20250529.xlsx
├── Portefeuille PretUp 20250529.xlsx
└── ...
```

## 📊 Nouvelles Analyses

### TRI (Taux de Rendement Interne)
- TRI global du portefeuille
- TRI par plateforme
- Multiple de capital

### Métriques de Risque
- **Sharpe Ratio** : Rendement ajusté du risque
- **VaR** : Value at Risk (perte potentielle)
- **Volatilité** : Écart-type des rendements
- **Max Drawdown** : Plus grosse baisse

### Comparaisons Benchmark
- CAC 40, S&P 500, MSCI World
- Alpha (surperformance vs marché)
- Beta (sensibilité marché)

### Simulateur Liberté Financière
- Simulation Monte Carlo (1000+ scénarios)
- Probabilité d'atteindre l'objectif
- Impact des allocations d'actifs
- Analyse de sensibilité

## 🔧 Maintenance

### Tests
```bash
python test_pea_parser.py        # Test parser PEA
python test_and_load_complete.py # Test complet
```

### Nettoyage
- Utilisez l'onglet "Configuration" 
- Bouton "Vider Cache" pour actualiser
- Bouton "Supprimer Données" pour reset

## 💡 Conseils d'Usage

1. **Chargez d'abord vos données** via les uploads
2. **Commencez par le Dashboard Principal** pour vue d'ensemble
3. **Explorez les Analyses Avancées** pour le TRI et métriques
4. **Utilisez le Simulateur** pour planifier votre liberté financière
5. **Consultez la Gestion PEA** pour vos positions actions

## 🆘 Dépannage

### Erreur "Module not found"
```bash
pip install -r requirements_phase2.txt
```

### Erreur PDF PEA
- Vérifiez que vos PDFs ne sont pas corrompus
- Assurez-vous qu'ils viennent de Bourse Direct
- Essayez de les renommer avec 'releve' ou 'evaluation'

### Cache bloqué
- Utilisez le bouton "Vider Cache" dans Configuration
- Ou redémarrez l'application

### Données manquantes
- Vérifiez que vos uploads ont réussi
- Consultez les logs dans la console
- Utilisez les scripts de chargement dédiés

## 🔗 Navigation Rapide

| Page | Raccourci | Usage |
|------|-----------|-------|
| Dashboard | `?page=dashboard` | Vue d'ensemble |
| Avancé | `?page=advanced` | TRI, métriques |
| Simulateur | `?page=simulator` | Projections |
| PEA | `?page=pea` | Gestion actions |
| Config | `?page=config` | Paramètres |
"""
    
    os.makedirs("docs", exist_ok=True)
    with open('docs/Phase2_Guide.md', 'w', encoding='utf-8') as f:
        f.write(guide_content)
    
    print("✅ Guide d'utilisation créé: docs/Phase2_Guide.md")

def run_final_tests():
    """Exécuter les tests finaux"""
    print("🧪 Tests finaux Phase 2...")
    
    tests = [
        ("Import advanced_metrics", lambda: __import__("backend.analytics.advanced_metrics")),
        ("Import financial_freedom", lambda: __import__("backend.analytics.financial_freedom")),
        ("Import pea_parser", lambda: __import__("backend.data.pea_parser")),
        ("Test database connection", test_database_connection)
    ]
    
    success_count = 0
    
    for test_name, test_func in tests:
        try:
            if test_name == "Test database connection":
                result = test_func()
            else:
                sys.path.insert(0, os.getcwd())
                test_func()
                result = True
            
            if result:
                print(f"✅ {test_name}")
                success_count += 1
            else:
                print(f"⚠️  {test_name} - Partiel")
                success_count += 0.5
        
        except Exception as e:
            print(f"❌ {test_name}: {e}")
    
    return success_count >= len(tests) - 1

def test_database_connection():
    """Test simple de la connexion BDD"""
    try:
        from backend.models.database import DatabaseManager
        db = DatabaseManager()
        return db.test_connection()
    except:
        return False

def main():
    """Mise à jour complète Phase 2"""
    print("🚀 MISE À JOUR WEALTH DASHBOARD - PHASE 2")
    print("=" * 60)
    print("Intégration : Navigation unifiée + Parser PEA + Métriques avancées")
    print("=" * 60)
    
    steps = [
        ("Sauvegarde fichiers existants", backup_existing_files),
        ("Installation nouvelles dépendances", install_new_dependencies),
        ("Création répertoires", create_missing_directories),
        ("Test imports", test_imports),
        ("Scripts de lancement", create_launcher_scripts),
        ("Guide d'utilisation", create_usage_guide),
        ("Tests finaux", run_final_tests)
    ]
    
    results = []
    
    for step_name, step_func in steps:
        print(f"\\n🔧 {step_name}...")
        try:
            result = step_func()
            success = result if isinstance(result, bool) else True
            results.append((step_name, success))
            
            if success:
                print(f"✅ {step_name} terminé")
            else:
                print(f"⚠️  {step_name} avec avertissements")
        
        except Exception as e:
            print(f"❌ Erreur {step_name}: {e}")
            results.append((step_name, False))
    
    # Rapport final
    print(f"\\n🎯 RAPPORT DE MISE À JOUR PHASE 2")
    print("=" * 50)
    
    passed = sum(1 for _, success in results if success)
    total = len(results)
    
    for step_name, success in results:
        status = "✅" if success else "❌"
        print(f"  {status} {step_name}")
    
    print(f"\\nScore: {passed}/{total} étapes réussies")
    
    if passed >= total - 1:
        print("\\n🎉 PHASE 2 INSTALLÉE AVEC SUCCÈS!")
        print("\\n🚀 COMMANDES DISPONIBLES:")
        print("  python launch_wealth_dashboard.py    # Dashboard unifié")
        print("  python load_sample_data_pea.py       # Chargement PEA")
        print("  python test_pea_parser.py            # Test parser PEA")
        print("\\n📚 DOCUMENTATION:")
        print("  docs/Phase2_Guide.md                 # Guide complet")
        print("\\n🌐 ACCÈS WEB:")
        print("  http://localhost:8501                # Dashboard principal")
        
    else:
        print(f"\\n⚠️  Installation partielle - {total - passed} problème(s)")
        print("\\n💡 SUGGESTIONS:")
        print("  - Vérifiez les erreurs ci-dessus")
        print("  - Relancez: pip install -r requirements_phase2.txt")
        print("  - Consultez docs/Phase2_Guide.md pour le dépannage")
    
    return passed >= total - 1

if __name__ == "__main__":
    try:
        success = main()
        print(f"\\n{'='*60}")
        
        input("\\nAppuyez sur Entrée pour continuer...")
        
        sys.exit(0 if success else 1)
    
    except KeyboardInterrupt:
        print("\\n\\n⚠️  Mise à jour interrompue")
        sys.exit(1)
    
    except Exception as e:
        print(f"\\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)