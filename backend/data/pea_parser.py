import pandas as pd
import uuid
from datetime import datetime
from typing import List, Dict, Tuple, Any
from backend.data.parsers import PlatformParser
from backend.utils.file_helpers import standardize_date, safe_get
import re

# Utiliser la nouvelle fonction clean_amount
def clean_amount_pea(amount) -> float:
    """Version spécialisée pour les montants PEA français"""
    if pd.isna(amount) or amount is None or amount == '':
        return 0.0
    
    if isinstance(amount, str):
        cleaned = amount.strip()
        cleaned = cleaned.replace('€', '').replace('EUR', '').replace('$', '')
        
        # Gérer les formats français complexes avec espaces
        if ',' in cleaned and ('.' not in cleaned or cleaned.rfind(',') > cleaned.rfind('.')):
            parts = cleaned.split(',')
            if len(parts) == 2:
                integer_part = parts[0].replace(' ', '').replace('.', '')
                decimal_part = parts[1].replace(' ', '')
                
                if len(decimal_part) <= 2 and decimal_part.isdigit():
                    cleaned = f"{integer_part}.{decimal_part}"
                else:
                    cleaned = cleaned.replace(' ', '').replace(',', '.')
            else:
                last_comma_pos = cleaned.rfind(',')
                before_comma = cleaned[:last_comma_pos].replace(' ', '').replace(',', '').replace('.', '')
                after_comma = cleaned[last_comma_pos+1:].replace(' ', '')
                
                if after_comma.isdigit() and len(after_comma) <= 2:
                    cleaned = f"{before_comma}.{after_comma}"
                else:
                    cleaned = cleaned.replace(' ', '').replace(',', '.')
        else:
            cleaned = cleaned.replace(' ', '').replace(',', '')
        
        cleaned = re.sub(r'[^\d\.\-]', '', cleaned)
        
        try:
            return float(cleaned)
        except ValueError:
            print(f"⚠️  Erreur lors du nettoyage du montant '{amount}': impossible de convertir")
            return 0.0
    
    try:
        return float(amount)
    except (ValueError, TypeError):
        return 0.0

