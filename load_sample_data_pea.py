"""
Script pour charger les données PEA depuis les PDFs Bourse Direct
Usage: python load_sample_data_pea.py [user_id]
"""
import os
import sys
import pandas as pd
from pathlib import Path
from backend.data.data_loader import UnifiedPortfolioParser
from backend.models.database import DatabaseManager

def find_pea_files(data_folder: str = "data/raw") -> dict:
    """Rechercher automatiquement les fichiers PEA"""
    
    pea_files = {
        'releve': None,
        'evaluation': None
    }
    
    # Dossiers à chercher
    search_folders = [
        os.path.join(data_folder, "pea"),
        os.path.join(data_folder),
        "data/raw/pea",
        "data/raw"
    ]
    
    print("🔍 Recherche des fichiers PEA...")
    
    for folder in search_folders:
        if not os.path.exists(folder):
            continue
        
        print(f"📂 Recherche dans: {folder}")
        
        for file in os.listdir(folder):
            if not file.lower().endswith('.pdf'):
                continue
            
            file_path = os.path.join(folder, file)
            file_lower = file.lower()
            
            # Détecter le type de fichier par le nom
            if any(keyword in file_lower for keyword in ['releve', 'compte', 'mouvement']):
                if not pea_files['releve']:
                    pea_files['releve'] = file_path
                    print(f"📄 Relevé trouvé: {file}")
            
            elif any(keyword in file_lower for keyword in ['evaluation', 'portefeuille', 'position']):
                if not pea_files['evaluation']:
                    pea_files['evaluation'] = file_path
                    print(f"📊 Évaluation trouvée: {file}")
            
            # Si les mots-clés ne correspondent pas, essayer par ordre
            elif not pea_files['releve'] and 'pea' in file_lower:
                pea_files['releve'] = file_path
                print(f"📄 PDF PEA trouvé (assumé relevé): {file}")
            
            elif not pea_files['evaluation'] and 'pea' in file_lower:
                pea_files['evaluation'] = file_path
                print(f"📊 PDF PEA trouvé (assumé évaluation): {file}")
    
    return pea_files

def validate_and_load_pea(user_id: str, releve_path: str = None, evaluation_path: str = None) -> bool:
    """Valider et charger les données PEA"""
    
    loader = UnifiedPortfolioParser()
    
    # Validation des fichiers
    print("\n🔍 Validation des fichiers PEA...")
    validation_result = loader.validate_pea_files(releve_path, evaluation_path)
    
    # Afficher les messages de validation
    for message in validation_result['messages']:
        print(f"  {message}")
    
    if not validation_result['valid']:
        print("\n❌ Validation échouée - chargement annulé")
        return False
    
    print("\n✅ Validation réussie - début du chargement...")
    
    # Chargement
    success = loader.load_pea_data(releve_path, evaluation_path, user_id)
    
    if success:
        print("\n✅ Chargement PEA terminé avec succès")
        return True
    else:
        print("\n❌ Échec du chargement PEA")
        return False

def show_pea_summary(user_id: str):
    """Afficher un résumé des données PEA chargées"""
    
    print("\n📊 RÉSUMÉ DES DONNÉES PEA CHARGÉES")
    print("=" * 50)
    
    try:
        db = DatabaseManager()
        
        # Récupérer les données PEA
        investments_pea = db.get_user_investments(user_id, platform='PEA')
        cash_flows_all = db.get_user_cash_flows(user_id)
        
        # Filtrer les flux PEA
        cash_flows_pea = cash_flows_all[
            cash_flows_all['payment_method'].str.contains('PEA', case=False, na=False)
        ] if not cash_flows_all.empty else pd.DataFrame()
        
        print(f"👤 Utilisateur: {user_id}")
        print(f"📈 Investissements PEA: {len(investments_pea)}")
        print(f"💰 Flux de trésorerie PEA: {len(cash_flows_pea)}")
        
        if not investments_pea.empty:
            total_value = investments_pea['invested_amount'].sum()
            print(f"💵 Valorisation totale: {total_value:,.2f} €")
            
            # Répartition par classe d'actifs
            if 'asset_class' in investments_pea.columns:
                asset_breakdown = investments_pea.groupby('asset_class')['invested_amount'].sum()
                print(f"\n📊 Répartition par classe d'actifs:")
                for asset_class, amount in asset_breakdown.items():
                    percentage = (amount / total_value) * 100
                    print(f"  - {asset_class.title()}: {amount:,.0f} € ({percentage:.1f}%)")
            
            # Top 5 positions
            print(f"\n🏆 Top 5 des positions:")
            top_positions = investments_pea.nlargest(5, 'invested_amount')[['project_name', 'invested_amount']]
            for idx, (_, row) in enumerate(top_positions.iterrows(), 1):
                print(f"  {idx}. {row['project_name']}: {row['invested_amount']:,.0f} €")
        
        if not cash_flows_pea.empty:
            # Analyse des flux
            flux_entrants = cash_flows_pea[cash_flows_pea['flow_direction'] == 'in']['gross_amount'].sum()
            flux_sortants = cash_flows_pea[cash_flows_pea['flow_direction'] == 'out']['gross_amount'].sum()
            
            print(f"\n💸 Flux de trésorerie:")
            print(f"  - Entrants: {flux_entrants:,.2f} €")
            print(f"  - Sortants: {flux_sortants:,.2f} €")
            print(f"  - Net: {flux_entrants - flux_sortants:,.2f} €")
            
            # Répartition par type de flux
            flux_by_type = cash_flows_pea.groupby('flow_type')['gross_amount'].sum()
            print(f"\n📈 Répartition par type de flux:")
            for flow_type, amount in flux_by_type.items():
                print(f"  - {flow_type.title()}: {amount:,.2f} €")
        
        print("\n" + "=" * 50)
        
    except Exception as e:
        print(f"❌ Erreur lors de la génération du résumé: {e}")
        import traceback
        traceback.print_exc()

