from backend.models.database import DatabaseManager
from backend.data.parsers import LBPParser, PretUpParser, BienPreterParser, HomunityParser
import os

class DataLoader:
    """Classe principale pour charger les données des différentes plateformes"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def load_platform_data(self, file_path: str, platform: str, user_id: str) -> bool:
        """Charger les données depuis un fichier de plateforme"""
        
        print(f"📥 Chargement des données {platform.upper()} pour l'utilisateur {user_id}")
        
        # Sélectionner le parser approprié
        if platform.lower() == 'lbp':
            parser = LBPParser(user_id)
        elif platform.lower() == 'pretup':
            parser = PretUpParser(user_id)
        elif platform.lower() == 'bienpreter':
            parser = BienPreterParser(user_id)
        elif platform.lower() == 'homunity':
            parser = HomunityParser(user_id)  # NOUVEAU
        else:
            print(f"❌ Parser non implémenté pour la plateforme: {platform}")
            return False
        
        try:
            # Parser les données
            print(f"🔍 Parsing du fichier: {file_path}")
            investissements, flux_tresorerie = parser.parse(file_path)
            
            print(f"📊 Données parsées: {len(investissements)} investissements, {len(flux_tresorerie)} flux de trésorerie")
            
            # Insérer en base de données
            succes_inv = self.db.insert_investments(investissements)
            succes_cf = self.db.insert_cash_flows(flux_tresorerie)
            
            if succes_inv and succes_cf:
                print(f"✅ Chargement réussi de {platform.upper()}")
                return True
            else:
                print(f"⚠️  Chargement partiel de {platform.upper()}")
                return False
            
        except Exception as e:
            print(f"❌ Erreur lors du chargement des données de {platform}: {e}")
            import traceback
            traceback.print_exc()
            return False
    
    def load_all_user_files(self, user_id: str, data_folder: str = "data/raw") -> bool:
        """Charger tous les fichiers depuis le dossier de données utilisateur"""
        
        fichiers_plateformes = {
            'lbp': 'Portefeuille LPB 20250529.xlsx',
            'pretup': 'Portefeuille PretUp 20250529.xlsx',
            'bienpreter': 'Portefeuille BienPreter 20250529.xlsx',
            'homunity': 'Portefeuille Homunity 20250529.xlsx'  # AJOUTÉ
        }
        
        succes_count = 0
        
        for plateforme, filename in fichiers_plateformes.items():
            file_path = os.path.join(data_folder, filename)
            if os.path.exists(file_path):
                print(f"\n📂 Traitement de {plateforme.upper()}...")
                if self.load_platform_data(file_path, plateforme, user_id):
                    succes_count += 1
                else:
                    print(f"❌ Échec du chargement de {plateforme}")
            else:
                print(f"⚠️  Fichier non trouvé: {file_path}")
        
        print(f"\n📋 Résumé: {succes_count}/{len(fichiers_plateformes)} plateformes chargées avec succès")
        return succes_count > 0
    
    def clear_user_data(self, user_id: str) -> bool:
        """Vider toutes les données d'un utilisateur (utile pour les tests)"""
        print(f"🗑️  Suppression des données de l'utilisateur {user_id}")
        return self.db.clear_user_data(user_id)
    
    def get_loading_summary(self, user_id: str) -> dict:
        """Obtenir un résumé des données chargées"""
        return self.db.get_platform_summary(user_id)

# ===== backend/models/database.py - MISE À JOUR POUR AUTHENTIFICATION SIMPLIFIÉE =====
from supabase import create_client, Client
import pandas as pd
from typing import List, Dict, Any, Optional
import uuid
import os
from dotenv import load_dotenv

# Charger les variables d'environnement
load_dotenv()

