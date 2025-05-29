import pandas as pd
from typing import List, Dict, Any, Tuple
from datetime import datetime
import uuid
from backend.utils.file_helpers import standardize_date, clean_amount, safe_get

class PlatformParser:
    """Base class for platform parsers"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def parse(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Parse file and return (investments, cash_flows)"""
        raise NotImplementedError

class LBPParser(PlatformParser):
    """Parser for LBP platform files"""
    
    def parse(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        # Read Excel file
        excel_file = pd.ExcelFile(file_path)
        
        # Parse projects sheet
        projects_df = pd.read_excel(file_path, sheet_name='Projets')
        account_df = pd.read_excel(file_path, sheet_name='Relevé compte')
        
        investments = self._parse_projects(projects_df)
        cash_flows = self._parse_account(account_df)
        
        return investments, cash_flows
    
    def _parse_projects(self, df: pd.DataFrame) -> List[Dict]:
        investments = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 1)) or safe_get(row, 1) == "Nom du projet":  # Skip header
                continue
                
            investment = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'LBP',
                'platform_id': f"LBP_{idx}",
                'investment_type': 'crowdfunding',
                'asset_class': 'real_estate',
                
                # Project info
                'project_name': safe_get(row, 1, ''),  # Nom du projet
                'company_name': safe_get(row, 1, ''),  # Same as project for LBP
                
                # Financial data
                'invested_amount': clean_amount(safe_get(row, 3, 0)),  # Montant investi
                'annual_rate': safe_get(row, 4, 0),  # Taux annuel
                
                # Dates
                'investment_date': standardize_date(safe_get(row, 0)),  # Date de collecte
                'signature_date': standardize_date(safe_get(row, 5)),  # Date de signature
                'expected_end_date': standardize_date(safe_get(row, 7)),  # Date remb max
                'actual_end_date': standardize_date(safe_get(row, 8)),  # Date remb effective
                
                # Status mapping
                'status': self._map_lbp_status(safe_get(row, 2, '')),
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investments.append(investment)
        
        return investments
    
    def _map_lbp_status(self, status: str) -> str:
        """Map LBP status to standardized status"""
        status_mapping = {
            'Finalisée': 'completed',
            'Remboursée': 'completed', 
            'En cours': 'active',
            'Retard': 'delayed'
        }
        return status_mapping.get(status, 'active')
    
    def _parse_account(self, df: pd.DataFrame) -> List[Dict]:
        cash_flows = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Nature de la transaction":
                continue
            
            # Determine flow type and direction
            transaction_nature = safe_get(row, 0, '')
            amount = clean_amount(safe_get(row, 3, 0))
            
            flow_type, flow_direction = self._classify_lbp_transaction(transaction_nature)
            
            cash_flow = {
                'id': str(uuid.uuid4()),
                'investment_id': None,  # Will be linked later if needed
                'user_id': self.user_id,
                
                'flow_type': flow_type,
                'flow_direction': flow_direction,
                
                'gross_amount': abs(amount),
                'net_amount': amount if flow_direction == 'in' else -abs(amount),
                
                'transaction_date': standardize_date(safe_get(row, 5)),  # Date d'exécution
                'status': 'completed' if safe_get(row, 4) == 'Réussi' else 'failed',
                
                'description': transaction_nature,
                'payment_method': safe_get(row, 1, ''),  # Moyen de paiement
                
                'created_at': datetime.now().isoformat()
            }
            
            cash_flows.append(cash_flow)
        
        return cash_flows
    
    def _classify_lbp_transaction(self, nature: str) -> Tuple[str, str]:
        """Classify LBP transaction type"""
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
    """Parser for PretUp platform files"""
    
    def parse(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        excel_file = pd.ExcelFile(file_path)
        
        # Parse different project categories
        investments = []
        investments.extend(self._parse_project_sheet(file_path, 'Projet Sains - Offres', 'active'))
        investments.extend(self._parse_project_sheet(file_path, 'Procédures - Offres', 'in_procedure'))
        investments.extend(self._parse_project_sheet(file_path, 'Perdu - Offres', 'defaulted'))
        
        # Parse cash flows
        cash_flows = self._parse_account_sheet(file_path, 'Relevé compte')
        
        return investments, cash_flows
    
    def _parse_project_sheet(self, file_path: str, sheet_name: str, status: str) -> List[Dict]:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        except:
            return []
        
        investments = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Nom du Projet":
                continue
            
            if safe_get(row, 0) == "TOTAUX :":  # Skip totals row
                continue
                
            investment = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'PretUp',
                'platform_id': str(safe_get(row, 2, '')),  # Numéro Offre
                'investment_type': 'crowdfunding',
                'asset_class': 'real_estate',
                
                'project_name': safe_get(row, 0, ''),  # Nom du Projet
                'company_name': safe_get(row, 1, ''),  # Entreprise
                
                'invested_amount': clean_amount(safe_get(row, 3, 0)),  # Montant Offre
                'current_value': clean_amount(safe_get(row, 4, 0)),  # Capital Reçu
                
                'status': status,
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investments.append(investment)
        
        return investments
    
    def _parse_account_sheet(self, file_path: str, sheet_name: str) -> List[Dict]:
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        except:
            return []
        
        cash_flows = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Date":
                continue
            
            # Parse PretUp specific format
            credit_amount = clean_amount(safe_get(row, 5, 0))  # Crédit
            debit_amount = clean_amount(safe_get(row, 4, 0))   # Débit
            
            if credit_amount > 0:
                gross_amount = credit_amount
                flow_direction = 'in'
            elif debit_amount > 0:
                gross_amount = debit_amount
                flow_direction = 'out'
            else:
                continue
            
            cash_flow = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                
                'flow_type': self._classify_pretup_transaction(safe_get(row, 1, '')),
                'flow_direction': flow_direction,
                
                'gross_amount': gross_amount,
                'net_amount': gross_amount if flow_direction == 'in' else -gross_amount,
                
                'capital_amount': clean_amount(safe_get(row, 9, 0)),    # Part de Capital
                'interest_amount': clean_amount(safe_get(row, 13, 0)),  # Intérêts nets
                'tax_amount': clean_amount(safe_get(row, 11, 0)) + clean_amount(safe_get(row, 12, 0)),  # Retenues
                
                'transaction_date': standardize_date(safe_get(row, 0)),
                'status': 'completed' if safe_get(row, 6) == 'Complété' else 'pending',
                
                'description': safe_get(row, 3, ''),  # Libellé
                
                'created_at': datetime.now().isoformat()
            }
            
            cash_flows.append(cash_flow)
        
        return cash_flows
    
    def _classify_pretup_transaction(self, transaction_type: str) -> str:
        """Classify PretUp transaction type"""
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
    """Parser for BienPreter platform files"""
    
    def parse(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        # Parse projects
        projects_df = pd.read_excel(file_path, sheet_name='Projets')
        account_df = pd.read_excel(file_path, sheet_name='Relevé compte')
        
        investments = self._parse_projects(projects_df)
        cash_flows = self._parse_account(account_df)
        
        return investments, cash_flows
    
    def _parse_projects(self, df: pd.DataFrame) -> List[Dict]:
        investments = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 1)) or safe_get(row, 1) == "Projet":
                continue
            
            investment = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'BienPreter',
                'platform_id': safe_get(row, 0, ''),  # N°Contrat
                'investment_type': 'crowdfunding',
                'asset_class': 'real_estate',
                
                'project_name': safe_get(row, 1, ''),  # Projet
                'company_name': safe_get(row, 2, ''),  # Entreprise
                
                'invested_amount': clean_amount(safe_get(row, 3, 0)),  # Montant
                'annual_rate': safe_get(row, 4, 0),  # Taux
                'duration_months': safe_get(row, 5, 0),  # Durée
                
                'investment_date': standardize_date(safe_get(row, 6)),  # Date de financement
                'expected_end_date': standardize_date(safe_get(row, 7)),  # Date de clôture
                
                'status': self._map_bienpreter_status(safe_get(row, 10, '')),
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investments.append(investment)
        
        return investments
    
    def _map_bienpreter_status(self, status: str) -> str:
        """Map BienPreter status to standardized status"""
        if 'en cours' in status.lower():
            return 'active'
        elif 'terminé' in status.lower() or 'remboursé' in status.lower():
            return 'completed'
        else:
            return 'active'
    
    def _parse_account(self, df: pd.DataFrame) -> List[Dict]:
        cash_flows = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Opération":
                continue
            
            cash_flow = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                
                'flow_type': 'repayment',  # BienPreter mainly has repayments
                'flow_direction': 'in',
                
                'gross_amount': clean_amount(safe_get(row, 4, 0)),  # Montant
                'net_amount': clean_amount(safe_get(row, 4, 0)),
                'capital_amount': clean_amount(safe_get(row, 6, 0)),  # Capital remboursé
                'interest_amount': clean_amount(safe_get(row, 7, 0)),  # Intérêts
                'tax_amount': clean_amount(safe_get(row, 8, 0)),  # Prélèvements
                
                'transaction_date': standardize_date(safe_get(row, 3)),  # Date
                'status': 'completed',
                
                'description': f"{safe_get(row, 0, '')} - {safe_get(row, 2, '')}",  # Opération + Projet
                
                'created_at': datetime.now().isoformat()
            }
            
            cash_flows.append(cash_flow)
        
        return cash_flows