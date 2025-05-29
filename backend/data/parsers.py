import pandas as pd
from typing import List, Dict, Any, Tuple
from datetime import datetime
import uuid
from backend.utils.file_helpers import standardize_date, clean_amount, safe_get

class PlatformParser:
    """Classe de base pour les parsers de plateformes"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def parse(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Parser le fichier et retourner (investissements, flux_tresorerie)"""
        raise NotImplementedError

class LBPParser(PlatformParser):
    """Parser pour les fichiers de la plateforme LBP"""
    
    def parse(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        try:
            # Lire le fichier Excel
            excel_file = pd.ExcelFile(file_path)
            
            # Parser les onglets projets et relevé de compte
            projects_df = pd.read_excel(file_path, sheet_name='Projets')
            account_df = pd.read_excel(file_path, sheet_name='Relevé compte')
            
            investissements = self._parse_projects(projects_df)
            flux_tresorerie = self._parse_account(account_df)
            
            return investissements, flux_tresorerie
        except Exception as e:
            print(f"❌ Erreur lors du parsing LBP: {e}")
            return [], []
    
    def _parse_projects(self, df: pd.DataFrame) -> List[Dict]:
        investissements = []
        
        for idx, row in df.iterrows():
            # Ignorer les lignes d'en-tête et vides
            if pd.isna(safe_get(row, 1)) or safe_get(row, 1) == "Nom du projet":
                continue
                
            # Parser la date d'investissement avec vérification
            date_collecte = safe_get(row, 0)
            date_investissement = standardize_date(date_collecte)
            
            # Si la date est nulle, utiliser une date par défaut ou ignorer
            if not date_investissement:
                print(f"⚠️  Date d'investissement manquante pour {safe_get(row, 1)}, utilisation date par défaut")
                date_investissement = "2022-01-01"  # Date par défaut
            
            investissement = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'LBP',
                'platform_id': f"LBP_{idx}",
                'investment_type': 'crowdfunding',
                'asset_class': 'real_estate',
                
                # Informations du projet
                'project_name': safe_get(row, 1, ''),  # Nom du projet
                'company_name': safe_get(row, 1, ''),  # Même que le projet pour LBP
                
                # Données financières
                'invested_amount': clean_amount(safe_get(row, 3, 0)),  # Montant investi
                'annual_rate': safe_get(row, 4, 0),  # Taux annuel
                
                # Dates avec vérifications
                'investment_date': date_investissement,
                'signature_date': standardize_date(safe_get(row, 5)),
                'expected_end_date': standardize_date(safe_get(row, 7)),
                'actual_end_date': standardize_date(safe_get(row, 8)),
                
                # Mapping du statut
                'status': self._map_lbp_status(safe_get(row, 2, '')),
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investissements.append(investissement)
        
        return investissements
    
    def _map_lbp_status(self, status: str) -> str:
        """Mapper le statut LBP vers un statut standardisé"""
        mapping_statut = {
            'Finalisée': 'completed',
            'Remboursée': 'completed', 
            'En cours': 'active',
            'Retard': 'delayed'
        }
        return mapping_statut.get(status, 'active')
    
    def _parse_account(self, df: pd.DataFrame) -> List[Dict]:
        flux_tresorerie = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Nature de la transaction":
                continue
            
            # Parser la date de transaction avec vérification
            date_execution = safe_get(row, 5)
            date_transaction = standardize_date(date_execution)
            
            # Si la date est nulle, ignorer cette transaction
            if not date_transaction:
                print(f"⚠️  Date de transaction manquante pour {safe_get(row, 0)}, transaction ignorée")
                continue
            
            # Déterminer le type et la direction du flux
            nature_transaction = safe_get(row, 0, '')
            montant = clean_amount(safe_get(row, 3, 0))
            
            type_flux, direction_flux = self._classify_lbp_transaction(nature_transaction)
            
            flux = {
                'id': str(uuid.uuid4()),
                'investment_id': None,  # Sera lié plus tard si nécessaire
                'user_id': self.user_id,
                
                'flow_type': type_flux,
                'flow_direction': direction_flux,
                
                'gross_amount': abs(montant),
                'net_amount': montant if direction_flux == 'in' else -abs(montant),
                
                'transaction_date': date_transaction,
                'status': 'completed' if safe_get(row, 4) == 'Réussi' else 'failed',
                
                'description': nature_transaction,
                'payment_method': safe_get(row, 1, ''),
                
                'created_at': datetime.now().isoformat()
            }
            
            flux_tresorerie.append(flux)
        
        return flux_tresorerie
    
    def _classify_lbp_transaction(self, nature: str) -> Tuple[str, str]:
        """Classifier le type de transaction LBP"""
        nature_lower = nature.lower()
        
        if 'rémunération' in nature_lower or 'intérêt' in nature_lower:
            return 'interest', 'in'
        elif 'remboursement' in nature_lower:
            return 'repayment', 'in'
        elif 'csg' in nature_lower or 'crds' in nature_lower or 'prélèvement' in nature_lower:
            return 'fee', 'out'
        elif 'investissement' in nature_lower or 'versement' in nature_lower:
            return 'deposit', 'out'
        else:
            return 'other', 'in' if 'bonus' in nature_lower else 'out'

class PretUpParser(PlatformParser):
    """Parser pour les fichiers de la plateforme PretUp"""
    
    def parse(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        try:
            excel_file = pd.ExcelFile(file_path)
            
            # Parser les différentes catégories de projets
            investissements = []
            investissements.extend(self._parse_project_sheet(file_path, 'Projet Sains - Offres', 'active'))
            investissements.extend(self._parse_project_sheet(file_path, 'Procédures - Offres', 'in_procedure'))
            investissements.extend(self._parse_project_sheet(file_path, 'Perdu - Offres', 'defaulted'))
            
            # Parser les flux de trésorerie
            flux_tresorerie = self._parse_account_sheet(file_path, 'Relevé compte')
            
            return investissements, flux_tresorerie
        except Exception as e:
            print(f"❌ Erreur lors du parsing PretUp: {e}")
            return [], []
    
    def _parse_project_sheet(self, file_path: str, sheet_name: str, status: str) -> List[Dict]:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        except:
            return []
        
        investissements = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Nom du Projet" or safe_get(row, 0) == "TOTAUX :":
                continue
                
            investissement = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'PretUp',
                'platform_id': str(safe_get(row, 2, '')),
                'investment_type': 'crowdfunding',
                'asset_class': 'real_estate',
                
                'project_name': safe_get(row, 0, ''),
                'company_name': safe_get(row, 1, ''),
                
                'invested_amount': clean_amount(safe_get(row, 3, 0)),
                'current_value': clean_amount(safe_get(row, 4, 0)),
                
                'status': status,
                
                # Date par défaut pour PretUp car pas de date dans ce tableau
                'investment_date': "2022-08-01",  # Date approximative
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investissements.append(investissement)
        
        return investissements
    
    def _parse_account_sheet(self, file_path: str, sheet_name: str) -> List[Dict]:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        except:
            return []
        
        flux_tresorerie = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Date":
                continue
            
            # Parser la date avec vérification PretUp
            date_str = safe_get(row, 0, '')
            date_transaction = self._parse_pretup_date(date_str)
            
            if not date_transaction:
                print(f"⚠️  Date PretUp invalide: {date_str}, transaction ignorée")
                continue
            
            # Parser les montants PretUp
            credit_amount = clean_amount(safe_get(row, 5, 0))
            debit_amount = clean_amount(safe_get(row, 4, 0))
            
            if credit_amount > 0:
                gross_amount = credit_amount
                direction_flux = 'in'
            elif debit_amount > 0:
                gross_amount = debit_amount
                direction_flux = 'out'
            else:
                continue
            
            flux = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                
                'flow_type': self._classify_pretup_transaction(safe_get(row, 1, '')),
                'flow_direction': direction_flux,
                
                'gross_amount': gross_amount,
                'net_amount': gross_amount if direction_flux == 'in' else -gross_amount,
                
                'capital_amount': clean_amount(safe_get(row, 9, 0)),
                'interest_amount': clean_amount(safe_get(row, 13, 0)),
                'tax_amount': clean_amount(safe_get(row, 11, 0)) + clean_amount(safe_get(row, 12, 0)),
                
                'transaction_date': date_transaction,
                'status': 'completed' if safe_get(row, 6) == 'Complété' else 'pending',
                
                'description': safe_get(row, 3, ''),
                
                'created_at': datetime.now().isoformat()
            }
            
            flux_tresorerie.append(flux)
        
        return flux_tresorerie
    
    def _parse_pretup_date(self, date_str: str) -> str:
        """Parser spécifiquement les dates PretUp"""
        if pd.isna(date_str) or not date_str:
            return None
        
        try:
            # PretUp utilise le format "DD/MM/YYYY à HH:MM"
            if 'à' in str(date_str):
                date_part = str(date_str).split(' à')[0]
            else:
                date_part = str(date_str)
            
            return standardize_date(date_part)
        except:
            return None
    
    def _classify_pretup_transaction(self, transaction_type: str) -> str:
        """Classifier le type de transaction PretUp"""
        type_lower = transaction_type.lower()
        
        if 'echéance' in type_lower:
            return 'repayment'
        elif 'impôts' in type_lower:
            return 'fee'
        elif 'versement' in type_lower:
            return 'deposit'
        else:
            return 'other'

class BienPreterParser(PlatformParser):
    """Parser pour les fichiers de la plateforme BienPreter"""
    
    def parse(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        try:
            # Parser les projets et le relevé de compte
            projects_df = pd.read_excel(file_path, sheet_name='Projets')
            account_df = pd.read_excel(file_path, sheet_name='Relevé compte')
            
            investissements = self._parse_projects(projects_df)
            flux_tresorerie = self._parse_account(account_df)
            
            return investissements, flux_tresorerie
        except Exception as e:
            print(f"❌ Erreur lors du parsing BienPreter: {e}")
            return [], []
    
    def _parse_projects(self, df: pd.DataFrame) -> List[Dict]:
        investissements = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 1)) or safe_get(row, 1) == "Projet":
                continue
            
            # Parser la date de financement
            date_financement = standardize_date(safe_get(row, 6))
            if not date_financement:
                date_financement = "2023-01-01"  # Date par défaut
            
            investissement = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'BienPreter',
                'platform_id': safe_get(row, 0, ''),
                'investment_type': 'crowdfunding',
                'asset_class': 'real_estate',
                
                'project_name': safe_get(row, 1, ''),
                'company_name': safe_get(row, 2, ''),
                
                'invested_amount': clean_amount(safe_get(row, 3, 0)),
                'annual_rate': safe_get(row, 4, 0),
                'duration_months': safe_get(row, 5, 0),
                
                'investment_date': date_financement,
                'expected_end_date': standardize_date(safe_get(row, 7)),
                
                'status': self._map_bienpreter_status(safe_get(row, 10, '')),
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investissements.append(investissement)
        
        return investissements
    
    def _map_bienpreter_status(self, status: str) -> str:
        """Mapper le statut BienPreter vers un statut standardisé"""
        if 'en cours' in status.lower():
            return 'active'
        elif 'terminé' in status.lower() or 'remboursé' in status.lower():
            return 'completed'
        else:
            return 'active'
    
    def _parse_account(self, df: pd.DataFrame) -> List[Dict]:
        flux_tresorerie = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Opération":
                continue
            
            # Parser la date avec vérification
            date_transaction = standardize_date(safe_get(row, 3))
            if not date_transaction:
                print(f"⚠️  Date BienPreter manquante, transaction ignorée")
                continue
            
            flux = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                
                'flow_type': 'repayment',  # BienPreter a principalement des remboursements
                'flow_direction': 'in',
                
                'gross_amount': clean_amount(safe_get(row, 4, 0)),
                'net_amount': clean_amount(safe_get(row, 4, 0)),
                'capital_amount': clean_amount(safe_get(row, 6, 0)),
                'interest_amount': clean_amount(safe_get(row, 7, 0)),
                'tax_amount': clean_amount(safe_get(row, 8, 0)),
                
                'transaction_date': date_transaction,
                'status': 'completed',
                
                'description': f"{safe_get(row, 0, '')} - {safe_get(row, 2, '')}",
                
                'created_at': datetime.now().isoformat()
            }
            
            flux_tresorerie.append(flux)
        
        return flux_tresorerie