def interactive_file_selection():
    """Sélection interactive des fichiers PEA"""
    
    print("\n🎯 SÉLECTION INTERACTIVE DES FICHIERS PEA")
    print("=" * 50)
    
    # Chercher automatiquement d'abord
    auto_files = find_pea_files()
    
    releve_path = None
    evaluation_path = None
    
    # Relevé de compte
    print(f"\n📄 SÉLECTION DU RELEVÉ DE COMPTE:")
    if auto_files['releve']:
        print(f"Fichier auto-détecté: {auto_files['releve']}")
        use_auto = input("Utiliser ce fichier ? (o/n) [o]: ").lower().strip()
        if use_auto in ['', 'o', 'oui', 'y', 'yes']:
            releve_path = auto_files['releve']
    
    if not releve_path:
        manual_path = input("Chemin vers le relevé de compte (ou Entrée pour ignorer): ").strip()
        if manual_path and os.path.exists(manual_path):
            releve_path = manual_path
        elif manual_path:
            print(f"⚠️  Fichier non trouvé: {manual_path}")
    
    # Évaluation de portefeuille
    print(f"\n📊 SÉLECTION DE L'ÉVALUATION DE PORTEFEUILLE:")
    if auto_files['evaluation']:
        print(f"Fichier auto-détecté: {auto_files['evaluation']}")
        use_auto = input("Utiliser ce fichier ? (o/n) [o]: ").lower().strip()
        if use_auto in ['', 'o', 'oui', 'y', 'yes']:
            evaluation_path = auto_files['evaluation']
    
    if not evaluation_path:
        manual_path = input("Chemin vers l'évaluation de portefeuille (ou Entrée pour ignorer): ").strip()
        if manual_path and os.path.exists(manual_path):
            evaluation_path = manual_path
        elif manual_path:
            print(f"⚠️  Fichier non trouvé: {manual_path}")
    
    return releve_path, evaluation_path

