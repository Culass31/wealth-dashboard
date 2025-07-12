# ===== backend/models/database.py - DATABASE MANAGER EXPERT =====
from supabase import create_client, Client
import pandas as pd
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from datetime import datetime, date
from uuid import UUID, uuid4
import logging
from backend.data.parser_constants import PLATFORM_MAPPING

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ExpertDatabaseManager:
    """Gestionnaire de base de données expert avec support complet nouvelles fonctionnalités"""
    
    def __init__(self):
        # Get credentials from environment
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            logging.error("SUPABASE_URL et SUPABASE_KEY doivent être définis dans le fichier .env")
            raise ValueError("SUPABASE_URL et SUPABASE_KEY doivent être définis dans le fichier .env")
        
        try:
            self.supabase: Client = create_client(
                self.supabase_url, 
                self.supabase_key
            )
            logging.info("Connexion à Supabase réussie.")
        except Exception as e:
            logging.exception(f"Échec de la connexion à Supabase : {e}")
            raise ConnectionError(f"Échec de la connexion à Supabase : {e}")
    
    def test_connection(self) -> bool:
        """Test the database connection"""
        try:
            result = self.supabase.table('investments').select("count").limit(1).execute()
            logging.info("Test de connexion à la base de données réussi.")
            return True
        except Exception as e:
            logging.error(f"Échec du test de connexion à la base de données : {e}", exc_info=True)
            return False
    
    # ===== MÉTHODES INVESTISSEMENTS =====
    
    

# Import Pydantic models
from backend.models.models import InvestmentCreate, CashFlowCreate, PortfolioPositionCreate, ExpertMetricCacheCreate

# Load environment variables
load_dotenv()

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

