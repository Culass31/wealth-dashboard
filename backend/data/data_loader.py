# ===== backend/data/data_loader.py - AVEC PARSER UNIFIÉ =====
from backend.models.database import DatabaseManager
from backend.data.unified_parser import UnifiedPortfolioParser
from typing import Dict
import pandas as pd
import os

class DataLoader:
    """DataLoader corrigé utilisant le parser unifié expert"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def load_platform_data(self, file_path: str, platform: str, user_id: str) -> bool:
        """
        Charger les données depuis un fichier de plateforme
        Utilise le parser unifié pour toutes les plateformes
        """
        
        print(f"📥 Chargement {platform.upper()} pour utilisateur {user_id}")
        
        if not os.path.exists(file_path):
            print(f"❌ Fichier non trouvé: {file_path}")
            return False
        
        try:
            # Créer le parser unifié
            parser = UnifiedPortfolioParser(user_id)
            
            # Parser selon la plateforme
            print(f"🔍 Parsing {platform}...")
            investissements, flux_tresorerie = parser.parse_platform(file_path, platform)
            
            print(f"📊 Données parsées: {len(investissements)} investissements, {len(flux_tresorerie)} flux")
            
            # Validation des données
            if not self._validate_parsed_data(investissements, flux_tresorerie, platform):
                print(f"⚠️  Données {platform} invalides")
                return False
            
            # Insérer en base de données
            success_inv = self.db.insert_investments(investissements) if investissements else True
            success_cf = self.db.insert_cash_flows(flux_tresorerie) if flux_tresorerie else True
            
            if success_inv and success_cf:
                print(f"✅ {platform.upper()} chargé avec succès")
                return True
            else:
                print(f"❌ Échec insertion BDD pour {platform}")
                return False
            
        except Exception as e:
            print(f"❌ Erreur chargement {platform}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_pea_data(self, releve_path: str = None, evaluation_path: str = None, user_id: str = None) -> bool:
        """Charger PEA avec portfolio_positions pour l'évaluation"""
        if not user_id:
            user_id = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e"
            
        print(f"🏦 Chargement PEA pour utilisateur: {user_id}")
        
        from backend.data.unified_parser import UnifiedPortfolioParser
        from backend.models.database import DatabaseManager
        
        # Si pas de fichiers fournis, chercher dans le répertoire
        if not releve_path and not evaluation_path:
            for file in os.listdir('.'):
                if 'pea' in file.lower() and file.lower().endswith('.pdf'):
                    if any(keyword in file.lower() for keyword in ['releve', 'compte', 'transaction']):
                        releve_path = file
                    elif any(keyword in file.lower() for keyword in ['evaluation', 'portefeuille', 'position']):
                        evaluation_path = file
        
        if not releve_path and not evaluation_path:
            print("⚠️  Aucun fichier PEA trouvé")
            return False
        
        print(f"📂 Fichiers trouvés:")
        print(f"  📄 Relevé: {releve_path or 'Non trouvé'}")
        print(f"  📊 Évaluation: {evaluation_path or 'Non trouvé'}")
        
        try:
            # Parser PEA
            parser = UnifiedPortfolioParser(user_id)
            investments, cash_flows = parser._parse_pea(releve_path, evaluation_path)
            
            # Récupérer les positions de portefeuille
            portfolio_positions = parser.get_pea_portfolio_positions()
            
            # Connexion BDD
            db = DatabaseManager()
            
            # Insérer données
            success_cf = True
            success_pp = True
            
            if cash_flows:
                success_cf = db.insert_cash_flows(cash_flows)
                print(f"📊 Cash flows: {len(cash_flows)} transactions")
            
            if portfolio_positions:
                success_pp = db.insert_portfolio_positions(portfolio_positions)
                print(f"📊 Portfolio positions: {len(portfolio_positions)} positions")
            
            if success_cf and success_pp:
                print("✅ PEA chargé avec succès!")
                
                # Résumé
                if portfolio_positions:
                    total_value = sum(pos.get('market_value', 0) for pos in portfolio_positions)
                    print(f"💰 Valorisation totale PEA: {total_value:,.0f}€")
                
                return True
            else:
                print("❌ Échec chargement PEA")
                return False
                
        except Exception as e:
            print(f"❌ Erreur chargement PEA: {e}")
            import traceback
            traceback.print_exc()
            return False

    def load_assurance_vie_data(self, file_path: str, user_id: str) -> bool:
        """
        Charger les données Assurance Vie
        Utilise le parser unifié
        """
        
        print(f"🏛️  Chargement Assurance Vie pour utilisateur {user_id}")
        
        if not os.path.exists(file_path):
            print(f"❌ Fichier AV non trouvé: {file_path}")
            return False
        
        try:
            # Utiliser le parser unifié
            parser = UnifiedPortfolioParser(user_id)
            
            print("🔍 Parsing Assurance Vie...")
            investissements, flux_tresorerie = parser.parse_platform(file_path, 'assurance_vie')
            
            print(f"📊 AV parsée: {len(investissements)} investissements, {len(flux_tresorerie)} flux")
            
            # Insérer en base
            success_inv = self.db.insert_investments(investissements) if investissements else True
            success_cf = self.db.insert_cash_flows(flux_tresorerie) if flux_tresorerie else True
            
            if success_inv and success_cf:
                print("✅ Assurance Vie chargée avec succès")
                return True
            else:
                print("❌ Échec insertion AV")
                return False
            
        except Exception as e:
            print(f"❌ Erreur chargement AV: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_all_user_files(self, user_id: str, data_folder: str = "data/raw") -> bool:
        """
        Charger tous les fichiers utilisateur
        Mapping complet de vos fichiers
        """
        
        print(f"📂 Chargement complet pour utilisateur {user_id} depuis {data_folder}")
        
        # Mapping de vos fichiers
        fichiers_plateformes = {
            'lpb': 'Portefeuille LPB.xlsx',
            'pretup': 'Portefeuille PretUp.xlsx',
            'bienpreter': 'Portefeuille BienPreter.xlsx',
            'homunity': 'Portefeuille Homunity.xlsx',
            'assurance_vie': 'Portefeuille Linxea.xlsx'
        }
        
        success_count = 0
        total_platforms = len(fichiers_plateformes)
        
        # Charger les plateformes
        for plateforme, filename in fichiers_plateformes.items():
            file_path = os.path.join(data_folder, filename)
            
            print(f"\n📊 Traitement {plateforme.upper()}...")
            print(f"  🔍 Recherche: {file_path}")
            
            if os.path.exists(file_path):
                print(f"  ✅ Fichier trouvé")
                
                if plateforme == 'assurance_vie':
                    success = self.load_assurance_vie_data(file_path, user_id)
                else:
                    success = self.load_platform_data(file_path, plateforme, user_id)
                
                if success:
                    success_count += 1
                    print(f"  ✅ {plateforme.upper()} chargé")
                else:
                    print(f"  ❌ Échec {plateforme.upper()}")
            else:
                print(f"  ⚠️  Fichier non trouvé: {filename}")
        
        # Charger PEA si fichiers PDF disponibles
        print(f"\n🏦 Traitement PEA...")
        pea_folder = os.path.join(data_folder, "pea")
        if os.path.exists(pea_folder):
            releve_pea = None
            evaluation_pea = None
        
        # Chercher fichiers PEA
        for file in os.listdir(pea_folder):
            if file.lower().endswith('.pdf'):
                if any(keyword in file.lower() for keyword in ['releve', 'compte']):
                    releve_pea = os.path.join(pea_folder, file)
                elif any(keyword in file.lower() for keyword in ['evaluation', 'portefeuille']):
                    evaluation_pea = os.path.join(pea_folder, file)
        
        if releve_pea or evaluation_pea:
            if self.load_pea_data(releve_pea, evaluation_pea, user_id):
                success_count += 1
                total_platforms += 1
                print("  ✅ PEA chargé")
            else:
                print("  ❌ Échec PEA")
                total_platforms += 1
        else:
            print("  ⚠️  Aucun fichier PEA PDF trouvé")
        
        # Résumé
        print(f"\n📋 RÉSUMÉ CHARGEMENT:")
        print(f"  ✅ Succès: {success_count}/{total_platforms} plateformes")
        print(f"  📊 Taux de réussite: {(success_count/total_platforms)*100:.1f}%")
        
        if success_count > 0:
            # Afficher résumé des données
            self._display_loading_summary(user_id)
        
        return success_count > 0
    
    def _validate_parsed_data(self, investissements: list, flux_tresorerie: list, platform: str) -> bool:
        """Valider les données parsées"""
        
        # Vérifications de base
        if not investissements and not flux_tresorerie:
            print(f"⚠️  Aucune donnée parsée pour {platform}")
            return False
        
        # Vérifier structure investissements
        for inv in investissements:
            required_fields = ['id', 'user_id', 'platform', 'invested_amount']
            if not all(field in inv for field in required_fields):
                print(f"⚠️  Structure investissement invalide pour {platform}")
                return False
        
        # Vérifier structure flux
        for flux in flux_tresorerie:
            required_fields = ['id', 'user_id', 'platform', 'flow_type', 'gross_amount']
            if not all(field in flux for field in required_fields):
                print(f"⚠️  Structure flux invalide pour {platform}")
                return False
        
        return True
    
    def _display_loading_summary(self, user_id: str):
        """Afficher résumé des données chargées"""
        
        try:
            investments_df = self.db.get_user_investments(user_id)
            cash_flows_df = self.db.get_user_cash_flows(user_id)
            
            print(f"\n📈 DONNÉES CHARGÉES:")
            print(f"  💰 Investissements: {len(investments_df)}")
            print(f"  💸 Flux de trésorerie: {len(cash_flows_df)}")
            
            if not investments_df.empty:
                total_investi = investments_df['invested_amount'].sum()
                print(f"  💵 Total investi: {total_investi:,.0f} €")
                
                # Par plateforme
                platform_summary = investments_df.groupby('platform')['invested_amount'].agg(['count', 'sum'])
                print(f"\n📊 RÉPARTITION PAR PLATEFORME:")
                for platform, data in platform_summary.iterrows():
                    count, amount = data['count'], data['sum']
                    print(f"  {platform}: {count} positions, {amount:,.0f} €")
            
            if not cash_flows_df.empty and 'platform' in cash_flows_df.columns:
                print(f"\n💰 FLUX PAR PLATEFORME:")
                flux_summary = cash_flows_df.groupby('platform')['gross_amount'].agg(['count', 'sum'])
                for platform, data in flux_summary.iterrows():
                    count, amount = data['count'], data['sum']
                    print(f"  {platform}: {count} flux, {amount:,.0f} € (brut)")
        
        except Exception as e:
            print(f"⚠️  Erreur affichage résumé: {e}")
    
    def clear_user_data(self, user_id: str) -> bool:
        """Vider toutes les données utilisateur"""
        print(f"🗑️  Suppression données utilisateur {user_id}")
        try:
            return self.db.clear_user_data(user_id)
        except Exception as e:
            print(f"❌ Erreur suppression: {e}")
            return False
    
    def validate_all_files(self, data_folder: str = "data/raw") -> Dict:
        """
        Valider tous les fichiers avant chargement
        Retourne un rapport de validation
        """
        
        print(f"🔍 Validation des fichiers dans {data_folder}")
        
        validation_report = {
            'valid_files': [],
            'missing_files': [],
            'invalid_files': [],
            'total_files': 0,
            'valid_count': 0
        }
        
        # Fichiers attendus
        expected_files = {
            'lpb': 'Portefeuille LPB.xlsx',
            'pretup': 'Portefeuille PretUp.xlsx', 
            'bienpreter': 'Portefeuille BienPreter.xlsx',
            'homunity': 'Portefeuille Homunity.xlsx',
            'assurance_vie': 'Portefeuille Linxea.xlsx'
        }
        
        validation_report['total_files'] = len(expected_files)
        
        for platform, filename in expected_files.items():
            file_path = os.path.join(data_folder, filename)
            
            if os.path.exists(file_path):
                try:
                    # Test d'ouverture Excel
                    import pandas as pd
                    pd.read_excel(file_path, nrows=1)
                    
                    validation_report['valid_files'].append({
                        'platform': platform,
                        'filename': filename,
                        'path': file_path
                    })
                    validation_report['valid_count'] += 1
                    print(f"✅ {platform.upper()}: {filename}")
                    
                except Exception as e:
                    validation_report['invalid_files'].append({
                        'platform': platform,
                        'filename': filename,
                        'error': str(e)
                    })
                    print(f"❌ {platform.upper()}: Fichier corrompu - {e}")
            else:
                validation_report['missing_files'].append({
                    'platform': platform,
                    'filename': filename
                })
                print(f"⚠️  {platform.upper()}: Fichier manquant - {filename}")
        
        # Vérifier PEA
        pea_folder = os.path.join(data_folder, "pea")
        if os.path.exists(pea_folder):
            pea_files = [f for f in os.listdir(pea_folder) if f.lower().endswith('.pdf')]
            if pea_files:
                validation_report['pea_files'] = pea_files
                print(f"✅ PEA: {len(pea_files)} fichier(s) PDF trouvé(s)")
            else:
                print("⚠️  PEA: Aucun fichier PDF trouvé")
        
        print(f"\n📋 VALIDATION: {validation_report['valid_count']}/{validation_report['total_files']} fichiers valides")
        
        return validation_report
    
    def get_platform_summary(self, user_id: str) -> Dict:
        """Obtenir un résumé par plateforme"""
        
        try:
            investments_df = self.db.get_user_investments(user_id)
            cash_flows_df = self.db.get_user_cash_flows(user_id)
            
            summary = {}
            
            if not investments_df.empty:
                platform_summary = investments_df.groupby('platform').agg({
                    'invested_amount': ['count', 'sum', 'mean'],
                    'status': lambda x: x.value_counts().to_dict()
                })
                
                for platform in platform_summary.index:
                    count = platform_summary.loc[platform, ('invested_amount', 'count')]
                    total = platform_summary.loc[platform, ('invested_amount', 'sum')]
                    avg = platform_summary.loc[platform, ('invested_amount', 'mean')]
                    status_dist = platform_summary.loc[platform, ('status', '<lambda>')]
                    
                    # Flux associés
                    platform_flows = cash_flows_df[cash_flows_df['platform'] == platform] if 'platform' in cash_flows_df.columns else pd.DataFrame()
                    flux_count = len(platform_flows)
                    
                    summary[platform] = {
                        'nb_investissements': count,
                        'capital_total': total,
                        'ticket_moyen': avg,
                        'repartition_statuts': status_dist,
                        'nb_flux': flux_count
                    }
            
            return summary
            
        except Exception as e:
            print(f"❌ Erreur résumé plateformes: {e}")
            return {}

# ===== SCRIPT DE CHARGEMENT AUTOMATIQUE =====
def load_user_data_auto(user_id: str = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e", data_folder: str = "data/raw") -> bool:
    """Script automatique pour charger toutes vos données"""
    
    print("🚀 CHARGEMENT AUTOMATIQUE DONNÉES PATRIMOINE")   
    print("=" * 50)
    
    # Créer le loader
    loader = DataLoader()
    
    # Validation des fichiers
    validation_report = loader.validate_all_files(data_folder)
    
    if validation_report['valid_count'] == 0:
        print("❌ Aucun fichier valide trouvé")
        return False    
    
    # Validation des fichiers
    fichiers_attendus = [
        'Portefeuille LPB.xlsx',
        'Portefeuille PretUp.xlsx',
        'Portefeuille BienPreter.xlsx',
        'Portefeuille Homunity.xlsx',
        'Portefeuille Linxea.xlsx'
    ]
    
    print(f"\n📋 VÉRIFICATION FICHIERS dans {data_folder}:")
    files_found = 0

    # Créer le dossier s'il n'existe pas
    if not os.path.exists(data_folder):
        print(f"📁 Création du dossier {data_folder}")
        os.makedirs(data_folder)
    
    for fichier in fichiers_attendus:
        file_path = os.path.join(data_folder, fichier)
        if os.path.exists(file_path):
            print(f"  ✅ {fichier}")
            files_found += 1
        else:
            print(f"  ❌ {fichier}")
    
    # Vérifier dossier PEA
    pea_folder = os.path.join(data_folder, "pea")
    if os.path.exists(pea_folder):
        pea_files = [f for f in os.listdir(pea_folder) if f.endswith('.pdf')]
        if pea_files:
            print(f"  🏦 PEA: {len(pea_files)} fichier(s) PDF dans {pea_folder}")
            files_found += len(pea_files)
    
    if files_found == 0:
        print("❌ Aucun fichier trouvé")
        print(f"💡 Placez vos fichiers dans le dossier '{data_folder}'")
        return False
    
    # Chargement
    print(f"\n📥 Début chargement pour utilisateur: {user_id}")
    success = loader.load_all_user_files(user_id, data_folder)
    
    if success:
        print("\n🎉 CHARGEMENT TERMINÉ AVEC SUCCÈS!")
        
        # Résumé final
        summary = loader.get_platform_summary(user_id)
        if summary:
            print("\n📊 RÉSUMÉ FINAL:")
            total_capital = sum(data['capital_total'] for data in summary.values())
            total_positions = sum(data['nb_investissements'] for data in summary.values())
            
            print(f"  💰 Capital total: {total_capital:,.0f} €")
            print(f"  📈 Positions totales: {total_positions}")
            print(f"  🏢 Plateformes: {len(summary)}")
    else:
        print("\n❌ ÉCHEC DU CHARGEMENT")
    
    return success

if __name__ == "__main__":
    import sys
    user_id = sys.argv[1] if len(sys.argv) > 1 else "29dec51d-0772-4e3a-8e8f-1fece8fefe0e"
    data_folder = sys.argv[2] if len(sys.argv) > 2 else "data/raw"
    
    load_user_data_auto(user_id, data_folder)