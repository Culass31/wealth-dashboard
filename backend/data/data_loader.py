import logging
import os
import pandas as pd
from typing import Dict, List, Optional
from backend.models.database import ExpertDatabaseManager
from backend.data.unified_parser import UnifiedPortfolioParser
from backend.data.parser_constants import PLATFORM_MAPPING
from scripts.config import Config

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.INFO)

class DataLoader:
    """DataLoader corrigé utilisant le parser unifié expert"""
    
    def __init__(self):
        self.db = ExpertDatabaseManager()
        
    def load_platform_data(self, file_path: str, platform_key: str, user_id: str) -> bool:
        """Charge les données pour une plateforme (sauf PEA)."""
        platform_name = PLATFORM_MAPPING.get(platform_key.lower(), platform_key) # Utilise le nom complet
        if platform_key.lower() == 'pea':
            logging.debug(f"[DEBUG] load_platform_data: Ignor le chargement PEA via cette mthode.")
            return False # Ne pas traiter le PEA ici

        logging.info(f"Chargement {platform_name.upper()} pour utilisateur {user_id}")
        
        if not os.path.exists(file_path):
            logging.error(f"❌ Fichier non trouvé: {file_path}")
            return False
        
        try:
            parser = UnifiedPortfolioParser(user_id)
            logging.info(f"Parsing {platform_name}...")
            
            # Le parser retourne maintenant un dictionnaire
            parsed_data = parser.parse_platform(file_path, platform_name)
            
            investments = parsed_data.get("investments", [])
            cash_flows = parsed_data.get("cash_flows", [])
            liquidity_balances = parsed_data.get("liquidity_balances", [])
            
            logging.info(f"📊 Données parsées: {len(investments)} investissements, {len(cash_flows)} flux")
            
            if not self._validate_parsed_data(investments, cash_flows, platform_name):
                logging.warning(f"Données {platform_name} invalides")
                return False
            
            success_inv = self.db.insert_investments(investments) if investments else True
            success_cf = self.db.insert_cash_flows(cash_flows) if cash_flows else True
            success_lb = True
            if liquidity_balances:
                for lb in liquidity_balances:
                    if not self.db.insert_liquidity_balance(lb):
                        success_lb = False
                        logging.error(f"Échec de l'insertion du solde de liquidités pour {platform_name}")

            if success_inv and success_cf and success_lb:
                logging.info(f"✅ {platform_name.upper()} chargé avec succès")
                return True
            else:
                logging.error(f"❌ Échec insertion BDD pour {platform_name}")
                return False
            
        except Exception as e:
            logging.exception(f"❌ Erreur chargement {platform_name}: {e}")
            return False

    from scripts.config import Config

    def load_pea_data(self, releve_path: str = None, evaluation_path: str = None, user_id: str = Config.DEFAULT_USER_ID) -> bool:
            """ Charger PEA avec portfolio_positions """
            logging.info(f"Chargement PEA pour utilisateur: {user_id}")
            
            if not releve_path and not evaluation_path:
                logging.warning("Aucun fichier PEA fourni")
                return False
            
            logging.info(f"Fichiers fournis:")
            if releve_path:
                logging.info(f"  📄 Relevé: {releve_path}")
            if evaluation_path:
                logging.info(f"  📊 Évaluation: {evaluation_path}")
            
            try:
                parser = UnifiedPortfolioParser(user_id)
                
                # Parser PEA
                investments_data, cash_flows_data = parser._parse_pea(releve_path, evaluation_path)
                
                # Récupérer les positions de portefeuille
                portfolio_positions_data = parser.get_pea_portfolio_positions()
                
                # Insérer données
                success_cf = True
                success_pp = True
                success_lb = True # Nouvelle variable pour liquidité
                
                if cash_flows_data:
                    success_cf = self.db.insert_cash_flows(cash_flows_data)
                    logging.info(f"📊 Cash flows: {len(cash_flows_data)} transactions")
                
                if portfolio_positions_data:
                    success_pp = self.db.insert_portfolio_positions(portfolio_positions_data)
                    logging.info(f"📊 Portfolio positions: {len(portfolio_positions_data)} positions")
                
                # Insérer la liquidité PEA si extraite
                liquidity_balance_data = parser.get_pea_liquidity_balance()
                if liquidity_balance_data:
                    success_lb = self.db.insert_liquidity_balance(liquidity_balance_data)
                    logging.info(f"Liquidité PEA: {liquidity_balance_data.get('amount', 0)} euros")
                
                if success_cf and success_pp and success_lb:
                    logging.info("✅ PEA chargé avec succès!")
                    
                    # Résumé
                    if portfolio_positions_data:
                        total_value = sum(pos.get('market_value', 0) for pos in portfolio_positions_data)
                        logging.info(f"💰 Valorisation totale PEA: {total_value:,.0f}€")
                    
                    return True
                else:
                    logging.error("❌ Échec chargement PEA")
                    return False
                    
            except Exception as e:
                logging.exception(f"❌ Erreur chargement PEA: {e}")
                return False
        
    def load_all_pea_files(self, user_id: str, pea_folder: str) -> bool:
        """
        [CORRIGÉ] Charge TOUS les fichiers PEA (relevés et évaluations) d'un dossier.
        Identifie les types de fichiers et les passe au parser PEA.
        """
        logging.info(f"Chargement AUTOMATIQUE et COMPLET du PEA pour l'utilisateur: {user_id}")
        
        if not os.path.exists(pea_folder):
            logging.error(f"❌ Dossier PEA non trouvé: {pea_folder}")
            return False

        all_pdf_files = [os.path.join(pea_folder, f) for f in os.listdir(pea_folder) if f.lower().endswith('.pdf')]
        if not all_pdf_files:
            logging.warning("Aucun fichier PDF trouvé dans le dossier PEA.")
            return False

        releve_files = []
        evaluation_files = []

        for file_path in all_pdf_files:
            file_lower = os.path.basename(file_path).lower()
            if 'releve' in file_lower:
                releve_files.append(file_path)
            elif any(keyword in file_lower for keyword in ['evaluation', 'portefeuille', 'positions']):
                evaluation_files.append(file_path)
            else:
                logging.warning(f"Fichier PEA non classifié et ignoré : {file_path}")

        if not releve_files and not evaluation_files:
            logging.warning("Aucun fichier PEA pertinent (relevé ou évaluation) trouvé.")
            return False

        parser = UnifiedPortfolioParser(user_id)
        
        try:
            # Passer les listes de fichiers au parser PEA
            parsed_data = parser._parse_pea(releve_paths=releve_files, evaluation_paths=evaluation_files)
            
            all_cash_flows = parsed_data.get("cash_flows", [])
            all_positions = parsed_data.get("portfolio_positions", [])
            all_liquidity = parsed_data.get("liquidity_balances", [])

            logging.info("--- Fin du parsing de tous les fichiers PEA --- ")
            logging.info(f"📊 Total transactions extraites: {len(all_cash_flows)}")
            logging.info(f"📈 Total positions extraites: {len(all_positions)}")
            logging.info(f"💰 Total liquidités extraites: {len(all_liquidity)}")

            # Insérer toutes les données agrégées en base
            success_cf = self.db.insert_cash_flows(all_cash_flows) if all_cash_flows else True
            success_pp = self.db.insert_portfolio_positions(all_positions) if all_positions else True
            success_lb = True
            if all_liquidity:
                for liquidity_item in all_liquidity:
                    if not self.db.insert_liquidity_balance(liquidity_item):
                        success_lb = False
                        logging.error(f"Échec de l'insertion pour l'enregistrement de liquidité : {liquidity_item}")

            if success_cf and success_pp and success_lb:
                logging.info("✅ Toutes les données PEA ont été chargées avec succès!")
                return True
            else:
                logging.error("❌ Échec de l'insertion des données PEA en base de données.")
                return False
                
        except Exception as e:
            logging.exception(f"❌ Erreur chargement PEA: {e}")
            return False

    def load_assurance_vie_data(self, file_path: str, user_id: str) -> bool:
        """
        Charger les données Assurance Vie
        Utilise le parser unifié
        """
        
        logging.info(f"🏛️  Chargement Assurance Vie pour utilisateur {user_id}")
        
        if not os.path.exists(file_path):
            logging.error(f"❌ Fichier AV non trouvé: {file_path}")
            return False
        
        try:
            # Utiliser le parser unifié
            parser = UnifiedPortfolioParser(user_id)
            
            logging.info("🔍 Parsing Assurance Vie...")
            investissements, flux_tresorerie = parser.parse_platform(file_path, 'assurance_vie')
            
            logging.info(f"📊 AV parsée: {len(investissements)} investissements, {len(flux_tresorerie)} flux")
            
            # Insérer en base
            success_inv = self.db.insert_investments(investissements) if investissements else True
            success_cf = self.db.insert_cash_flows(flux_tresorerie) if flux_tresorerie else True
            
            if success_inv and success_cf:
                logging.info("✅ Assurance Vie chargée avec succès")
                return True
            else:
                logging.error(f"❌ Échec insertion AV")
                return False
            
        except Exception as e:
            logging.exception(f"❌ Erreur chargement AV: {e}")
            return False
    
    def load_all_user_files(self, user_id: str, data_folder: str = "data/raw", platforms_to_load: Optional[List[str]] = None) -> bool:
        """[CORRIGÉ] Charge les fichiers pour un utilisateur, avec filtrage par plateforme."""
        logging.info(f"📂 Chargement complet pour utilisateur {user_id} depuis {data_folder}")
        if platforms_to_load:
            logging.info(f"Filtre appliqué pour les plateformes : {', '.join(platforms_to_load)}")

        fichiers_plateformes = {
            'lpb': 'Portefeuille LPB.xlsx',
            'pretup': 'Portefeuille PretUp.xlsx',
            'bienpreter': 'Portefeuille BienPreter.xlsx',
            'homunity': 'Portefeuille Homunity.xlsx',
            'assurance_vie': 'Portefeuille Linxea.xlsx'
        }
        
        success_count = 0
        
        # Charger les plateformes Excel
        for plateforme_key, filename in fichiers_plateformes.items():
            if platforms_to_load and plateforme_key not in platforms_to_load:
                continue # Ignorer si pas dans la liste demandée
            
            file_path = os.path.join(data_folder, filename)
            if os.path.exists(file_path):
                if self.load_platform_data(file_path, plateforme_key, user_id):
                    success_count += 1
            else:
                logging.warning(f"Fichier non trouvé pour {PLATFORM_MAPPING.get(plateforme_key.lower(), plateforme_key).upper()}: {file_path}")

        # Charger tous les fichiers du dossier PEA
        
        if not platforms_to_load or 'pea' in platforms_to_load:
            logging.info(f"[DEBUG] Entrée dans le bloc de chargement PEA.") # NOUVELLE LIGNE DE DEBUG
            pea_folder = os.path.join(data_folder, "pea")
            if os.path.exists(pea_folder):
                if self.load_all_pea_files(user_id, pea_folder):
                    success_count += 1
            else:
                logging.warning(f"⚠️  Dossier 'pea' non trouvé dans {data_folder}")

        logging.info(f"📋 RÉSUMÉ CHARGEMENT: {success_count} source(s) de données chargée(s) avec succès.")
        return success_count > 0
   
    def _validate_parsed_data(self, investissements: list, flux_tresorerie: list, platform_name: str) -> bool:
        """Valider les données parsées"""
        
        # Vérifications de base
        if not investissements and not flux_tresorerie:
            logging.warning(f"Aucune donnée parsée pour {platform_name}")
            return False
        
        # Vérifier structure investissements
        for inv in investissements:
            required_fields = ['id', 'user_id', 'platform', 'invested_amount']
            if not all(field in inv for field in required_fields):
                logging.warning(f"Structure investissement invalide pour {platform_name}")
                return False
        
        # Vérifier structure flux
        for flux in flux_tresorerie:
            required_fields = ['id', 'user_id', 'platform', 'flow_type', 'gross_amount']
            if not all(field in flux for field in required_fields):
                logging.warning(f"Structure flux invalide pour {platform_name}")
                return False
        
        return True
    
    def _display_loading_summary(self, user_id: str):
        """Afficher résumé des données chargées"""
        
        try:
            investments_df = self.db.get_user_investments(user_id)
            cash_flows_df = self.db.get_user_cash_flows(user_id)
            
            logging.info(f"Données chargées:")
            logging.info(f"  Investissements: {len(investments_df)}")
            logging.info(f"  Flux de trésorerie: {len(cash_flows_df)}")
            
            if not investments_df.empty:
                total_investi = investments_df['invested_amount'].sum()
                logging.info(f"  Total investi: {total_investi:,.0f} euros")
                
                # Par plateforme
                platform_summary = investments_df.groupby('platform')['invested_amount'].agg(['count', 'sum'])
                logging.info(f"Répartition par plateforme:")
                for platform, data in platform_summary.iterrows():
                    count, amount = data['count'], data['sum']
                    logging.info(f"  {platform}: {count} positions, {amount:,.0f} euros")
            
            if not cash_flows_df.empty and 'platform' in cash_flows_df.columns:
                logging.info(f"Flux par plateforme:")
                flux_summary = cash_flows_df.groupby('platform')['gross_amount'].agg(['count', 'sum'])
                for platform, data in flux_summary.iterrows():
                    count, amount = data['count'], data['sum']
                    logging.info(f"  {platform}: {count} flux, {amount:,.0f} euros (brut)")
        
        except Exception as e:
            logging.error(f"Erreur affichage résumé: {e}")

    def display_lpb_investment_details(self, user_id: str):
        """Affiche les détails des investissements LPB, y compris la date de fin réelle."""
        try:
            investments_df = self.db.get_user_investments(user_id)
            lpb_investments = investments_df[investments_df['platform'] == 'La Première Brique']

            if not lpb_investments.empty:
                logging.info("\n📊 Détails des investissements LPB (status, capital_repaid, actual_end_date):")
                for _, inv in lpb_investments.iterrows():
                    logging.info(f"  Projet: {inv['project_name']}")
                    logging.info(f"    Statut: {inv['status']}")
                    logging.info(f"    Montant investi: {inv['invested_amount']:.2f}€")
                    logging.info(f"    Capital remboursé: {inv['capital_repaid']:.2f}€")
                    logging.info(f"    Date de fin réelle: {inv['actual_end_date']}")
                    logging.info(f"    Date de fin prévue: {inv['expected_end_date']}")
            else:
                logging.info("Aucun investissement LPB trouvé pour l'utilisateur.")
        except Exception as e:
            logging.error(f"Erreur lors de l'affichage des détails LPB: {e}")
    
    def clear_user_data(self, user_id: str) -> bool:
        """Vider toutes les données utilisateur"""
        logging.info(f"Suppression données utilisateur {user_id}")
        try:
            return self.db.clear_user_data(user_id)
        except Exception as e:
            logging.error(f"Erreur suppression: {e}")
            return False
    
    def validate_all_files(self, data_folder: str = "data/raw", platforms_to_load: Optional[List[str]] = None) -> Dict:
        """
        [CORRIGÉ] Valider tous les fichiers avant chargement, avec filtre optionnel par plateforme.
        Retourne un rapport de validation.
        """
        
        logging.info(f"Validation des fichiers dans {data_folder}")
        if platforms_to_load:
            logging.info(f"Validation filtrée pour les plateformes : {', '.join(platforms_to_load)}")
        
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
        
        # Compter les fichiers attendus en fonction du filtre
        validation_report['total_files'] = len(platforms_to_load) if platforms_to_load else len(expected_files) + 1 # +1 pour PEA
        
        for platform_key, filename in expected_files.items():
            if platforms_to_load and platform_key not in platforms_to_load:
                continue # Ignorer si pas dans la liste demandée

            file_path = os.path.join(data_folder, filename)
            
            if os.path.exists(file_path):
                try:
                    # Test d'ouverture Excel
                    import pandas as pd
                    pd.read_excel(file_path, nrows=1)
                    
                    validation_report['valid_files'].append({
                        'platform': platform_key,
                        'filename': filename,
                        'path': file_path
                    })
                    validation_report['valid_count'] += 1
                    logging.info(f"Fichier valide: {PLATFORM_MAPPING.get(platform_key.lower(), platform_key).upper()}: {filename}")
                    
                except Exception as e:
                    validation_report['invalid_files'].append({
                        'platform': platform_key,
                        'filename': filename,
                        'error': str(e)
                    })
                    logging.error(f"Fichier corrompu: {PLATFORM_MAPPING.get(platform_key.lower(), platform_key).upper()} - {e}")
            else:
                validation_report['missing_files'].append({
                    'platform': platform_key,
                    'filename': filename
                })
                logging.warning(f"Fichier manquant: {PLATFORM_MAPPING.get(platform_key.lower(), platform_key).upper()}: {filename}")
        
        # Vérifier PEA uniquement si demandé ou si aucun filtre
         # NOUVELLE LIGNE DE DEBUG
        if not platforms_to_load or 'pea' in platforms_to_load:
            pea_folder = os.path.join(data_folder, "pea")
            if os.path.exists(pea_folder):
                pea_files = [f for f in os.listdir(pea_folder) if f.lower().endswith('.pdf')]
                if pea_files:
                    validation_report['pea_files'] = pea_files
                    logging.info(f"PEA: {len(pea_files)} fichier(s) PDF trouvé(s)")
                    if not platforms_to_load: # Si pas de filtre, on compte le PEA comme valide
                        validation_report['valid_count'] += 1
                else:
                    logging.warning("PEA: Aucun fichier PDF trouvé")
            else:
                logging.warning(f"⚠️  Dossier 'pea' non trouvé dans {data_folder}")
        
        logging.info(f"VALIDATION: {validation_report['valid_count']}/{validation_report['total_files']} fichiers valides")
        
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
            logging.error(f"Erreur résumé plateformes: {e}")
            return {}

def load_user_data_auto(user_id: str = Config.DEFAULT_USER_ID, data_folder: str = "data/raw"):
    """ Script automatique pour charger toutes vos données """
    
    print("🚀 CHARGEMENT AUTOMATIQUE DONNÉES PATRIMOINE")   
    print("=" * 50)
    
    # Créer le loader
    loader = DataLoader()
    
    # Validation des fichiers
    validation_report = loader.validate_all_files(data_folder)
    
    if validation_report['valid_count'] == 0:
        print("❌ Aucun fichier valide trouvé")
        return False
    
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
    user_id = sys.argv[1] if len(sys.argv) > 1 else Config.DEFAULT_USER_ID
    data_folder = sys.argv[2] if len(sys.argv) > 2 else "data/raw"
    
    load_user_data_auto(user_id, data_folder)