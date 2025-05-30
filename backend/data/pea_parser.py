# ===== backend/data/pea_parser.py - VERSION CORRIGÉE =====
import pdfplumber
import pandas as pd
from typing import List, Dict, Any, Tuple
from datetime import datetime
import uuid
import re
import os
from backend.utils.file_helpers import standardize_date, clean_amount, safe_get

class PEAParser:
    """Parser pour les PDFs PEA de Bourse Direct"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
    
    def parse_pdf_files(self, releve_path: str = None, evaluation_path: str = None) -> Tuple[List[Dict], List[Dict], List[Dict]]:
        """
        Parser les fichiers PDF PEA et retourner (investissements, flux_tresorerie, positions)
        """
        investissements = []
        flux_tresorerie = []
        positions = []
        
        # Parser le relevé de compte (transactions)
        if releve_path:
            try:
                flux_tresorerie = self._parse_releve_compte(releve_path)
                print(f"✅ Relevé PEA parsé: {len(flux_tresorerie)} transactions")
            except Exception as e:
                print(f"❌ Erreur parsing relevé PEA: {e}")
                import traceback
                traceback.print_exc()
        
        # Parser l'évaluation de portefeuille (positions actuelles)
        if evaluation_path:
            try:
                positions = self._parse_evaluation_portefeuille(evaluation_path)
                investissements = self._convert_positions_to_investments(positions)
                print(f"✅ Évaluation PEA parsée: {len(positions)} positions")
            except Exception as e:
                print(f"❌ Erreur parsing évaluation PEA: {e}")
                import traceback
                traceback.print_exc()
        
        return investissements, flux_tresorerie, positions
    
    def _parse_releve_compte(self, pdf_path: str) -> List[Dict]:
        """Parser le relevé de compte PEA"""
        flux_tresorerie = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                # Chercher les transactions dans le texte
                transactions = self._extract_transactions_from_text(text)
                flux_tresorerie.extend(transactions)
        
        return flux_tresorerie
    
    def _extract_transactions_from_text(self, text: str) -> List[Dict]:
        """Extraire les transactions du texte du PDF"""
        transactions = []
        lines = text.split('\n')
        
        for i, line in enumerate(lines):
            line = line.strip()
            
            # Détecter les lignes de transaction par date (DD/MM/YYYY)
            date_match = re.match(r'^(\d{2}/\d{2}/\d{4})', line)
            if date_match:
                try:
                    # Prendre aussi les 2 lignes suivantes pour le contexte
                    context_lines = lines[i:i+3] if i+2 < len(lines) else lines[i:]
                    transaction = self._parse_transaction_line(line, context_lines)
                    if transaction:
                        transactions.append(transaction)
                except Exception as e:
                    print(f"⚠️  Erreur parsing transaction '{line[:50]}...': {e}")
        
        return transactions
    
    def _parse_transaction_line(self, main_line: str, context_lines: List[str]) -> Dict:
        """Parser une ligne de transaction"""
        
        # Extraire la date
        date_match = re.match(r'^(\d{2}/\d{2}/\d{4})', main_line)
        if not date_match:
            return None
        
        date_str = date_match.group(1)
        transaction_date = standardize_date(date_str)
        
        # Analyser le type de transaction
        line_upper = main_line.upper()
        
        # Déterminer le type et la direction
        if 'ACH CPT' in line_upper or 'ACHAT' in line_upper:
            flow_type = 'purchase'
            flow_direction = 'out'
        elif 'VENTE' in line_upper or 'VTE CPT' in line_upper:
            flow_type = 'sale'
            flow_direction = 'in'
        elif 'COUPONS' in line_upper or 'DIVIDENDE' in line_upper:
            flow_type = 'dividend'
            flow_direction = 'in'
        elif 'INVESTISSEMENT ESPECES' in line_upper or 'VERSEMENT' in line_upper:
            flow_type = 'deposit'
            flow_direction = 'out'
        elif 'TAXE' in line_upper or 'TTF' in line_upper:
            flow_type = 'fee'
            flow_direction = 'out'
        elif 'REGULARISATION' in line_upper:
            flow_type = 'adjustment'
            flow_direction = 'in' if 'RBT' in line_upper else 'out'
        else:
            flow_type = 'other'
            flow_direction = 'in'
        
        # CORRECTION : Extraction intelligente des montants
        quantity, price, montant = self._extract_financial_data_from_line(main_line)
        
        # Extraire la description (partie centrale sans les montants)
        description = self._extract_description(main_line)
        
        return {
            'id': str(uuid.uuid4()),
            'user_id': self.user_id,
            'investment_id': None,  # Sera lié plus tard
            
            'flow_type': flow_type,
            'flow_direction': flow_direction,
            
            'gross_amount': montant,
            'net_amount': montant if flow_direction == 'in' else -montant,
            
            'transaction_date': transaction_date,
            'status': 'completed',
            
            'description': description,
            'payment_method': 'PEA',
            
            # Données spécifiques PEA
            'quantity': quantity,
            'unit_price': price,
            
            'created_at': datetime.now().isoformat()
        }
    
    def _extract_financial_data_from_line(self, line: str) -> Tuple[float, float, float]:
        """
        Extraire quantité, cours et montant d'une ligne de transaction
        Format attendu: "DATE DESCRIPTION Qté : XX Cours : YY MONTANT"
        """
        quantity = 0.0
        price = 0.0
        montant = 0.0
        
        try:
            # Extraire quantité
            qty_match = re.search(r'Qté\s*:\s*([\d\s,\.]+)', line)
            if qty_match:
                qty_str = qty_match.group(1).strip()
                quantity = clean_amount(qty_str)
            
            # Extraire cours
            cours_match = re.search(r'Cours\s*:\s*([\d\s,\.]+)', line)
            if cours_match:
                prix_str = cours_match.group(1).strip()
                price = clean_amount(prix_str)
            
            # Pour le montant total, prendre le dernier nombre de la ligne (après cours)
            # Diviser la ligne en sections pour éviter la confusion
            parts = line.split()
            
            # Chercher le montant final (généralement les 1-2 derniers éléments numériques)
            potential_amounts = []
            for part in reversed(parts):  # Commencer par la fin
                # Nettoyer et tester si c'est un montant
                cleaned_part = re.sub(r'[^\d,\.]', '', part)
                if cleaned_part and (',' in cleaned_part or '.' in cleaned_part):
                    try:
                        amount = clean_amount(cleaned_part)
                        if amount > 0:
                            potential_amounts.append(amount)
                    except:
                        continue
                
                # Arrêter après avoir trouvé 3 montants potentiels
                if len(potential_amounts) >= 3:
                    break
            
            # Le montant principal est généralement le plus gros (hors cours très élevés)
            if potential_amounts:
                # Filtrer les montants aberrants (cours très élevés)
                reasonable_amounts = [amt for amt in potential_amounts if amt < 100000]
                if reasonable_amounts:
                    montant = max(reasonable_amounts)
                else:
                    montant = potential_amounts[0]
            
            # Validation : si on a quantité et cours, vérifier la cohérence
            if quantity > 0 and price > 0:
                calculated_amount = quantity * price
                # Si le montant calculé est proche du montant trouvé, utiliser le calculé
                if abs(calculated_amount - montant) / max(calculated_amount, montant) < 0.1:
                    montant = calculated_amount
        
        except Exception as e:
            print(f"⚠️  Erreur extraction données financières '{line[:50]}...': {e}")
        
        return quantity, price, montant
    
    def _extract_description(self, line: str) -> str:
        """Extraire la description en évitant les données numériques"""
        
        # Enlever la date du début
        line_without_date = re.sub(r'^\d{2}/\d{2}/\d{4}\s+', '', line)
        
        # Enlever les parties "Qté : XX Cours : YY"
        line_clean = re.sub(r'Qté\s*:\s*[\d\s,\.]+', '', line_without_date)
        line_clean = re.sub(r'Cours\s*:\s*[\d\s,\.]+', '', line_clean)
        
        # Enlever les montants en fin de ligne
        line_clean = re.sub(r'[\d\s,\.]+$', '', line_clean)
        
        # Nettoyer les espaces multiples
        description = ' '.join(line_clean.split()).strip()
        
        return description if description else "Transaction PEA"
    
    def _parse_evaluation_portefeuille(self, pdf_path: str) -> List[Dict]:
        """Parser l'évaluation de portefeuille PEA"""
        positions = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                # Essayer d'extraire les tableaux
                tables = page.extract_tables()
                
                for table in tables:
                    if not table or len(table) < 2:
                        continue
                    
                    # Vérifier si c'est le tableau des positions
                    header = table[0] if table[0] else []
                    if any('Désignation' in str(cell) or 'Quantité' in str(cell) for cell in header if cell):
                        positions_from_table = self._parse_positions_table(table)
                        positions.extend(positions_from_table)
                
                # Fallback: Parser le texte si pas de tableaux
                if not positions:
                    text = page.extract_text()
                    if text and 'EVALUATION DE PORTEFEUILLE' in text:
                        positions = self._parse_positions_from_text(text)
        
        return positions
    
    def _parse_positions_table(self, table: List[List]) -> List[Dict]:
        """Parser le tableau des positions"""
        positions = []
        
        if len(table) < 2:
            return positions
        
        # Identifier les colonnes (header)
        header = [str(cell).strip() if cell else '' for cell in table[0]]
        
        # Mapping des colonnes (flexible)
        col_mapping = {}
        for i, col_name in enumerate(header):
            col_lower = col_name.lower()
            if 'désignation' in col_lower or 'valeur' in col_lower:
                col_mapping['designation'] = i
            elif 'quantité' in col_lower:
                col_mapping['quantity'] = i
            elif 'cours' in col_lower:
                col_mapping['price'] = i
            elif 'valorisation' in col_lower:
                col_mapping['value'] = i
            elif '%' in col_lower or 'pourcent' in col_lower:
                col_mapping['percentage'] = i
        
        # Parser les lignes de données
        for row in table[1:]:
            if not row or not any(cell for cell in row):
                continue
            
            try:
                position = self._parse_position_row(row, col_mapping)
                if position:
                    positions.append(position)
            except Exception as e:
                print(f"⚠️  Erreur parsing position: {e}")
        
        return positions
    
    def _parse_position_row(self, row: List, col_mapping: Dict) -> Dict:
        """Parser une ligne de position - VERSION CORRIGÉE"""
        
        # Extraire les données selon le mapping avec nettoyage amélioré
        designation = safe_get(pd.Series(row), col_mapping.get('designation', 0), '')
        
        # CORRECTION : Nettoyage individuel des montants
        quantity_raw = safe_get(pd.Series(row), col_mapping.get('quantity', 1), '')
        price_raw = safe_get(pd.Series(row), col_mapping.get('price', 2), '')
        value_raw = safe_get(pd.Series(row), col_mapping.get('value', 3), '')
        percentage_raw = safe_get(pd.Series(row), col_mapping.get('percentage', 4), '')
        
        # Nettoyer chaque montant séparément
        quantity = self._clean_single_amount(quantity_raw)
        price = self._clean_single_amount(price_raw)
        value = self._clean_single_amount(value_raw)
        percentage = self._clean_single_amount(percentage_raw)
        
        # Ignorer les lignes sans désignation ou avec totaux
        if not designation or 'TOTAL' in str(designation).upper():
            return None
        
        # Extraire ISIN si présent (format FRXXXXXXXXXXXX)
        isin_match = re.search(r'FR\d{10}', str(designation))
        isin = isin_match.group(0) if isin_match else None
        
        # Nettoyer le nom de l'actif
        asset_name = str(designation).strip()
        if isin:
            asset_name = asset_name.replace(isin, '').strip()
        
        # Enlever les codes en début (ex: "025")
        asset_name = re.sub(r'^\d{3}\s*', '', asset_name).strip()
        
        # Déterminer la catégorie d'actif
        asset_class = self._classify_pea_asset(asset_name)
        
        return {
            'id': str(uuid.uuid4()),
            'user_id': self.user_id,
            'investment_id': None,
            
            'isin': isin,
            'asset_name': asset_name,
            'quantity': quantity,
            'current_price': price,
            'market_value': value,
            'portfolio_percentage': percentage,
            
            'asset_class': asset_class,
            'platform': 'PEA',
            
            'valuation_date': datetime.now().strftime('%Y-%m-%d'),
            'created_at': datetime.now().isoformat()
        }
    
    
    
    def _parse_positions_from_text(self, text: str) -> List[Dict]:
        """Parser les positions depuis le texte (fallback) - VERSION CORRIGÉE"""
        positions = []
        lines = text.split('\n')
        
        # Chercher les lignes avec format: "NOM_ACTIF ISIN QTÉ COURS VALEUR %"
        for line in lines:
            if re.search(r'FR\d{10}', line) and re.search(r'\d+[,\.]\d{2}', line):
                try:
                    position = self._parse_position_text_line_corrected(line)
                    if position:
                        positions.append(position)
                except Exception as e:
                    print(f"⚠️  Erreur parsing ligne position: {e}")
        
        return positions
    
    def _parse_position_text_line_corrected(self, line: str) -> Dict:
        """Parser une ligne de position depuis le texte - VERSION CORRIGÉE"""
        
        # Extraire ISIN
        isin_match = re.search(r'FR\d{10}', line)
        isin = isin_match.group(0) if isin_match else None
        
        # CORRECTION : Extraire les montants de façon plus intelligente
        # Diviser la ligne et extraire les montants un par un
        parts = line.split()
        amounts = []
        
        for part in parts:
            # Chercher les patterns de montants
            if re.match(r'^\d+[,\.]\d{2}$', part) or re.match(r'^\d{1,3}([,\.]\d{3})*[,\.]\d{2}$', part):
                try:
                    amount = self._clean_single_amount(part)
                    if amount > 0:
                        amounts.append(amount)
                except:
                    continue
        
        # Assigner les montants par ordre logique
        quantity = amounts[0] if len(amounts) > 0 else 0
        price = amounts[1] if len(amounts) > 1 else 0
        value = amounts[2] if len(amounts) > 2 else 0
        percentage = amounts[3] if len(amounts) > 3 else 0
        
        # Extraire le nom (début de ligne jusqu'à ISIN)
        asset_name = line.split(isin)[0].strip() if isin else line.strip()
        asset_name = re.sub(r'^\w+\s+', '', asset_name)  # Supprimer code initial
        asset_name = re.sub(r'\d+[,\.]\d{2}.*$', '', asset_name).strip()  # Supprimer montants
        
        return {
            'id': str(uuid.uuid4()),
            'user_id': self.user_id,
            'isin': isin,
            'asset_name': asset_name,
            'quantity': quantity,
            'current_price': price,
            'market_value': value,
            'portfolio_percentage': percentage,
            'platform': 'PEA',
            'asset_class': self._classify_pea_asset(asset_name),
            'valuation_date': datetime.now().strftime('%Y-%m-%d'),
            'created_at': datetime.now().isoformat()
        }
    
    def _classify_pea_asset(self, asset_name: str) -> str:
        """Classifier un actif PEA par catégorie"""
        name_upper = str(asset_name).upper()
        
        if any(keyword in name_upper for keyword in ['ETF', 'TRACKER', 'INDEX']):
            return 'etf'
        elif any(keyword in name_upper for keyword in ['EURO', 'FONDS']):
            return 'fund'
        elif any(keyword in name_upper for keyword in ['BOND', 'OBLIGATION']):
            return 'bond'
        else:
            return 'stock'
    
    def _convert_positions_to_investments(self, positions: List[Dict]) -> List[Dict]:
        """Convertir les positions en investissements pour la cohérence de données"""
        investments = []
        
        for position in positions:
            # Créer un investissement "virtuel" pour chaque position
            investment = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'PEA',
                'platform_id': position.get('isin', ''),
                'investment_type': 'stocks',
                'asset_class': position.get('asset_class', 'stock'),
                
                'project_name': position.get('asset_name', ''),
                'company_name': position.get('asset_name', ''),
                
                # Utiliser la valorisation actuelle comme montant investi (approximation)
                'invested_amount': position.get('market_value', 0),
                'current_value': position.get('market_value', 0),
                
                'investment_date': '2020-01-01',  # Date approximative, à affiner
                'status': 'active',
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investments.append(investment)
        
        return investments

if __name__ == "__main__":
    # Test du parser avec vos fichiers
    print("🧪 Test du parser PEA...")
    
    parser = PEAParser("test-user")
    
    # Remplacer par vos vrais chemins de fichiers
    releve_path = "data/raw/releve_pea_avril_2025.pdf"
    evaluation_path = "data/raw/evaluation_pea_avril_2025.pdf"
    
    if os.path.exists(releve_path) and os.path.exists(evaluation_path):
        investissements, flux_tresorerie, positions = parser.parse_pdf_files(releve_path, evaluation_path)
        
        print(f"📊 Résultats: {len(investissements)} investissements, {len(flux_tresorerie)} flux, {len(positions)} positions")
    else:
        print("⚠️  Fichiers PDF non trouvés pour le test")