class ExpertDatabaseManager:
    """Gestionnaire de base de données expert avec support complet nouvelles fonctionnalités"""
    
    def __init__(self):
        # Get credentials from environment
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            logging.error("SUPABASE_URL et SUPABASE_KEY doivent être définis dans le fichier .env")
            raise ValueError("SUPABASE_URL et SUPABASE_KEY doivent être définis dans le fichier .env")
        
        try:
            self.supabase: Client = create_client(
                self.supabase_url, 
                self.supabase_key
            )
            logging.info("Connexion à Supabase réussie.")
        except Exception as e:
            logging.exception(f"Échec de la connexion à Supabase : {e}")
            raise ConnectionError(f"Échec de la connexion à Supabase : {e}")
    
    def test_connection(self) -> bool:
        """Test the database connection"""
        try:
            result = self.supabase.table('investments').select("count").limit(1).execute()
            logging.info("Test de connexion à la base de données réussi.")
            return True
        except Exception as e:
            logging.error(f"Échec du test de connexion à la base de données : {e}", exc_info=True)
            return False
    
    # ===== MÉTHODES INVESTISSEMENTS =====
    
    def insert_investments(self, investments_data: List[Dict[str, Any]]) -> bool:
        """Insert multiple investments avec validation Pydantic"""
        if not investments_data:
            logging.info("Aucun investissement à insérer.")
            return True
        
        validated_investments = []
        for inv_data in investments_data:
            try:
                # Generate UUID if not provided (for new records)
                if 'id' not in inv_data or inv_data['id'] is None:
                    inv_data['id'] = str(uuid4())
                
                investment = InvestmentCreate(**inv_data)
                validated_investments.append(investment.model_dump(mode='json')) # Use model_dump for Pydantic v2
            except Exception as e:
                logging.warning(f"Investissement invalide ignoré : {inv_data.get('project_name', 'Inconnu')} - Erreur: {e}")
                continue
        
        if not validated_investments:
            logging.info("Aucun investissement valide à insérer.")
            return True
            
        try:
            result = self.supabase.table('investments').insert(validated_investments).execute()
            logging.info(f"{len(validated_investments)} investissements insérés avec succès.")
            return True
        except Exception as e:
            logging.error(f"Erreur lors de l'insertion des investissements : {e}", exc_info=True)
            return False
    
    def get_user_investments(self, user_id: str, platform: Optional[str] = None) -> pd.DataFrame:
        """Get user investments as DataFrame avec filtres"""
        try:
            query = self.supabase.table('investments').select("*").eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            result = query.execute()
            logging.info(f"Récupération de {len(result.data) if result.data else 0} investissements pour l'utilisateur {user_id}.")
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des investissements pour l'utilisateur {user_id} : {e}", exc_info=True)
            return pd.DataFrame()
    
    def update_investment_status(self, investment_id: str, status: str, actual_end_date: Optional[datetime.date] = None) -> bool:
        """Mettre à jour le statut d'un investissement"""
        try:
            update_data = {'status': status, 'updated_at': datetime.now().isoformat()}
            if actual_end_date:
                update_data['actual_end_date'] = actual_end_date.isoformat() # Convert date to ISO format
            
            result = self.supabase.table('investments').update(update_data).eq('id', investment_id).execute()
            logging.info(f"Statut de l'investissement {investment_id} mis à jour à {status}.")
            return True
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour du statut de l'investissement {investment_id} : {e}", exc_info=True)
            return False
    
    # ===== MÉTHODES CASH FLOWS =====
    
    def insert_cash_flows(self, cash_flows_data: List[Dict[str, Any]]) -> bool:
        """Insert multiple cash flows avec validation Pydantic"""
        if not cash_flows_data:
            logging.info("Aucun flux de trésorerie à insérer.")
            return True
        
        validated_flows = []
        for flow_data in cash_flows_data:
            try:
                # Generate UUID if not provided
                if 'id' not in flow_data or flow_data['id'] is None:
                    flow_data['id'] = str(uuid4())
                
                cash_flow = CashFlowCreate(**flow_data)
                validated_flows.append(cash_flow.model_dump(mode='json'))
            except Exception as e:
                logging.warning(f"Flux de trésorerie invalide ignoré : {flow_data.get('description', 'Inconnu')} - Erreur: {e}")
                continue
        
        if not validated_flows:
            logging.info("Aucun flux de trésorerie valide à insérer.")
            return True
            
        try:
            result = self.supabase.table('cash_flows').insert(validated_flows).execute()
            logging.info(f"{len(validated_flows)} flux de trésorerie insérés avec succès.")
            return True
        except Exception as e:
            logging.error(f"Erreur lors de l'insertion des flux de trésorerie : {e}", exc_info=True)
            return False
    
    def get_user_cash_flows(self, user_id: str, start_date: Optional[str] = None, platform: Optional[str] = None) -> pd.DataFrame:
        """Get user cash flows as DataFrame avec filtres avancés"""
        try:
            query = self.supabase.table('cash_flows').select("*").eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            result = query.execute()
            logging.info(f"Récupération de {len(result.data) if result.data else 0} flux de trésorerie pour l'utilisateur {user_id}.")
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des flux de trésorerie pour l'utilisateur {user_id} : {e}", exc_info=True)
            return pd.DataFrame()
    
    def get_platform_cash_flows(self, user_id: str, platform: str) -> pd.DataFrame:
        """Obtenir tous les flux d'une plateforme pour calculs TRI"""
        return self.get_user_cash_flows(user_id, platform=platform)
    
    # ===== MÉTHODES PORTFOLIO POSITIONS =====
    def insert_portfolio_positions(self, positions_data: List[Dict[str, Any]]) -> bool:
        """Insert portfolio positions (PEA/AV) avec validation Pydantic"""
        if not positions_data:
            logging.info("Aucune position de portefeuille à insérer.")
            return True
        
        validated_positions = []
        for pos_data in positions_data:
            try:
                # Generate UUID if not provided
                if 'id' not in pos_data or pos_data['id'] is None:
                    pos_data['id'] = str(uuid4())
                
                position = PortfolioPositionCreate(**pos_data)
                validated_positions.append(position.model_dump(mode='json'))
            except Exception as e:
                logging.warning(f"Position de portefeuille invalide ignorée : {pos_data.get('asset_name', 'Inconnu')} - Erreur: {e}")
                continue
        
        if not validated_positions:
            logging.info("Aucune position de portefeuille valide à insérer.")
            return True
            
        try:
            # Supprimer anciennes positions avant insertion si user_id et platform sont présents
            if validated_positions:
                user_id = validated_positions[0]['user_id']
                platform = validated_positions[0]['platform']
                # This delete is commented out in the original code, uncomment if desired behavior
                # self.supabase.table('portfolio_positions').delete().eq('user_id', user_id).eq('platform', platform).execute()
            
            result = self.supabase.table('portfolio_positions').insert(validated_positions).execute()
            logging.info(f"{len(validated_positions)} positions de portefeuille insérées avec succès.")
            return True
        except Exception as e:
            logging.error(f"Erreur lors de l'insertion des positions de portefeuille : {e}", exc_info=True)
            return False
    
    def get_portfolio_positions(self, user_id: str, platform: Optional[str] = None) -> pd.DataFrame:
        """Obtenir les positions de portefeuille"""
        try:
            query = self.supabase.table('portfolio_positions').select("*").eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            result = query.execute()
            logging.info(f"Récupération de {len(result.data) if result.data else 0} positions de portefeuille pour l'utilisateur {user_id}.")
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des positions de portefeuille pour l'utilisateur {user_id} : {e}", exc_info=True)
            return pd.DataFrame()
    
    # ===== MÉTHODES LIQUIDITY BALANCES =====
    def insert_liquidity_balance(self, balance_data: Dict[str, Any]) -> bool:
        """Insert ou upsert une entrée de solde de liquidités"""
        if not balance_data:
            logging.info("Aucune donnée de solde de liquidités à insérer.")
            return True
        
        try:
            # Generate UUID if not provided
            if 'id' not in balance_data or balance_data['id'] is None:
                balance_data['id'] = str(uuid4())
            
            # Validate with Pydantic model
            from backend.models.models import LiquidityBalanceCreate # Import local pour éviter les imports circulaires
            balance_entry = LiquidityBalanceCreate(**balance_data)
            
            # Upsert (insert or update) based on user_id, platform, and balance_date
            result = self.supabase.table('liquidity_balances').upsert(balance_entry.model_dump(mode='json')).execute()
            logging.info(f"Solde de liquidités pour {balance_data.get('platform')} à {balance_data.get('balance_date')} inséré/mis à jour.")
            return True
        except Exception as e:
            logging.error(f"Erreur lors de l'insertion/mise à jour du solde de liquidités : {e}", exc_info=True)
            return False

    def get_liquidity_balances(self, user_id: str, platform: Optional[str] = None) -> pd.DataFrame:
        """Obtenir les soldes de liquidités"""
        try:
            query = self.supabase.table('liquidity_balances').select("*").eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            result = query.execute()
            logging.info(f"Récupération de {len(result.data) if result.data else 0} soldes de liquidités pour l'utilisateur {user_id}.")
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des soldes de liquidités pour l'utilisateur {user_id} : {e}", exc_info=True)
            return pd.DataFrame()

    # ===== MÉTHODES EXPERT METRICS CACHE =====
    def cache_expert_metric(self, user_id: str, metric_type: str, 
                          platform: Optional[str] = None, metric_value: Optional[float] = None, 
                          metric_percentage: Optional[float] = None, 
                          metric_json: Optional[Dict] = None) -> bool:
        """Mettre en cache une métrique calculée avec validation Pydantic"""
        try:
            cache_data = {
                'user_id': user_id,
                'platform': platform,
                'metric_type': metric_type,
                'metric_value': metric_value,
                'metric_percentage': metric_percentage,
                'metric_json': metric_json,
                'calculation_date': datetime.now().isoformat()
            }
            
            # Validate with Pydantic model
            metric_entry = ExpertMetricCacheCreate(**cache_data)
            
            # Upsert (insert or update)
            result = self.supabase.table('expert_metrics_cache').upsert(metric_entry.model_dump(mode='json')).execute()
            logging.info(f"Métrique {metric_type} mise en cache pour l'utilisateur {user_id} et la plateforme {platform}.")
            return True
        except Exception as e:
            logging.error(f"Erreur lors de la mise en cache de la métrique {metric_type} pour l'utilisateur {user_id} : {e}", exc_info=True)
            return False
    
    def get_cached_metric(self, user_id: str, metric_type: str, platform: Optional[str] = None) -> Optional[Dict]:
        """Récupérer une métrique en cache"""
        try:
            query = self.supabase.table('expert_metrics_cache').select("*").eq('user_id', user_id).eq('metric_type', metric_type)
            if platform:
                query = query.eq('platform', platform)
            else:
                query = query.is_('platform', 'null')
            
            result = query.execute()
            if result.data:
                logging.info(f"Métrique {metric_type} récupérée du cache pour l'utilisateur {user_id}.")
                return result.data[0]
            else:
                logging.info(f"Aucune métrique {metric_type} trouvée dans le cache pour l'utilisateur {user_id}.")
                return None
        except Exception as e:
            logging.error(f"Erreur lors de la récupération de la métrique {metric_type} pour l'utilisateur {user_id} : {e}", exc_info=True)
            return None
    
    def clear_metrics_cache(self, user_id: str, platform: Optional[str] = None) -> bool:
        """Vider le cache des métriques"""
        try:
            query = self.supabase.table('expert_metrics_cache').delete().eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            query.execute()
            logging.info(f"Cache des métriques vidé pour l'utilisateur {user_id} et la plateforme {platform if platform else 'toutes'}.")
            return True
        except Exception as e:
            logging.error(f"Erreur lors du vidage du cache des métriques pour l'utilisateur {user_id} : {e}", exc_info=True)
            return False
    
    # ===== MÉTHODES DE NETTOYAGE =====
    def clear_user_data(self, user_id: str) -> bool:
        """Supprimer toutes les données d'un utilisateur"""
        try:
            logging.info(f"Suppression de toutes les données pour l'utilisateur {user_id}...")
            
            # Supprimer dans l'ordre (contraintes clés étrangères)
            tables = ['expert_metrics_cache', 'cash_flows', 'portfolio_positions', 'investments']
            
            for table in tables:
                try:
                    result = self.supabase.table(table).delete().eq('user_id', user_id).execute()
                    logging.info(f"Données de la table {table} supprimées avec succès pour l'utilisateur {user_id}.")
                except Exception as e:
                    logging.error(f"Erreur lors de la suppression des données de la table {table} pour l'utilisateur {user_id} : {e}", exc_info=True)
            
            logging.info(f"Toutes les données pour l'utilisateur {user_id} ont été supprimées.")
            return True
        except Exception as e:
            logging.error(f"Erreur lors de la suppression des données utilisateur pour {user_id} : {e}", exc_info=True)
            return False
    
    def clear_platform_data(self, user_id: str, platform_key: str) -> bool:
        """
        [NOUVEAU] Supprime toutes les données d'une plateforme spécifique pour un utilisateur.
        Ceci inclut les investissements, les flux, le cache et les liquidités.
        """
        if not user_id or not platform_key:
            logging.error("User ID et nom de la plateforme sont requis.")
            return False

        platform_name = PLATFORM_MAPPING.get(platform_key.lower(), platform_key)
        logging.info(f"Début de la suppression des données pour la plateforme '{platform_name}'...")
        
        # L'ordre est important pour respecter les contraintes de clés étrangères
        tables_to_clear = [
            "cash_flows",
            "expert_metrics_cache",
            "liquidity_balances",
            "portfolio_positions",
            "investments"
        ]

        all_successful = True
        for table in tables_to_clear:
            try:
                logging.info(f"Suppression des données de la table '{table}' pour la plateforme '{platform_name}'...")
                result = self.supabase.table(table).delete().eq('user_id', user_id).eq('platform', platform_name).execute()
                
                # La réponse de Supabase contient les données supprimées dans `data`
                if result.data:
                    logging.info(f"-> {len(result.data)} enregistrements supprimés de '{table}'.")
                else:
                    logging.info(f"-> Aucune donnée à supprimer dans '{table}' pour cette plateforme.")

            except Exception as e:
                logging.error(f"Erreur lors de la suppression dans la table '{table}' pour la plateforme '{platform_name}': {e}", exc_info=True)
                all_successful = False
        
        if all_successful:
            logging.info(f"✅ Suppression des données pour la plateforme '{platform_name}' terminée.")
        else:
            logging.error(f"❌ Échec de la suppression complète des données pour la plateforme '{platform_name}'.")

        return all_successful
        
    def get_database_stats(self) -> Dict:
        """Obtenir les statistiques de la base de données"""
        logging.info("Analyse des statistiques de la base de données...")
        
        stats = {}
        tables = ['investments', 'cash_flows', 'portfolio_positions', 'financial_goals', 'user_preferences']
        
        total_records = 0
        
        for table in tables:
            try:
                # Compter les lignes
                select_column = 'user_id' if table == 'user_preferences' else 'id'
                result = self.supabase.table(table).select(select_column).execute()
                count = len(result.data) if result.data else 0
                
                # Obtenir quelques user_ids échantillons
                sample_result = self.supabase.table(table).select("user_id").limit(5).execute()
                sample_users = []
                if sample_result.data:
                    sample_users = list(set(row.get('user_id', 'N/A') for row in sample_result.data if row.get('user_id')))
                
                stats[table] = {
                    'count': count,
                    'sample_users': sample_users[:3]  # Max 3 user_ids
                }
                
                total_records += count
                
            except Exception as e:
                logging.error(f"Erreur lors de la récupération des statistiques pour la table {table} : {e}", exc_info=True)
                stats[table] = {'count': 0, 'error': str(e)}
        
        stats['total_records'] = total_records
        
        # Affichage
        logging.info(f"\nSTATISTIQUES DE LA BASE DE DONNÉES:")
        logging.info(f"   Total des enregistrements : {total_records}")
        
        for table, data in stats.items():
            if table != 'total_records':
                count = data.get('count', 0)
                users = data.get('sample_users', [])
                logging.info(f"   {table} : {count} lignes")
                if users:
                    logging.info(f"      Utilisateurs : {', '.join(str(u)[:8] + '...' for u in users)}")
        
        return stats

    def clear_all_data(self, confirm: bool = False) -> bool:
        """Supprimer TOUTES les données de TOUTES les tables, en gérant les cas particuliers."""
        if not confirm:
            logging.warning("Confirmation requise : clear_all_data(confirm=True)")
            return False
        
        logging.warning("SUPPRESSION TOTALE DE TOUTES LES DONNÉES...")
        
        all_successful = True
        
        # L'ordre est important à cause des clés étrangères (foreign keys)
        # Supprimer d'abord les tables dépendantes
        tables_to_clear_by_id = [
            'expert_metrics_cache', 
            'cash_flows', 
            'portfolio_positions', 
            'investments', 
            'financial_goals',
            'liquidity_balances'
        ]

        for table in tables_to_clear_by_id:
            try:
                logging.info(f"Vidage de la table {table} (par 'id')...")
                self.supabase.table(table).delete().neq('id', '00000000-0000-0000-0000-000000000000').execute()
                logging.info(f"Table {table} vidée avec succès.")
            except Exception as e:
                logging.error(f"Erreur lors du vidage de la table {table} : {e}", exc_info=True)
                all_successful = False

        # Cas particulier pour user_preferences qui utilise 'user_id' comme clé primaire
        try:
            logging.info(f"Vidage de la table user_preferences (par 'user_id')...")
            self.supabase.table('user_preferences').delete().neq('user_id', '00000000-0000-0000-0000-000000000000').execute()
            logging.info("Table user_preferences vidée avec succès.")
        except Exception as e:
            logging.error(f"Erreur lors du vidage de la table user_preferences : {e}", exc_info=True)
            all_successful = False
        
        if all_successful:
            logging.info("Toutes les tables ont été vidées avec succès.")
        else:
            logging.warning("Certaines tables n'ont pas pu être vidées complètement.")
            
        return all_successful

    def truncate_table(self, table_name: str, confirm: bool = False) -> bool:
        """Vider une table spécifique"""
        if not confirm:
            logging.warning(f"Confirmation requise : truncate_table('{table_name}', confirm=True)")
            return False
        
        try:
            result = self.supabase.table(table_name).select('id').execute()
            count_before = len(result.data) if result.data else 0
            
            self.supabase.table(table_name).delete().gte('id', '00000000-0000-0000-0000-000000000000').execute()
            
            logging.info(f"Table '{table_name}' : {count_before} lignes supprimées.")
            return True
            
        except Exception as e:
            logging.error(f"Erreur lors du vidage de la table '{table_name}' : {e}", exc_info=True)
            return False
    
    # ===== MÉTHODES D'ANALYSE =====
    
    def get_platform_summary(self, user_id: str) -> Dict:
        """Obtenir un résumé par plateforme"""
        try:
            # Utiliser la vue créée dans le schéma
            result = self.supabase.table('v_platform_summary').select("*").eq('user_id', user_id).execute()
            
            if result.data:
                summary = {}
                for row in result.data:
                    platform = row['platform']
                    summary[platform] = {
                        'nb_investments': row['nb_investments'],
                        'total_invested': row['total_invested'],
                        'avg_investment': row['avg_investment'],
                        'total_current_value': row['total_current_value'],
                        'active_count': row['active_count'],
                        'completed_count': row['completed_count'],
                        'delayed_count': row['delayed_count'],
                        'avg_duration_months': row['avg_duration_months'],
                        'short_term_count': row['short_term_count']
                    }
                logging.info(f"Résumé de la plateforme récupéré pour l'utilisateur {user_id}.")
                return summary
            else:
                logging.info(f"Aucun résumé de plateforme trouvé pour l'utilisateur {user_id}.")
                return {}
        except Exception as e:
            logging.error(f"Erreur lors de la récupération du résumé de la plateforme pour l'utilisateur {user_id} : {e}", exc_info=True)
            return {}
    
    def get_monthly_flows_summary(self, user_id: str, platform: Optional[str] = None) -> pd.DataFrame:
        """Obtenir un résumé des flux mensuels"""
        try:
            query = self.supabase.table('v_monthly_flows').select("*").eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            result = query.execute()
            logging.info(f"Récupération de {len(result.data) if result.data else 0} flux mensuels pour l'utilisateur {user_id}.")
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des flux mensuels pour l'utilisateur {user_id} : {e}", exc_info=True)
            return pd.DataFrame()
    
    def get_concentration_analysis(self, user_id: str, platform: Optional[str] = None) -> pd.DataFrame:
        """Obtenir l'analyse de concentration"""
        try:
            query = self.supabase.table('v_concentration_analysis').select("*").eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            result = query.execute()
            logging.info(f"Récupération de {len(result.data) if result.data else 0} enregistrements d'analyse de concentration pour l'utilisateur {user_id}.")
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            logging.error(f"Erreur lors de la récupération de l'analyse de concentration pour l'utilisateur {user_id} : {e}", exc_info=True)
            return {}
    
    # ===== MÉTHODES DE MAINTENANCE =====
    def update_delayed_status(self, user_id: str) -> bool:
        """Mettre à jour automatiquement les statuts de retard"""
        try:
            today = datetime.now().strftime('%Y-%m-%d')
            
            result = self.supabase.table('investments').update({
                'is_delayed': True,
                'updated_at': datetime.now().isoformat()
            }).eq('user_id', user_id).eq('status', 'active').lt('expected_end_date', today).execute()
            
            logging.info(f"Statuts de retard mis à jour pour l'utilisateur {user_id}.")
            return True
        except Exception as e:
            logging.error(f"Erreur lors de la mise à jour du statut de retard pour l'utilisateur {user_id} : {e}", exc_info=True)
            return False
    
    def analyze_data_quality(self, user_id: str) -> Dict:
        """Analyser la qualité des données"""
        try:
            quality_report = {
                'investments': {},
                'cash_flows': {},
                'overall_score': 0
            }
            
            # Analyser investissements
            investments_df = self.get_user_investments(user_id)
            if not investments_df.empty:
                quality_report['investments'] = {
                    'total_records': len(investments_df),
                    'missing_dates': investments_df['investment_date'].isna().sum(),
                    'missing_amounts': investments_df['invested_amount'].isna().sum(),
                    'missing_platforms': investments_df['platform'].isna().sum(),
                    'data_completeness': (1 - (investments_df.isna().sum().sum() / (len(investments_df) * len(investments_df.columns)))) * 100
                }
            
            # Analyser cash flows
            cash_flows_df = self.get_user_cash_flows(user_id)
            if not cash_flows_df.empty:
                quality_report['cash_flows'] = {
                    'total_records': len(cash_flows_df),
                    'missing_platforms': cash_flows_df['platform'].isna().sum() if 'platform' in cash_flows_df.columns else len(cash_flows_df),
                    'missing_dates': cash_flows_df['transaction_date'].isna().sum(),
                    'missing_amounts': cash_flows_df['gross_amount'].isna().sum(),
                    'data_completeness': (1 - (cash_flows_df.isna().sum().sum() / (len(cash_flows_df) * len(cash_flows_df.columns)))) * 100
                }
            
            # Score global
            inv_score = quality_report['investments'].get('data_completeness', 0)
            cf_score = quality_report['cash_flows'].get('data_completeness', 0)
            quality_report['overall_score'] = (inv_score + cf_score) / 2
            
            logging.info(f"Analyse de la qualité des données pour l'utilisateur {user_id} terminée. Score global : {quality_report['overall_score']:.1f}%")
            return quality_report
        except Exception as e:
            logging.error(f"Erreur lors de l'analyse de la qualité des données pour l'utilisateur {user_id} : {e}", exc_info=True)
            return {}
    
    # ===== MÉTHODES DE BACKUP =====
    def export_user_data(self, user_id: str, format: str = 'json') -> Dict:
        """Exporter toutes les données utilisateur"""
        try:
            export_data = {
                'user_id': user_id,
                'export_date': datetime.now().isoformat(),
                'investments': self.get_user_investments(user_id).to_dict('records'),
                'cash_flows': self.get_user_cash_flows(user_id).to_dict('records'),
                'portfolio_positions': self.get_portfolio_positions(user_id).to_dict('records')
            }
            logging.info(f"Données exportées pour l'utilisateur {user_id}.")
            return export_data
        except Exception as e:
            logging.error(f"Erreur lors de l'exportation des données pour l'utilisateur {user_id} : {e}", exc_info=True)
            return {}