class HomunityParser(PlatformParser):
    """Parser pour les fichiers de la plateforme Homunity - NOUVEAU"""
    
    def parse(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        try:
            # Parser les projets et le relevé de compte Homunity
            projects_df = pd.read_excel(file_path, sheet_name='Projets')
            account_df = pd.read_excel(file_path, sheet_name='Relevé compte')
            
            investissements = self._parse_projects(projects_df)
            flux_tresorerie = self._parse_account(account_df)
            
            return investissements, flux_tresorerie
        except Exception as e:
            print(f"❌ Erreur lors du parsing Homunity: {e}")
            return [], []
    
    def _parse_projects(self, df: pd.DataFrame) -> List[Dict]:
        investissements = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Date de souscription":
                continue
            
            # Parser la date de souscription
            date_souscription = standardize_date(safe_get(row, 0))
            if not date_souscription:
                print(f"⚠️  Date souscription Homunity manquante pour {safe_get(row, 2)}")
                date_souscription = "2021-01-01"  # Date par défaut
            
            investissement = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'Homunity',
                'platform_id': f"HOM_{idx}",
                'investment_type': 'crowdfunding',
                'asset_class': 'real_estate',
                
                'project_name': safe_get(row, 2, ''),  # Projet
                'company_name': safe_get(row, 1, ''),  # Promoteur
                
                'invested_amount': clean_amount(safe_get(row, 3, 0)),  # Invest.
                'annual_rate': clean_amount(safe_get(row, 5, 0)),  # Taux d'intérêt
                
                'investment_date': date_souscription,
                'expected_end_date': standardize_date(safe_get(row, 4)),  # Date de remb projet
                
                'status': self._map_homunity_status(safe_get(row, 6, '')),
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investissements.append(investissement)
        
        return investissements
    
    def _map_homunity_status(self, status: str) -> str:
        """Mapper le statut Homunity vers un statut standardisé"""
        status_lower = status.lower() if status else ''
        
        if 'en attente' in status_lower:
            return 'active'
        elif 'en cours' in status_lower:
            return 'active'
        elif 'terminé' in status_lower or 'remboursé' in status_lower:
            return 'completed'
        else:
            return 'active'
    
    def _parse_account(self, df: pd.DataFrame) -> List[Dict]:
        flux_tresorerie = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Type de mouvement":
                continue
            
            # Parser la date avec vérification
            date_transaction = standardize_date(safe_get(row, 1))
            if not date_transaction:
                print(f"⚠️  Date Homunity manquante, transaction ignorée")
                continue
            
            # Parser le montant (format "+ 74.52" ou "- 10.00")
            montant_str = safe_get(row, 3, '')
            montant = clean_amount(montant_str.replace('+', '').replace('-', '').strip())
            direction = 'in' if '+' in str(montant_str) else 'out'
            
            flux = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                
                'flow_type': self._classify_homunity_transaction(safe_get(row, 0, '')),
                'flow_direction': direction,
                
                'gross_amount': montant,
                'net_amount': montant if direction == 'in' else -montant,
                
                'transaction_date': date_transaction,
                'status': 'completed' if safe_get(row, 2) == 'Succès' else 'failed',
                
                'description': safe_get(row, 4, ''),  # Message
                
                'created_at': datetime.now().isoformat()
            }
            
            flux_tresorerie.append(flux)
        
        return flux_tresorerie
    
    def _classify_homunity_transaction(self, type_mouvement: str) -> str:
        """Classifier le type de transaction Homunity"""
        type_lower = type_mouvement.lower()
        
        if 'transfert' in type_lower:
            return 'repayment'  # La plupart des transferts Homunity sont des remboursements
        elif 'versement' in type_lower:
            return 'deposit'
        else:
            return 'other'