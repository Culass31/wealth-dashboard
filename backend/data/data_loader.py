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
    
    def load_pea_data(self, releve_path: str = None, evaluation_path: str = None, user_id: str = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e") -> bool:
        """ Charger PEA avec portfolio_positions """
        print(f"🏦 Chargement PEA pour utilisateur: {user_id}")
        
        if not releve_path and not evaluation_path:
            print("⚠️  Aucun fichier PEA fourni")
            return False
        
        print(f"📂 Fichiers fournis:")
        if releve_path:
            print(f"  📄 Relevé: {releve_path}")
        if evaluation_path:
            print(f"  📊 Évaluation: {evaluation_path}")
        
        try:
            from backend.data.unified_parser import UnifiedPortfolioParser
            
            # Parser PEA
            parser = UnifiedPortfolioParser(user_id)
            investments, cash_flows = parser._parse_pea(releve_path, evaluation_path)
            
            # Récupérer les positions de portefeuille
            portfolio_positions = parser.get_pea_portfolio_positions()
            
            # Insérer données
            success_cf = True
            success_pp = True
            
            if cash_flows:
                success_cf = self.db.insert_cash_flows(cash_flows)
                print(f"📊 Cash flows: {len(cash_flows)} transactions")
            
            if portfolio_positions:
                success_pp = self.db.insert_portfolio_positions(portfolio_positions)
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
        
    def load_all_pea_files(self, user_id: str, pea_folder: str = ".") -> bool:
        """
        ✅ NOUVEAU : Charger TOUS les fichiers PEA d'un dossier automatiquement
        """
        print(f"🏦 Chargement AUTOMATIQUE PEA pour utilisateur: {user_id}")
        print(f"📂 Dossier PEA: {pea_folder}")
        
        # Chercher tous les fichiers PEA
        evaluation_files = []
        releve_files = []
        
        import os
        
        if not os.path.exists(pea_folder):
            print(f"❌ Dossier non trouvé: {pea_folder}")
            return False
        
        for file in os.listdir(pea_folder):
            if file.lower().endswith('.pdf'):
                file_lower = file.lower()
                file_path = os.path.join(pea_folder, file)
                
                # Classification par type de fichier
                if any(keyword in file_lower for keyword in ['evaluation', 'portefeuille', 'position']):
                    evaluation_files.append(file_path)
                    print(f"📊 Évaluation trouvée: {file}")
                elif any(keyword in file_lower for keyword in ['releve', 'compte', 'transaction']):
                    releve_files.append(file_path)
                    print(f"📄 Relevé trouvé: {file}")
                elif 'pea' in file_lower:
                    # Fichier PEA générique - deviner le type
                    if any(hint in file_lower for hint in ['eval', 'portfolio', 'pos']):
                        evaluation_files.append(file_path)
                        print(f"📊 Évaluation (PEA): {file}")
                    else:
                        releve_files.append(file_path)
                        print(f"📄 Relevé (PEA): {file}")
        
        if not evaluation_files and not releve_files:
            print("⚠️  Aucun fichier PEA trouvé dans le dossier")
            return False
        
        print(f"\n📂 Fichiers PEA détectés:")
        print(f"  📊 {len(evaluation_files)} évaluation(s)")
        print(f"  📄 {len(releve_files)} relevé(s)")
        
        try:
            from backend.data.unified_parser import UnifiedPortfolioParser
            
            parser = UnifiedPortfolioParser(user_id)
            
            total_positions = 0
            total_cash_flows = 0
            
            # TRAITER TOUTES LES ÉVALUATIONS
            for eval_file in evaluation_files:
                print(f"\n📊 Traitement évaluation: {os.path.basename(eval_file)}")
                try:
                    # Parser seulement l'évaluation
                    _, _ = parser._parse_pea(None, eval_file)
                    
                    # Récupérer les positions extraites
                    positions = parser.get_pea_portfolio_positions()
                    
                    if positions:
                        # Insertion en base
                        success_pos = self.db.insert_portfolio_positions(positions)
                        if success_pos:
                            total_positions += len(positions)
                            print(f"    ✅ {len(positions)} positions insérées")
                        else:
                            print(f"    ❌ Échec insertion positions")
                    else:
                        print(f"    ⚠️  Aucune position extraite")
                    
                except Exception as e:
                    print(f"    ❌ Erreur traitement évaluation: {e}")
            
            # TRAITER TOUS LES RELEVÉS
            for releve_file in releve_files:
                print(f"\n📄 Traitement relevé: {os.path.basename(releve_file)}")
                try:
                    # Parser seulement le relevé
                    _, cash_flows = parser._parse_pea(releve_file, None)
                    
                    if cash_flows:
                        # Insertion en base
                        success_cf = self.db.insert_cash_flows(cash_flows)
                        if success_cf:
                            total_cash_flows += len(cash_flows)
                            print(f"    ✅ {len(cash_flows)} transactions insérées")
                        else:
                            print(f"    ❌ Échec insertion transactions")
                    else:
                        print(f"    ⚠️  Aucune transaction extraite")
                    
                except Exception as e:
                    print(f"    ❌ Erreur traitement relevé: {e}")
            
            # RÉSUMÉ FINAL
            print(f"\n🎉 RÉSUMÉ CHARGEMENT PEA AUTOMATIQUE:")
            print(f"   📊 Positions insérées: {total_positions}")
            print(f"   💰 Transactions insérées: {total_cash_flows}")
            
            # Calculer valorisation totale actuelle
            if total_positions > 0:
                try:
                    positions_df = self.db.get_portfolio_positions(user_id, 'PEA')
                    if not positions_df.empty:
                        total_value = positions_df['market_value'].sum()
                        unique_dates = positions_df['valuation_date'].nunique()
                        print(f"   💎 Valorisation totale: {total_value:,.0f}€")
                        print(f"   📅 Périodes de valorisation: {unique_dates}")
                except Exception as e:
                    print(f"   ⚠️  Impossible de calculer la valorisation: {e}")
            
            success = (total_positions > 0 or total_cash_flows > 0)
            
            if success:
                print(f"\n✅ PEA complet chargé avec succès!")
            else:
                print(f"\n❌ Aucune donnée PEA extraite")
            
            return success
            
        except Exception as e:
            print(f"❌ Erreur chargement PEA automatique: {e}")
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
        ✅ CORRIGÉ : Charger tous les fichiers utilisateur
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
            
            if os.path.exists(file_path):
                print(f"\n📊 Traitement {plateforme.upper()}...")
                
                if plateforme == 'assurance_vie':
                    success = self.load_assurance_vie_data(file_path, user_id)
                else:
                    success = self.load_platform_data(file_path, plateforme, user_id)
                
                if success:
                    success_count += 1
                    print(f"✅ {plateforme.upper()} chargé")
                else:
                    print(f"❌ Échec {plateforme.upper()}")
            else:
                print(f"⚠️  Fichier non trouvé: {file_path}")
        
        # ✅ CORRECTION : Charger PEA avec la nouvelle méthode automatique
        print(f"\n🏦 Traitement PEA automatique...")
        
        # Chercher dossier PEA ou fichiers PEA dans le dossier principal
        pea_folder = os.path.join(data_folder, "pea")
        
        if os.path.exists(pea_folder):
            print(f"📂 Dossier PEA trouvé: {pea_folder}")
            pea_success = self.load_all_pea_files(user_id, pea_folder)
        else:
            print(f"📂 Recherche fichiers PEA dans: {data_folder}")
            pea_success = self.load_all_pea_files(user_id, data_folder)
        
        if pea_success:
            success_count += 1
            total_platforms += 1
            print("✅ PEA chargé")
        else:
            print("❌ Échec PEA")
            total_platforms += 1
        
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


if __name__ == "__main__":
    import sys
    user_id = sys.argv[1] if len(sys.argv) > 1 else "29dec51d-0772-4e3a-8e8f-1fece8fefe0e"
    data_folder = sys.argv[2] if len(sys.argv) > 2 else "data/raw"
    
    load_user_data_auto(user_id, data_folder)