# ===== FACTORY FUNCTION =====
def get_database_manager():
    """Factory function pour obtenir le DatabaseManager"""
    return ExpertDatabaseManager()

# Alias pour compatibilité
DatabaseManager = ExpertDatabaseManager

# ===== TESTS =====
if __name__ == "__main__":
    logging.info("Démarrage des tests du DatabaseManager Expert...")
    
    try:
        db = ExpertDatabaseManager()
        
        # Test de connexion
        if db.test_connection():
            logging.info("Test de connexion réussi.")
        else:
            logging.error("Test de connexion échoué.")
        
        # Test avec user de test
        test_user_id = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e" # Use a valid UUID for testing
        
        # Example data for insertion
        sample_investment = {
            "user_id": test_user_id,
            "platform": "PEA",
            "investment_type": "stocks",
            "invested_amount": 1000.00,
            "investment_date": "2023-01-01",
            "project_name": "Test Stock",
            "company_name": "TestCo",
            "isin": "FR0000000000"
        }
        
        sample_cash_flow = {
            "user_id": test_user_id,
            "platform": "PEA",
            "flow_type": "deposit",
            "flow_direction": "in",
            "gross_amount": 500.00,
            "transaction_date": "2023-01-05",
            "description": "Initial deposit"
        }
        
        sample_position = {
            "user_id": test_user_id,
            "platform": "PEA",
            "asset_name": "Test Asset",
            "valuation_date": "2023-12-31",
            "quantity": 10.0,
            "current_price": 100.0,
            "market_value": 1000.0
        }
        
        # Clear existing data for test user
        db.clear_user_data(test_user_id)
        
        # Insert sample data
        db.insert_investments([sample_investment])
        db.insert_cash_flows([sample_cash_flow])
        db.insert_portfolio_positions([sample_position])
        
        # Get and log data
        investments = db.get_user_investments(test_user_id)
        cash_flows = db.get_user_cash_flows(test_user_id)
        positions = db.get_portfolio_positions(test_user_id)
        
        logging.info(f"Investments for {test_user_id}:\n{investments}")
        logging.info(f"Cash Flows for {test_user_id}:\n{cash_flows}")
        logging.info(f"Portfolio Positions for {test_user_id}:\n{positions}")
        
        # Cache and retrieve a metric
        db.cache_expert_metric(test_user_id, "test_metric", platform="PEA", metric_value=123.45)
        cached_metric = db.get_cached_metric(test_user_id, "test_metric", platform="PEA")
        logging.info(f"Cached metric: {cached_metric}")
        
        # Analyser qualité données
        quality_report = db.analyze_data_quality(test_user_id)
        logging.info(f"Qualité des données : {quality_report.get('overall_score', 0):.1f}%")
        
        # Résumé plateformes
        summary = db.get_platform_summary(test_user_id)
        logging.info(f"Plateformes actives : {len(summary)}")
        
        logging.info("Tous les tests sont terminés avec succès.")
        
    except Exception as e:
        logging.exception(f"Erreur lors des tests : {e}")