class PEAParser(PlatformParser):
    """Parser spécialisé pour les relevés PEA"""
    
    def parse(self, file_path: str) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Parse le fichier PEA et retourne (cash_flows, positions, transactions)
        """
        try:
            # Lire le PDF ou Excel selon l'extension
            if file_path.endswith('.pdf'):
                # Vous devrez implémenter la lecture PDF
                # Pour l'instant, on suppose un Excel
                raise NotImplementedError("Lecture PDF à implémenter")
            else:
                df = pd.read_excel(file_path)
            
            cash_flows = []
            positions = []
            transactions = []
            
            # Parser selon les sections identifiées
            for idx, row in df.iterrows():
                # Identifier le type de ligne
                designation = safe_get(row, 'Designation', '') or safe_get(row, 0, '')
                quantite = safe_get(row, 'Quantité', '') or safe_get(row, 1, '')
                cours = safe_get(row, 'Cours', '') or safe_get(row, 2, '')
                debit = safe_get(row, 'Débit', '') or safe_get(row, 3, '')
                credit = safe_get(row, 'Crédit', '') or safe_get(row, 4, '')
                date_operation = safe_get(row, 'Date', '') or safe_get(row, 5, '')
                
                # Nettoyer les montants
                debit_amount = clean_amount_pea(debit)
                credit_amount = clean_amount_pea(credit)
                quantite_clean = clean_amount_pea(quantite) if quantite else 0
                cours_clean = clean_amount_pea(cours) if cours else 0
                
                # Ignorer les lignes vides ou d'en-tête
                if not designation or designation in ['Designation', 'Désignation']:
                    continue
                
                # Traitement selon le type d'opération
                if self._is_ttf_line(designation):
                    # TTF - Taxe sur transactions financières (uniquement cash flow)
                    if debit_amount > 0:
                        cash_flow = self._create_cash_flow(
                            user_id=self.user_id,
                            flow_type='fee',
                            flow_direction='out',
                            amount=debit_amount,
                            date=date_operation,
                            description=designation
                        )
                        cash_flows.append(cash_flow)
                
                elif self._is_dividend_or_coupon(designation):
                    # Dividendes ou coupons (crédit)
                    if credit_amount > 0:
                        cash_flow = self._create_cash_flow(
                            user_id=self.user_id,
                            flow_type='dividend',
                            flow_direction='in',
                            amount=credit_amount,
                            date=date_operation,
                            description=designation
                        )
                        cash_flows.append(cash_flow)
                
                elif quantite_clean > 0 and cours_clean > 0:
                    # Transaction d'achat/vente avec quantité et cours
                    total_amount = quantite_clean * cours_clean
                    
                    # Déterminer si c'est un achat ou une vente
                    if debit_amount > 0:
                        # Achat (débit)
                        transaction_type = 'buy'
                        flow_direction = 'out'
                        amount = debit_amount
                    else:
                        # Vente (crédit)
                        transaction_type = 'sell'
                        flow_direction = 'in'
                        amount = credit_amount
                    
                    # Créer la transaction
                    transaction = self._create_transaction(
                        user_id=self.user_id,
                        security_name=designation,
                        transaction_type=transaction_type,
                        quantity=quantite_clean,
                        price=cours_clean,
                        total_amount=amount,
                        date=date_operation
                    )
                    transactions.append(transaction)
                    
                    # Créer le cash flow correspondant
                    cash_flow = self._create_cash_flow(
                        user_id=self.user_id,
                        flow_type=transaction_type,
                        flow_direction=flow_direction,
                        amount=amount,
                        date=date_operation,
                        description=f"{transaction_type.title()} {designation}",
                        security_name=designation
                    )
                    cash_flows.append(cash_flow)
                
                elif debit_amount > 0 or credit_amount > 0:
                    # Autre type de flux (versement, retrait, etc.)
                    if debit_amount > 0:
                        flow_type = self._classify_debit_flow(designation)
                        cash_flow = self._create_cash_flow(
                            user_id=self.user_id,
                            flow_type=flow_type,
                            flow_direction='out',
                            amount=debit_amount,
                            date=date_operation,
                            description=designation
                        )
                        cash_flows.append(cash_flow)
                    
                    if credit_amount > 0:
                        flow_type = self._classify_credit_flow(designation)
                        cash_flow = self._create_cash_flow(
                            user_id=self.user_id,
                            flow_type=flow_type,
                            flow_direction='in',
                            amount=credit_amount,
                            date=date_operation,
                            description=designation
                        )
                        cash_flows.append(cash_flow)
            
            return cash_flows, positions, transactions
            
        except Exception as e:
            print(f"❌ Erreur lors du parsing PEA: {e}")
            return [], [], []
    
    def _is_ttf_line(self, designation: str) -> bool:
        """Vérifie si c'est une ligne TTF"""
        ttf_keywords = ['ttf', 'taxe transaction', 'taxe sur les transactions']
        return any(keyword in designation.lower() for keyword in ttf_keywords)
    
    def _is_dividend_or_coupon(self, designation: str) -> bool:
        """Vérifie si c'est un dividende ou coupon"""
        dividend_keywords = ['dividende', 'coupon', 'détachement', 'distribution']
        return any(keyword in designation.lower() for keyword in dividend_keywords)
    
    def _classify_debit_flow(self, designation: str) -> str:
        """Classifie un flux débit"""
        designation_lower = designation.lower()
        
        if 'achat' in designation_lower or 'acquisition' in designation_lower:
            return 'buy'
        elif 'frais' in designation_lower or 'commission' in designation_lower:
            return 'fee'
        elif 'ttf' in designation_lower or 'taxe' in designation_lower:
            return 'fee'
        elif 'versement' in designation_lower:
            return 'deposit'
        else:
            return 'other'
    
    def _classify_credit_flow(self, designation: str) -> str:
        """Classifie un flux crédit"""
        designation_lower = designation.lower()
        
        if 'vente' in designation_lower or 'cession' in designation_lower:
            return 'sell'
        elif 'dividende' in designation_lower:
            return 'dividend'
        elif 'coupon' in designation_lower:
            return 'interest'
        elif 'remboursement' in designation_lower:
            return 'repayment'
        elif 'régularisation' in designation_lower:
            return 'adjustment'
        else:
            return 'other'
    
    def _create_cash_flow(self, user_id: str, flow_type: str, flow_direction: str, 
                         amount: float, date: str, description: str, 
                         security_name: str = None) -> Dict:
        """Crée un cash flow (SANS quantité)"""
        return {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'platform': 'PEA',
            'flow_type': flow_type,
            'flow_direction': flow_direction,
            'gross_amount': amount,
            'net_amount': amount if flow_direction == 'in' else -amount,
            'transaction_date': standardize_date(date),
            'description': description,
            'security_name': security_name,
            'status': 'completed',
            'created_at': datetime.now().isoformat()
        }
    
    def _create_transaction(self, user_id: str, security_name: str, 
                          transaction_type: str, quantity: float, price: float,
                          total_amount: float, date: str) -> Dict:
        """Crée une transaction avec quantité (pour table séparée)"""
        return {
            'id': str(uuid.uuid4()),
            'user_id': user_id,
            'platform': 'PEA',
            'security_name': security_name,
            'transaction_type': transaction_type,
            'quantity': quantity,
            'price': price,
            'total_amount': total_amount,
            'transaction_date': standardize_date(date),
            'created_at': datetime.now().isoformat()
        }
