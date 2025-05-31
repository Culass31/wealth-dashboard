# ===== backend/models/database.py - DATABASE MANAGER EXPERT =====
from supabase import create_client, Client
import pandas as pd
from typing import List, Dict, Any, Optional
import os
from dotenv import load_dotenv
from datetime import datetime

# Load environment variables
load_dotenv()

class ExpertDatabaseManager:
    """Gestionnaire de base de données expert avec support complet nouvelles fonctionnalités"""
    
    def __init__(self):
        # Get credentials from environment
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY") or os.getenv("SUPABASE_SERVICE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        
        try:
            self.supabase: Client = create_client(
                self.supabase_url, 
                self.supabase_key
            )
            print("✅ Connected to Supabase successfully")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Supabase: {e}")
    
    def test_connection(self) -> bool:
        """Test the database connection"""
        try:
            result = self.supabase.table('investments').select("count").limit(1).execute()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    # ===== MÉTHODES INVESTISSEMENTS =====
    
    def insert_investments(self, investments: List[Dict[str, Any]]) -> bool:
        """Insert multiple investments avec validation"""
        if not investments:
            return True
        
        try:
            # Validation des données
            for investment in investments:
                if not self._validate_investment(investment):
                    print(f"⚠️  Investment invalide ignoré: {investment.get('project_name', 'Unknown')}")
                    continue
            
            result = self.supabase.table('investments').insert(investments).execute()
            print(f"✅ Inserted {len(investments)} investments")
            return True
        except Exception as e:
            print(f"❌ Error inserting investments: {e}")
            return False
    
    def _validate_investment(self, investment: Dict[str, Any]) -> bool:
        """Valider un investissement avant insertion"""
        required_fields = ['id', 'user_id', 'platform', 'invested_amount']
        
        # Vérifier champs requis
        for field in required_fields:
            if field not in investment or investment[field] is None:
                print(f"⚠️  Champ manquant: {field}")
                return False
        
        # Vérifier montant positif
        if investment['invested_amount'] <= 0:
            print(f"⚠️  Montant invalide: {investment['invested_amount']}")
            return False
        
        # Vérifier plateforme valide
        valid_platforms = ['La Première Brique', 'PretUp', 'BienPrêter', 'Homunity', 'PEA', 'Assurance_Vie']
        if investment['platform'] not in valid_platforms:
            print(f"⚠️  Plateforme invalide: {investment['platform']}")
            return False
        
        return True
    
    def get_user_investments(self, user_id: str, platform: Optional[str] = None) -> pd.DataFrame:
        """Get user investments as DataFrame avec filtres"""
        try:
            query = self.supabase.table('investments').select("*").eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            result = query.execute()
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            print(f"❌ Error fetching investments: {e}")
            return pd.DataFrame()
    
    def update_investment_status(self, investment_id: str, status: str, actual_end_date: str = None) -> bool:
        """Mettre à jour le statut d'un investissement"""
        try:
            update_data = {'status': status, 'updated_at': 'now()'}
            if actual_end_date:
                update_data['actual_end_date'] = actual_end_date
            
            result = self.supabase.table('investments').update(update_data).eq('id', investment_id).execute()
            return True
        except Exception as e:
            print(f"❌ Error updating investment status: {e}")
            return False
    
    # ===== MÉTHODES CASH FLOWS =====
    
    def insert_cash_flows(self, cash_flows: List[Dict[str, Any]]) -> bool:
        """Insert multiple cash flows avec validation platform"""
        if not cash_flows:
            return True
        
        try:
            # Validation des données
            validated_flows = []
            for flow in cash_flows:
                if self._validate_cash_flow(flow):
                    validated_flows.append(flow)
                else:
                    print(f"⚠️  Cash flow invalide ignoré: {flow.get('description', 'Unknown')}")
            
            if validated_flows:
                result = self.supabase.table('cash_flows').insert(validated_flows).execute()
                print(f"✅ Inserted {len(validated_flows)} cash flows")
            return True
        except Exception as e:
            print(f"❌ Error inserting cash flows: {e}")
            return False
    
    def _validate_cash_flow(self, cash_flow: Dict[str, Any]) -> bool:
        """Valider un flux de trésorerie"""
        required_fields = ['id', 'user_id', 'platform', 'flow_type', 'flow_direction', 'gross_amount']
        
        # Vérifier champs requis
        for field in required_fields:
            if field not in cash_flow or cash_flow[field] is None:
                print(f"⚠️  Champ cash flow manquant: {field}")
                return False
        
        # Vérifier direction valide
        if cash_flow['flow_direction'] not in ['in', 'out']:
            print(f"⚠️  Direction invalide: {cash_flow['flow_direction']}")
            return False
        
        # Vérifier type valide
        valid_types = ['deposit', 'withdrawal', 'investment', 'repayment', 'interest', 'dividend', 'fee', 'sale', 'purchase', 'adjustment', 'other']
        if cash_flow['flow_type'] not in valid_types:
            print(f"⚠️  Type invalide: {cash_flow['flow_type']}")
            return False
        
        return True
    
    def get_user_cash_flows(self, user_id: str, start_date: Optional[str] = None, platform: Optional[str] = None) -> pd.DataFrame:
        """Get user cash flows as DataFrame avec filtres avancés"""
        try:
            query = self.supabase.table('cash_flows').select("*").eq('user_id', user_id)
            if start_date:
                query = query.gte('transaction_date', start_date)
            if platform:
                query = query.eq('platform', platform)
            result = query.execute()
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            print(f"❌ Error fetching cash flows: {e}")
            return pd.DataFrame()
    
    def get_platform_cash_flows(self, user_id: str, platform: str) -> pd.DataFrame:
        """Obtenir tous les flux d'une plateforme pour calculs TRI"""
        return self.get_user_cash_flows(user_id, platform=platform)
    
    # ===== MÉTHODES PORTFOLIO POSITIONS =====
    
    def insert_portfolio_positions(self, positions: List[Dict[str, Any]]) -> bool:
        """Insert portfolio positions (PEA/AV)"""
        if not positions:
            return True
        
        try:
            # Supprimer anciennes positions avant insertion
            if positions:
                user_id = positions[0]['user_id']
                platform = positions[0]['platform']
                self.supabase.table('portfolio_positions').delete().eq('user_id', user_id).eq('platform', platform).execute()
            
            result = self.supabase.table('portfolio_positions').insert(positions).execute()
            print(f"✅ Inserted {len(positions)} portfolio positions")
            return True
        except Exception as e:
            print(f"❌ Error inserting portfolio positions: {e}")
            return False
    
    def get_portfolio_positions(self, user_id: str, platform: Optional[str] = None) -> pd.DataFrame:
        """Obtenir les positions de portefeuille"""
        try:
            query = self.supabase.table('portfolio_positions').select("*").eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            result = query.execute()
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            print(f"❌ Error fetching portfolio positions: {e}")
            return pd.DataFrame()
    
    # ===== MÉTHODES EXPERT METRICS CACHE =====
    
    def cache_expert_metric(self, user_id: str, platform: Optional[str], metric_type: str, 
                          metric_value: float = None, metric_percentage: float = None, 
                          metric_json: Dict = None) -> bool:
        """Mettre en cache une métrique calculée"""
        try:
            cache_data = {
                'user_id': user_id,
                'platform': platform,
                'metric_type': metric_type,
                'metric_value': metric_value,
                'metric_percentage': metric_percentage,
                'metric_json': metric_json,
                'calculation_date': 'now()'
            }
            
            # Upsert (insert or update)
            result = self.supabase.table('expert_metrics_cache').upsert(cache_data).execute()
            return True
        except Exception as e:
            print(f"❌ Error caching metric: {e}")
            return False
    
    def get_cached_metric(self, user_id: str, platform: Optional[str], metric_type: str) -> Optional[Dict]:
        """Récupérer une métrique en cache"""
        try:
            query = self.supabase.table('expert_metrics_cache').select("*").eq('user_id', user_id).eq('metric_type', metric_type)
            if platform:
                query = query.eq('platform', platform)
            else:
                query = query.is_('platform', 'null')
            
            result = query.execute()
            return result.data[0] if result.data else None
        except Exception as e:
            print(f"❌ Error fetching cached metric: {e}")
            return None
    
    def clear_metrics_cache(self, user_id: str, platform: Optional[str] = None) -> bool:
        """Vider le cache des métriques"""
        try:
            query = self.supabase.table('expert_metrics_cache').delete().eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            query.execute()
            return True
        except Exception as e:
            print(f"❌ Error clearing metrics cache: {e}")
            return False
    
    # ===== MÉTHODES DE NETTOYAGE =====
    
    def clear_user_data(self, user_id: str) -> bool:
        """Supprimer toutes les données d'un utilisateur"""
        try:
            print(f"🗑️  Suppression données utilisateur {user_id}...")
            
            # Supprimer dans l'ordre (contraintes clés étrangères)
            tables = ['expert_metrics_cache', 'cash_flows', 'portfolio_positions', 'investments']
            
            for table in tables:
                try:
                    result = self.supabase.table(table).delete().eq('user_id', user_id).execute()
                    print(f"  ✅ {table}: supprimé")
                except Exception as e:
                    print(f"  ⚠️  {table}: erreur - {e}")
            
            print(f"✅ Données utilisateur {user_id} supprimées")
            return True
        except Exception as e:
            print(f"❌ Error clearing user data: {e}")
            return False
    
    def clear_platform_data(self, user_id: str, platform: str) -> bool:
        """Supprimer les données d'une plateforme spécifique"""
        try:
            print(f"🗑️  Suppression données {platform} pour utilisateur {user_id}...")
            
            # Supprimer par plateforme
            tables = ['expert_metrics_cache', 'cash_flows', 'portfolio_positions', 'investments']
            
            for table in tables:
                try:
                    result = self.supabase.table(table).delete().eq('user_id', user_id).eq('platform', platform).execute()
                    print(f"  ✅ {table}: {platform} supprimé")
                except Exception as e:
                    print(f"  ⚠️  {table}: erreur - {e}")
            
            return True
        except Exception as e:
            print(f"❌ Error clearing platform data: {e}")
            return False
        
    def get_database_stats(self) -> Dict:
        """Obtenir les statistiques de la base de données"""
        print("📊 Analyse de la base de données...")
        
        stats = {}
        tables = ['investments', 'cash_flows', 'portfolio_positions', 'financial_goals', 'user_preferences']
        
        total_records = 0
        
        for table in tables:
            try:
                # Compter les lignes
                result = self.supabase.table(table).select('id').execute()
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
                stats[table] = {'count': 0, 'error': str(e)}
        
        stats['total_records'] = total_records
        
        # Affichage
        print(f"\n📋 STATISTIQUES BASE DE DONNÉES:")
        print(f"   📊 Total enregistrements: {total_records}")
        
        for table, data in stats.items():
            if table != 'total_records':
                count = data.get('count', 0)
                users = data.get('sample_users', [])
                print(f"   📄 {table}: {count} lignes")
                if users:
                    print(f"      👤 Utilisateurs: {', '.join(str(u)[:8] + '...' for u in users)}")
        
        return stats

    def clear_all_data(self, confirm: bool = False) -> bool:
        """Supprimer TOUTES les données de TOUTES les tables"""
        if not confirm:
            print("❌ Confirmation requise : clear_all_data(confirm=True)")
            return False
        
        print("🗑️ SUPPRESSION TOTALE DE TOUTES LES DONNÉES...")
        
        try:
            # Obtenir tous les user_ids
            result_inv = self.supabase.table('investments').select('user_id').execute()
            result_cf = self.supabase.table('cash_flows').select('user_id').execute()
            
            user_ids = set()
            
            if result_inv.data:
                for row in result_inv.data:
                    if row.get('user_id'):
                        user_ids.add(row['user_id'])
            
            if result_cf.data:
                for row in result_cf.data:
                    if row.get('user_id'):
                        user_ids.add(row['user_id'])
            
            # Supprimer tous les utilisateurs
            success_count = 0
            for user_id in user_ids:
                if self.clear_user_data(str(user_id)):
                    success_count += 1
            
            # Nettoyage final
            tables = ['portfolio_positions', 'financial_goals', 'user_preferences']
            for table in tables:
                try:
                    self.supabase.table(table).delete().gte('id', '00000000-0000-0000-0000-000000000000').execute()
                except:
                    pass
            
            print(f"✅ {success_count} utilisateurs supprimés")
            return True
            
        except Exception as e:
            print(f"❌ Erreur suppression globale: {e}")
            return False

    def truncate_table(self, table_name: str, confirm: bool = False) -> bool:
        """Vider une table spécifique"""
        if not confirm:
            print(f"❌ Confirmation requise : truncate_table('{table_name}', confirm=True)")
            return False
        
        try:
            result = self.supabase.table(table_name).select('id').execute()
            count_before = len(result.data) if result.data else 0
            
            self.supabase.table(table_name).delete().gte('id', '00000000-0000-0000-0000-000000000000').execute()
            
            print(f"✅ Table '{table_name}': {count_before} lignes supprimées")
            return True
            
        except Exception as e:
            print(f"❌ Erreur truncate table '{table_name}': {e}")
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
                return summary
            else:
                return {}
        except Exception as e:
            print(f"❌ Error fetching platform summary: {e}")
            return {}
    
    def get_monthly_flows_summary(self, user_id: str, platform: Optional[str] = None) -> pd.DataFrame:
        """Obtenir un résumé des flux mensuels"""
        try:
            query = self.supabase.table('v_monthly_flows').select("*").eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            result = query.execute()
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            print(f"❌ Error fetching monthly flows: {e}")
            return pd.DataFrame()
    
    def get_concentration_analysis(self, user_id: str, platform: Optional[str] = None) -> pd.DataFrame:
        """Obtenir l'analyse de concentration"""
        try:
            query = self.supabase.table('v_concentration_analysis').select("*").eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            result = query.execute()
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            print(f"❌ Error fetching concentration analysis: {e}")
            return pd.DataFrame()
    
    # ===== MÉTHODES DE MAINTENANCE =====
    
    def update_delayed_status(self, user_id: str) -> bool:
        """Mettre à jour automatiquement les statuts de retard"""
        try:
            # Marquer comme retardé les projets actifs dont expected_end_date < aujourd'hui
            from datetime import datetime
            today = datetime.now().strftime('%Y-%m-%d')
            
            result = self.supabase.table('investments').update({
                'is_delayed': True,
                'updated_at': 'now()'
            }).eq('user_id', user_id).eq('status', 'active').lt('expected_end_date', today).execute()
            
            print(f"✅ Statuts de retard mis à jour")
            return True
        except Exception as e:
            print(f"❌ Error updating delayed status: {e}")
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
            
            return quality_report
        except Exception as e:
            print(f"❌ Error analyzing data quality: {e}")
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
            
            return export_data
        except Exception as e:
            print(f"❌ Error exporting user data: {e}")
            return {}

# ===== FACTORY FUNCTION =====
def get_database_manager():
    """Factory function pour obtenir le DatabaseManager"""
    return ExpertDatabaseManager()

# Alias pour compatibilité
DatabaseManager = ExpertDatabaseManager

# ===== TESTS =====
if __name__ == "__main__":
    print("🧪 Test du DatabaseManager Expert...")
    
    try:
        db = ExpertDatabaseManager()
        
        # Test de connexion
        if db.test_connection():
            print("✅ Connexion réussie")
        else:
            print("❌ Échec connexion")
        
        # Test avec user de test
        test_user_id = "test-user-123"
        
        # Analyser qualité données
        quality_report = db.analyze_data_quality(test_user_id)
        print(f"📊 Qualité données: {quality_report.get('overall_score', 0):.1f}%")
        
        # Résumé plateformes
        summary = db.get_platform_summary(test_user_id)
        print(f"🏢 Plateformes actives: {len(summary)}")
        
        print("✅ Tests terminés avec succès")
        
    except Exception as e:
        print(f"❌ Erreur tests: {e}")
        import traceback
        traceback.print_exc()