class DatabaseManager:
    """Gestionnaire de base de données Supabase avec authentification simplifiée"""
    
    def __init__(self):
        # Récupérer les identifiants depuis l'environnement
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_SERVICE_KEY") or os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL et SUPABASE_KEY doivent être définis dans le fichier .env")
        
        try:
            self.supabase: Client = create_client(
                self.supabase_url, 
                self.supabase_key
            )
            print("✅ Connexion à Supabase réussie")
        except Exception as e:
            raise ConnectionError(f"Échec de la connexion à Supabase: {e}")
    
    def test_connection(self) -> bool:
        """Tester la connexion à la base de données"""
        try:
            # Test simple avec count
            result = self.supabase.table('investments').select("count").limit(1).execute()
            return True
        except Exception as e:
            print(f"Test de connexion échoué: {e}")
            return False
    
    def insert_investments(self, investments: List[Dict[str, Any]]) -> bool:
        """Insérer plusieurs investissements"""
        if not investments:
            print("Aucun investissement à insérer")
            return True
            
        try:
            # Nettoyer les données avant insertion
            investments_clean = []
            for inv in investments:
                inv_clean = self._clean_investment_data(inv)
                if inv_clean:
                    investments_clean.append(inv_clean)
            
            if investments_clean:
                result = self.supabase.table('investments').insert(investments_clean).execute()
                print(f"✅ {len(investments_clean)} investissements insérés")
                return True
            else:
                print("⚠️  Aucun investissement valide à insérer")
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors de l'insertion des investissements: {e}")
            return False
    
    def insert_cash_flows(self, cash_flows: List[Dict[str, Any]]) -> bool:
        """Insérer plusieurs flux de trésorerie"""
        if not cash_flows:
            print("Aucun flux de trésorerie à insérer")
            return True
            
        try:
            # Nettoyer les données avant insertion
            cash_flows_clean = []
            for cf in cash_flows:
                cf_clean = self._clean_cash_flow_data(cf)
                if cf_clean:
                    cash_flows_clean.append(cf_clean)
            
            if cash_flows_clean:
                result = self.supabase.table('cash_flows').insert(cash_flows_clean).execute()
                print(f"✅ {len(cash_flows_clean)} flux de trésorerie insérés")
                return True
            else:
                print("⚠️  Aucun flux de trésorerie valide à insérer")  
                return False
                
        except Exception as e:
            print(f"❌ Erreur lors de l'insertion des flux de trésorerie: {e}")
            return False
    
    def _clean_investment_data(self, investment: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Nettoyer les données d'investissement avant insertion"""
        try:
            # Vérifier les champs obligatoires
            if not investment.get('investment_date'):
                print(f"⚠️  Date d'investissement manquante pour {investment.get('project_name', 'Projet inconnu')}")
                return None
            
            if not investment.get('invested_amount') or investment.get('invested_amount') <= 0:
                print(f"⚠️  Montant d'investissement invalide pour {investment.get('project_name', 'Projet inconnu')}")
                return None
            
            # Nettoyer et valider les données
            cleaned = {
                'id': investment.get('id', str(uuid.uuid4())),
                'user_id': investment.get('user_id'),
                'platform': investment.get('platform'),
                'platform_id': investment.get('platform_id'),
                'investment_type': investment.get('investment_type', 'crowdfunding'),
                'asset_class': investment.get('asset_class', 'real_estate'),
                'project_name': investment.get('project_name', ''),
                'company_name': investment.get('company_name', ''),
                'invested_amount': float(investment.get('invested_amount', 0)),
                'annual_rate': float(investment.get('annual_rate', 0)) if investment.get('annual_rate') else None,
                'investment_date': investment.get('investment_date'),
                'status': investment.get('status', 'active'),
                'created_at': investment.get('created_at'),
                'updated_at': investment.get('updated_at')
            }
            
            # Ajouter les champs optionnels seulement s'ils existent
            optional_fields = ['signature_date', 'expected_end_date', 'actual_end_date', 
                             'current_value', 'duration_months', 'sector', 'geographic_zone']
            
            for field in optional_fields:
                if investment.get(field):
                    cleaned[field] = investment[field]
            
            return cleaned
            
        except Exception as e:
            print(f"❌ Erreur lors du nettoyage des données d'investissement: {e}")
            return None
    
    def _clean_cash_flow_data(self, cash_flow: Dict[str, Any]) -> Optional[Dict[str, Any]]:
        """Nettoyer les données de flux de trésorerie avant insertion"""
        try:
            # Vérifier les champs obligatoires
            if not cash_flow.get('transaction_date'):
                print(f"⚠️  Date de transaction manquante pour {cash_flow.get('description', 'Transaction inconnue')}")
                return None
            
            if not cash_flow.get('gross_amount') or cash_flow.get('gross_amount') <= 0:
                print(f"⚠️  Montant invalide pour {cash_flow.get('description', 'Transaction inconnue')}")
                return None
            
            # Nettoyer et valider les données
            cleaned = {
                'id': cash_flow.get('id', str(uuid.uuid4())),
                'user_id': cash_flow.get('user_id'),
                'flow_type': cash_flow.get('flow_type', 'other'),
                'flow_direction': cash_flow.get('flow_direction', 'in'),
                'gross_amount': float(cash_flow.get('gross_amount', 0)),
                'net_amount': float(cash_flow.get('net_amount', 0)),
                'transaction_date': cash_flow.get('transaction_date'),
                'status': cash_flow.get('status', 'completed'),
                'description': cash_flow.get('description', ''),
                'created_at': cash_flow.get('created_at')
            }
            
            # Ajouter les champs optionnels
            optional_fields = ['investment_id', 'capital_amount', 'interest_amount', 
                             'fee_amount', 'tax_amount', 'expected_date', 'payment_method']
            
            for field in optional_fields:
                if cash_flow.get(field) is not None:
                    cleaned[field] = cash_flow[field]
            
            return cleaned
            
        except Exception as e:
            print(f"❌ Erreur lors du nettoyage des données de flux: {e}")
            return None
    
    def get_user_investments(self, user_id: str, platform: Optional[str] = None) -> pd.DataFrame:
        """Récupérer les investissements utilisateur sous forme de DataFrame"""
        try:
            query = self.supabase.table('investments').select("*").eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            
            result = query.execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                print(f"📊 {len(df)} investissements récupérés pour l'utilisateur {user_id}")
                return df
            else:
                print(f"Aucun investissement trouvé pour l'utilisateur {user_id}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des investissements: {e}")
            return pd.DataFrame()
    
    def get_user_cash_flows(self, user_id: str, start_date: Optional[str] = None) -> pd.DataFrame:
        """Récupérer les flux de trésorerie utilisateur sous forme de DataFrame"""
        try:
            query = self.supabase.table('cash_flows').select("*").eq('user_id', user_id)
            if start_date:
                query = query.gte('transaction_date', start_date)
            
            result = query.execute()
            
            if result.data:
                df = pd.DataFrame(result.data)
                print(f"💰 {len(df)} flux de trésorerie récupérés pour l'utilisateur {user_id}")
                return df
            else:
                print(f"Aucun flux de trésorerie trouvé pour l'utilisateur {user_id}")
                return pd.DataFrame()
                
        except Exception as e:
            print(f"❌ Erreur lors de la récupération des flux de trésorerie: {e}")
            return pd.DataFrame()
    
    def clear_user_data(self, user_id: str) -> bool:
        """Supprimer toutes les données d'un utilisateur (utile pour les tests)"""
        try:
            # Supprimer dans le bon ordre à cause des clés étrangères
            self.supabase.table('cash_flows').delete().eq('user_id', user_id).execute()
            self.supabase.table('portfolio_positions').delete().eq('user_id', user_id).execute()
            self.supabase.table('investments').delete().eq('user_id', user_id).execute()
            print(f"🗑️  Toutes les données supprimées pour l'utilisateur {user_id}")
            return True
        except Exception as e:
            print(f"❌ Erreur lors de la suppression des données: {e}")
            return False
    
    def get_platform_summary(self, user_id: str) -> Dict[str, Any]:
        """Obtenir des statistiques de résumé par plateforme"""
        try:
            investments_df = self.get_user_investments(user_id)
            cash_flows_df = self.get_user_cash_flows(user_id)
            
            summary = {}
            
            if not investments_df.empty:
                # Statistiques par plateforme
                platform_stats = investments_df.groupby('platform').agg({
                    'invested_amount': ['sum', 'count'],
                    'status': lambda x: (x == 'active').sum()
                }).round(2)
                
                summary['plateformes'] = platform_stats.to_dict()
                summary['total_investi'] = investments_df['invested_amount'].sum()
                summary['total_projets'] = len(investments_df)
            
            if not cash_flows_df.empty:
                cash_flows_df['transaction_date'] = pd.to_datetime(cash_flows_df['transaction_date'])
                entrees = cash_flows_df[cash_flows_df['flow_direction'] == 'in']['net_amount'].sum()
                sorties = abs(cash_flows_df[cash_flows_df['flow_direction'] == 'out']['net_amount'].sum())
                
                summary['total_entrees'] = entrees
                summary['total_sorties'] = sorties
                summary['performance_nette'] = entrees - sorties
            
            return summary
            
        except Exception as e:
            print(f"❌ Erreur lors de la génération du résumé: {e}")
            return {}

# Test function
def test_database_connection():
    """Fonction de test pour vérifier la configuration de la base de données"""
    try:
        print("🔍 Test de la connexion à la base de données...")
        db = DatabaseManager()
        
        if db.test_connection():
            print("✅ Connexion à la base de données réussie!")
            return True
        else:
            print("❌ Connexion à la base de données échouée!")
            return False
            
    except Exception as e:
        print(f"❌ Erreur de configuration de la base de données: {e}")
        return False

if __name__ == "__main__":
    # Tester la connexion lors de l'exécution directe de ce fichier
    test_database_connection()