def main():
    """Fonction principale"""
    
    print("🏦 CHARGEMENT DES DONNÉES PEA - BOURSE DIRECT")
    print("=" * 60)
    
    # Récupérer l'ID utilisateur
    if len(sys.argv) > 1:
        user_id = sys.argv[1]
    else:
        user_id = input("ID Utilisateur [29dec51d-0772-4e3a-8e8f-1fece8fefe0e]: ").strip()
        if not user_id:
            user_id = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e"
    
    print(f"👤 Utilisateur: {user_id}")
    
    # Mode de sélection des fichiers
    print(f"\n🎯 MODES DE CHARGEMENT DISPONIBLES:")
    print("1. Automatique (recherche dans data/raw/pea/)")
    print("2. Interactif (sélection manuelle)")
    print("3. Arguments (spécifier les chemins)")
    
    mode = input("\nMode souhaité (1/2/3) [1]: ").strip()
    
    releve_path = None
    evaluation_path = None
    
    if mode == "2":
        # Mode interactif
        releve_path, evaluation_path = interactive_file_selection()
    
    elif mode == "3":
        # Mode arguments
        if len(sys.argv) > 2:
            releve_path = sys.argv[2] if os.path.exists(sys.argv[2]) else None
        if len(sys.argv) > 3:
            evaluation_path = sys.argv[3] if os.path.exists(sys.argv[3]) else None
        
        if not releve_path and not evaluation_path:
            print("❌ Aucun fichier valide fourni en argument")
            return False
    
    else:
        # Mode automatique (par défaut)
        auto_files = find_pea_files()
        releve_path = auto_files['releve']
        evaluation_path = auto_files['evaluation']
    
    # Vérifier qu'on a au moins un fichier
    if not releve_path and not evaluation_path:
        print("\n❌ Aucun fichier PEA trouvé ou sélectionné")
        print("\n💡 Conseils:")
        print("- Placez vos PDFs dans le dossier data/raw/pea/")
        print("- Nommez-les avec 'releve' ou 'evaluation' dans le nom")
        print("- Ou utilisez le mode interactif (option 2)")
        return False
    
    # Afficher les fichiers sélectionnés
    print(f"\n📁 FICHIERS SÉLECTIONNÉS:")
    if releve_path:
        print(f"📄 Relevé: {releve_path}")
    if evaluation_path:
        print(f"📊 Évaluation: {evaluation_path}")
    
    # Confirmation
    confirm = input(f"\nContinuer le chargement ? (o/n) [o]: ").lower().strip()
    if confirm not in ['', 'o', 'oui', 'y', 'yes']:
        print("❌ Chargement annulé")
        return False
    
    # Chargement
    print(f"\n🚀 DÉBUT DU CHARGEMENT PEA")
    print("-" * 40)
    
    success = validate_and_load_pea(user_id, releve_path, evaluation_path)
    
    if success:
        # Afficher le résumé
        show_pea_summary(user_id)
        
        print(f"\n🎉 CHARGEMENT PEA TERMINÉ AVEC SUCCÈS!")
        print(f"\n📋 Prochaines étapes:")
        print(f"1. Lancez le dashboard: python run_app.py")
        print(f"2. Allez dans l'onglet 'Gestion PEA' pour voir vos données")
        print(f"3. Consultez les analyses avancées pour voir votre TRI")
        
        return True
    
    else:
        print(f"\n❌ ÉCHEC DU CHARGEMENT PEA")
        print(f"\n💡 Suggestions:")
        print(f"- Vérifiez que vos PDFs ne sont pas corrompus")
        print(f"- Assurez-vous qu'ils proviennent bien de Bourse Direct")
        print(f"- Consultez les logs d'erreur ci-dessus")
        
        return False

def create_sample_folder_structure():
    """Créer la structure de dossiers pour les fichiers PEA"""
    
    print("📁 Création de la structure de dossiers...")
    
    folders_to_create = [
        "data/raw/pea",
        "data/processed/pea"
    ]
    
    for folder in folders_to_create:
        Path(folder).mkdir(parents=True, exist_ok=True)
        print(f"✅ Créé: {folder}")
    
    # Créer un fichier README
    readme_content = """# Dossier PEA

## Structure des fichiers

Placez vos fichiers PDF de Bourse Direct dans ce dossier :

- `releve_pea_YYYYMM.pdf` : Relevé de compte mensuel
- `evaluation_pea_YYYYMM.pdf` : Évaluation de portefeuille

## Nommage recommandé

- Incluez 'releve' ou 'compte' dans le nom pour les relevés
- Incluez 'evaluation' ou 'portefeuille' dans le nom pour les évaluations
- Ajoutez la date pour organiser vos fichiers

## Exemples

- `releve_pea_202504.pdf`
- `evaluation_portefeuille_avril_2025.pdf`
- `compte_pea_30042025.pdf`

## Chargement

```bash
# Chargement automatique
python load_sample_data_pea.py

# Avec ID utilisateur spécifique
python load_sample_data_pea.py votre-user-id

# Mode interactif
python load_sample_data_pea.py votre-user-id
# puis choisir l'option 2
```
"""
    
    readme_path = "data/raw/pea/README.md"
    with open(readme_path, 'w', encoding='utf-8') as f:
        f.write(readme_content)
    
    print(f"✅ README créé: {readme_path}")

if __name__ == "__main__":
    try:
        # Créer la structure de dossiers si nécessaire
        create_sample_folder_structure()
        
        # Lancer le chargement principal
        success = main()
        
        sys.exit(0 if success else 1)
        
    except KeyboardInterrupt:
        print("\n\n⚠️  Chargement interrompu par l'utilisateur")
        sys.exit(1)
    
    except Exception as e:
        print(f"\n❌ Erreur fatale: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)