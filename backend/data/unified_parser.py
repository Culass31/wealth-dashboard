# ===== backend/data/unified_parser.py - PARSER UNIFIÉ EXPERT =====
import pandas as pd
import pdfplumber
import numpy as np
from typing import List, Dict, Tuple, Optional, Any
from datetime import datetime
import uuid
import re
import os
import logging
from pprint import pprint
from backend.utils.file_helpers import (
    standardize_date, clean_amount, clean_string_operation, safe_get, 
    normalize_text, get_column_by_normalized_name
)
from backend.data.parser_constants import PRETUP_SHEET_NAMES, PLATFORM_MAPPING

class UnifiedPortfolioParser:
    """Parser unifié pour toutes les plateformes d'investissement"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.pea_liquidity_balance = None
        self.pretup_liquidity_balance = None
        self.platform_methods = {
            'lpb': self._parse_lpb,
            'pretup': self._parse_pretup, 
            'bienpreter': self._parse_bienpreter,
            'homunity': self._parse_homunity,
            'assurance_vie': self._parse_assurance_vie,
            'pea': self._parse_pea
        }
    
    def _validate_data(self, data: List[Dict], required_fields: List[str], platform: str):
        """Vérifie que les champs requis ne sont pas vides dans les données parsées."""
        for i, item in enumerate(data):
            for field in required_fields:
                if field not in item or item[field] is None or (isinstance(item[field], str) and not item[field].strip()):
                    logging.warning(f"Validation {platform.upper()}: Champ manquant ou vide '{field}' dans l'élément {i}. Données: {item}")

    def parse_platform(self, file_path: str, platform_name: str) -> Dict[str, List[Dict]]:
        """Point d'entrée principal pour parser une plateforme"""
        logging.info(f"Début du parsing pour la plateforme {platform_name.upper()} avec le fichier : {file_path}")
        
        # Convertir le nom complet en clé abrégée pour la recherche dans platform_methods
        platform_key = None
        for key, name in PLATFORM_MAPPING.items():
            if name == platform_name:
                platform_key = key
                break

        if platform_key not in self.platform_methods:
            logging.error(f"Plateforme non supportée : {platform_name}")
            raise ValueError(f"Plateforme non supportée : {platform_name}")
        
        try:
            # Passer le mode verbeux à la méthode de la plateforme si elle l'accepte
            method = self.platform_methods[platform_key]
            import inspect
            sig = inspect.signature(method)
            if 'verbose' in sig.parameters:
                return method(file_path, verbose=self.verbose)
            else:
                return method(file_path)
        except Exception:
            logging.exception(f"Erreur critique lors du parsing de la plateforme {platform_name}")
            return {
                "investments": [],
                "cash_flows": [],
                "portfolio_positions": [],
                "liquidity_balances": []
            }

    # ===== LPB (LA PREMIÈRE BRIQUE) =====
    def _parse_lpb(self, file_path: str) -> Dict[str, List[Dict]]:
        """[FINAL V4] Parser LPB avec une logique de classification et de mise à jour entièrement revue."""
        logging.info("Début du parsing pour La Première Brique avec la logique finale V4.")
        
        try:
            xls = pd.ExcelFile(file_path)
            projects_df = pd.read_excel(xls, sheet_name='Projets')
            account_df = pd.read_excel(xls, sheet_name='Relevé compte')
        except Exception as e:
            logging.error(f"Erreur critique lors de la lecture des onglets principaux du fichier LPB : {e}")
            return {"investments": [], "cash_flows": [], "portfolio_positions": [], "liquidity_balances": []}

        investment_map_by_name, investment_map_by_id = self._parse_lpb_projects(projects_df)
        schedules = self._parse_lpb_schedules(xls, investment_map_by_name)
        cash_flows_df = self._parse_lpb_account(account_df, schedules, investment_map_by_name)
        
        cash_flows = cash_flows_df.to_dict(orient='records')
        self._update_investments_from_cashflows(self.investments, cash_flows)
        
        self._validate_data(self.investments, ['id', 'user_id', 'platform', 'project_name', 'invested_amount', 'status'], 'LPB')
        self._validate_data(cash_flows, ['id', 'user_id', 'platform', 'flow_type', 'flow_direction', 'net_amount', 'transaction_date'], 'LPB')
        
        logging.info(f"Parsing LPB terminé. {len(self.investments)} investissements et {len(cash_flows)} flux trouvés.")

        return {
            "investments": self.investments,
            "cash_flows": cash_flows,
            "portfolio_positions": [],
            "liquidity_balances": []
        }

    def _parse_lpb_schedules(self, xls: pd.ExcelFile, investment_map_by_name: Dict[str, str]) -> Dict[str, pd.DataFrame]:
        schedules = {}
        ignored_sheets = ['Projets', 'Relevé compte']
        numeric_cols = ['partducapital', 'partdesinterets', 'interetsrembourses', 'bonusverse', 'csgcrds', 'ir', 'partdubonus', 'montantapayer', 'echeance']

        for sheet_name in xls.sheet_names:
            if sheet_name in ignored_sheets: continue
            
            normalized_sheet_name = normalize_text(sheet_name)
            investment_id = investment_map_by_name.get(normalized_sheet_name)
            
            if investment_id:
                try:
                    df = pd.read_excel(xls, sheet_name=sheet_name)
                    df.columns = [normalize_text(col) for col in df.columns]
                    for col_name in numeric_cols:
                        if col_name in df.columns:
                            df[col_name] = df[col_name].apply(lambda x: clean_amount(x))
                    schedules[investment_id] = df

                    # --- NOUVELLE LOGIQUE POUR duration_months ---
                    # Calcule la durée en mois à partir du numéro d'échéance le plus élevé
                    if 'echeance' in df.columns:
                        max_echeance = df['echeance'].max()
                        if pd.notna(max_echeance):
                            # Met à jour l'objet investissement directement
                            investment = next((inv for inv in self.investments if inv['id'] == investment_id), None)
                            if investment:
                                investment['duration_months'] = int(max_echeance)
                                logging.info(f"LPB: Durée ({max_echeance} mois) mise à jour pour le projet {investment['project_name']}")

                    # --- NOUVELLE LOGIQUE POUR le statut 'delayed' ---
                    # Vérifie la présence de 'prolongation' dans le DataFrame de l'échéancier
                    prolongation_detected = df.astype(str).apply(lambda x: x.str.contains('prolongation', case=False)).any().any()
                    
                    if prolongation_detected:
                        investment = next((inv for inv in self.investments if inv['id'] == investment_id), None)
                        if investment:
                            investment['is_delayed'] = True
                            # Ne met à jour le statut à 'delayed' que s'il n'est pas déjà 'completed'
                            if investment['status'] != 'completed':
                                investment['status'] = 'delayed'
                            logging.warning(f"LPB: Prolongation détectée pour le projet {investment['project_name']}. Statut mis à jour à 'delayed'.")

                except Exception as e:
                    logging.warning(f"Impossible de lire l'échéancier pour le projet '{sheet_name}'. Erreur: {e}")
        return schedules

    def _parse_lpb_projects(self, df: pd.DataFrame) -> Tuple[Dict[str, str], Dict[str, Dict]]:
        self.investments = []
        investment_map_by_name = {}
        investment_map_by_id = {}
        
        for _, row in df.iterrows():
            project_name = safe_get(row, 'Nom du projet')
            if pd.isna(project_name) or "Nom du projet" in project_name: continue

            invested_amount = clean_amount(safe_get(row, 'Montant investi (€)', 0))
            status_from_file = safe_get(row, 'Statut', '').lower()
            status = 'completed' if 'remboursée' in status_from_file else 'active'

            investment = {
                'id': str(uuid.uuid4()), 'user_id': self.user_id, 'platform': 'La Première Brique',
                'investment_type': 'crowdfunding', 'asset_class': 'real_estate', 'project_name': project_name,
                'company_name': project_name, 'invested_amount': invested_amount,
                'annual_rate': clean_amount(safe_get(row, 'Taux annuel total (%)', 0)),
                'capital_repaid': 0.0, 'remaining_capital': invested_amount,
                'duration_months': None, 'investment_date': standardize_date(safe_get(row, 'Date de collecte (JJ/MM/AAAA)')),
                'signature_date': standardize_date(safe_get(row, 'Date de signature (JJ/MM/AAAA)')),
                'expected_end_date': standardize_date(safe_get(row, 'Date de remboursement maximale (JJ/MM/AAAA)')),
                'actual_end_date': None, 'status': status, 'is_delayed': False,
                'created_at': datetime.now().isoformat(), 'updated_at': datetime.now().isoformat(),
            }
            self.investments.append(investment)
            investment_map_by_name[normalize_text(project_name)] = investment['id']
            investment_map_by_id[investment['id']] = investment
        
        return investment_map_by_name, investment_map_by_id

    def _parse_lpb_account(self, df_account: pd.DataFrame, lpb_schedules: Dict[str, pd.DataFrame], investment_map: Dict[str, str]) -> pd.DataFrame:
        cash_flows = []
        df = df_account
        df['Date d’exécution'] = pd.to_datetime(df['Date d’exécution'], dayfirst=True, errors='coerce')
        df = df.sort_values(by='Date d’exécution').reset_index(drop=True)

        for _, row in df.iterrows():
            nature = safe_get(row, 'Nature de la transaction', '').strip()
            if not nature: continue

            flow_type, flow_direction, should_ignore = self._classify_lpb_transaction(nature)
            if should_ignore:
                continue

            transaction_date = pd.to_datetime(row['Date d’exécution']).strftime('%Y-%m-%d')
            gross_amount_from_releve = clean_amount(safe_get(row, 'Montant', 0))
            
            linked_investment_id = None
            for project_name_key, inv_id in investment_map.items():
                if project_name_key in normalize_text(nature):
                    linked_investment_id = inv_id
                    break
            
            gross_amount = abs(gross_amount_from_releve)
            net_amount = gross_amount_from_releve
            tax_amount, capital_amount, interest_amount = 0.0, 0.0, 0.0

            if flow_type == 'repayment':
                if linked_investment_id and linked_investment_id in lpb_schedules:
                    schedule_df = lpb_schedules[linked_investment_id]
                    echeance_col = get_column_by_normalized_name(schedule_df, 'echeance')
                    matched_row = None
                    installment_match = re.search(r'mensualit\S*\s+n\D*(\d+)', nature, re.IGNORECASE)
                    
                    if installment_match and echeance_col is not None:
                        installment_number = int(installment_match.group(1))
                        matched_rows = schedule_df[schedule_df[echeance_col] == installment_number]
                        if not matched_rows.empty:
                            matched_row = matched_rows.iloc[0]

                    if matched_row is not None:
                        capital_amount = clean_amount(safe_get(matched_row, 'partducapital', 0))
                        interest_amount = clean_amount(safe_get(matched_row, 'partdesinterets', 0)) + clean_amount(safe_get(matched_row, 'partdubonus', 0))
                        tax_amount = clean_amount(safe_get(matched_row, 'csgcrds', 0)) + clean_amount(safe_get(matched_row, 'ir', 0))
                        net_amount = gross_amount - tax_amount
            
            elif flow_type == 'investment':
                if flow_direction == 'out':
                    net_amount = -gross_amount
                else:  # Annulation, direction 'in'
                    net_amount = gross_amount
            elif flow_type == 'bonus': interest_amount = gross_amount
            elif flow_type == 'withdrawal': net_amount = -gross_amount

            cash_flows.append({
                'id': str(uuid.uuid4()), 'investment_id': linked_investment_id, 'user_id': self.user_id,
                'platform': 'La Première Brique', 'flow_type': flow_type, 'flow_direction': flow_direction,
                'gross_amount': round(gross_amount, 2), 'net_amount': round(net_amount, 2),
                'tax_amount': round(tax_amount, 2), 'capital_amount': round(capital_amount, 2),
                'interest_amount': round(interest_amount, 2), 'transaction_date': transaction_date,
                'status': 'completed', 'description': f"{nature} - {safe_get(row, 'Détails', '')}",
                'created_at': datetime.now().isoformat()
            })
        
        return pd.DataFrame(cash_flows)
    
    def _classify_lpb_transaction(self, nature: str) -> Tuple[str, str, bool]:
        nature_lower = nature.lower().strip()
        if nature_lower.startswith('remboursement mensualité'): return 'repayment', 'in', False
        if nature_lower.startswith('annulation de la souscription'): return 'investment', 'in', False
        if nature_lower.startswith('souscription au projet'): return 'investment', 'out', False
        if nature_lower.startswith('rémunération code cadeau'): return 'bonus', 'in', False
        if nature_lower == 'crédit du compte': return 'deposit', 'in', False
        if nature_lower == "retrait de l'épargne": return 'withdrawal', 'out', False
        if nature_lower in ['csg/crds', 'prélèvement ir']: return 'tax', 'out', True
        return 'other', 'in', False

    # ===== BIENPRÊTER =====
    def _parse_bienpreter(self, file_path: str) -> Dict[str, List[Dict]]:
        """Parser BienPrêter robuste avec post-traitement pour la cohérence des données."""
        logging.info("Début du parsing pour BienPrêter.")
        try:
            projects_df = pd.read_excel(file_path, sheet_name='Projets')
            account_df = pd.read_excel(file_path, sheet_name='Relevé compte')
        except Exception as e:
            logging.error(f"Erreur lors de la lecture des onglets du fichier BienPrêter : {e}")
            return {"investments": [], "cash_flows": [], "portfolio_positions": [], "liquidity_balances": []}

        investments, investment_map = self._parse_bienpreter_projects(projects_df)
        cash_flows = self._parse_bienpreter_account(account_df, investment_map)
        
        # Post-traitement pour mettre à jour les investissements avec les données des flux
        self._update_investments_from_cashflows(investments, cash_flows)

        logging.info(f"Parsing BienPrêter terminé. {len(investments)} investissements et {len(cash_flows)} flux trouvés.")
        
        return {
            "investments": investments,
            "cash_flows": cash_flows,
            "portfolio_positions": [],
            "liquidity_balances": []
        }

    def _parse_bienpreter_projects(self, df: pd.DataFrame) -> Tuple[List[Dict], Dict[str, str]]:
        """Parse les projets BienPrêter et retourne les investissements et une table de correspondance."""
        investments = []
        investment_map = {}
        
        for _, row in df.iterrows():
            project_name = safe_get(row, 'Projet')
            if pd.isna(project_name) or "Projet" in project_name:
                continue

            platform_id = str(safe_get(row, 'N°Contrat', ''))
            if not platform_id:
                logging.warning(f"N°Contrat manquant pour le projet {project_name}, liaison impossible.")
                continue

            investment = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'BienPrêter',
                'platform_id': platform_id,
                'investment_type': 'crowdfunding',
                'asset_class': 'real_estate',
                'project_name': project_name,
                'company_name': safe_get(row, 'Entreprise', ''),
                'invested_amount': clean_amount(safe_get(row, 'Montant', 0)),
                'annual_rate': clean_amount(safe_get(row, 'Taux', 0)),
                'duration_months': int(round(clean_amount(safe_get(row, 'Durée de remboursements (mois)', 0)))),
                'investment_date': standardize_date(safe_get(row, 'Date de financement')),
                'signature_date': standardize_date(safe_get(row, 'Date de financement')),
                'expected_end_date': standardize_date(safe_get(row, 'Date de clôture')), # Corrigé
                'actual_end_date': None, # Sera calculé en post-traitement
                'status': self._map_bienpreter_status(safe_get(row, 'Statut', '')),
                'capital_repaid': 0, 
                'remaining_capital': clean_amount(safe_get(row, 'Montant', 0)),
                'is_delayed': False,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
            }
            investments.append(investment)
            investment_map[platform_id] = investment['id']
        
        return investments, investment_map

    def _parse_bienpreter_account(self, df: pd.DataFrame, investment_map: Dict[str, str]) -> List[Dict]:
        """Parse le relevé BienPrêter avec une liaison fiable par N°Contrat."""
        cash_flows = []
        
        for _, row in df.iterrows():
            operation = safe_get(row, 'Opération', '')
            if pd.isna(operation) or "Opération" in operation:
                continue

            date_transaction = standardize_date(safe_get(row, 'Date'))
            if not date_transaction:
                continue

            platform_id = str(safe_get(row, 'N°Contrat', ''))
            linked_investment_id = investment_map.get(platform_id)

            flow_type, flow_direction = self._classify_bienpreter_transaction(operation)
            net_amount = clean_amount(safe_get(row, 'Montant', 0))
            gross_amount, tax_amount, capital_amount, interest_amount = 0, 0, 0, 0

            if flow_type == 'repayment':
                capital_amount = clean_amount(safe_get(row, 'Capital remboursé', 0))
                interest_amount = clean_amount(safe_get(row, 'Intérêts remboursés', 0))
                tax_amount = clean_amount(safe_get(row, 'Prélèvements fiscaux et sociaux', 0))
                gross_amount = capital_amount + interest_amount
                # Le net_amount est déjà correct dans le fichier
            elif flow_type == 'investment':
                gross_amount = abs(net_amount)
                flow_direction = 'out'
            else: # deposit, interest (bonus)
                gross_amount = net_amount

            cash_flow = {
                'id': str(uuid.uuid4()),
                'investment_id': linked_investment_id,
                'user_id': self.user_id,
                'platform': 'BienPrêter',
                'flow_type': flow_type,
                'flow_direction': flow_direction,
                'gross_amount': gross_amount,
                'net_amount': net_amount,
                'tax_amount': tax_amount,
                'capital_amount': capital_amount,
                'interest_amount': interest_amount,
                'transaction_date': date_transaction,
                'status': 'completed',
                'description': f"{operation} - {safe_get(row, 'Projet', '')}",
                'created_at': datetime.now().isoformat()
            }
            cash_flows.append(cash_flow)
        
        return cash_flows

    def _classify_bienpreter_transaction(self, operation: str) -> Tuple[str, str]:
        """Classification robuste des opérations BienPrêter."""
        op_lower = operation.lower()
        if 'remboursement' in op_lower:
            return 'repayment', 'in'
        if 'investissement' in op_lower or 'offre acceptée' in op_lower:
            return 'investment', 'out'
        if 'dépôt' in op_lower:
            return 'deposit', 'in'
        if 'bonus' in op_lower:
            return 'bonus', 'in' # Nouveau type 'bonus' pour les codes cadeaux
        return 'other', 'in'

    def _update_investments_from_cashflows(self, investments: List[Dict], cash_flows: List[Dict]):
        """
        [CORRIGÉ] Met à jour les investissements après avoir traité tous les flux.
        C'est la source de vérité pour le capital remboursé et le statut final (completed/delayed).
        """
        investment_map = {inv['id']: inv for inv in investments}
        
        capital_repaid_from_flows = {inv_id: 0.0 for inv_id in investment_map.keys()}
        repayment_dates = {inv_id: [] for inv_id in investment_map.keys()}

        for cf in cash_flows:
            inv_id = cf.get('investment_id')
            if inv_id and inv_id in investment_map:
                if cf.get('flow_type') == 'repayment':
                    capital_repaid_from_flows[inv_id] += cf.get('capital_amount', 0)
                    repayment_dates[inv_id].append(cf['transaction_date'])

        for inv_id, inv in investment_map.items():
            calculated_repaid = capital_repaid_from_flows[inv_id]
            inv['capital_repaid'] = calculated_repaid
            inv['remaining_capital'] = inv['invested_amount'] - calculated_repaid

            # Logique de mise à jour du statut
            # Utilise une tolérance de 1 centime pour la comparaison des montants
            if inv['invested_amount'] > 0 and inv['remaining_capital'] <= 0.01:
                inv['status'] = 'completed'
                if repayment_dates[inv_id]:
                    inv['actual_end_date'] = max(repayment_dates[inv_id])
            elif inv.get('expected_end_date'):
                try:
                    expected_end = datetime.strptime(inv['expected_end_date'], '%Y-%m-%d')
                    if expected_end.date() < datetime.now().date() and inv['status'] != 'completed':
                        inv['is_delayed'] = True
                        inv['status'] = 'delayed'
                except (ValueError, TypeError):
                    pass
            
            inv['updated_at'] = datetime.now().isoformat()

    # ===== HOMUNITY =====
    def _parse_homunity(self, file_path: str) -> Dict[str, List[Dict]]:
        """Parser Homunity avec liaison par date et calculs financiers précis."""
        logging.info("Début du parsing pour Homunity avec la logique de liaison par date.")
        
        try:
            projects_df = pd.read_excel(file_path, sheet_name='Projets')
            account_df = pd.read_excel(file_path, sheet_name='Relevé compte')
        except Exception as e:
            logging.error(f"Erreur lors de la lecture des onglets du fichier Homunity : {e}")
            return {"investments": [], "cash_flows": [], "portfolio_positions": [], "liquidity_balances": []}

        investments, investment_map, repayment_schedule = self._parse_homunity_projects(projects_df)
        cash_flows = self._parse_homunity_account(account_df, investment_map, repayment_schedule)
        
        logging.info(f"Parsing Homunity terminé. {len(investments)} investissements et {len(cash_flows)} flux trouvés.")
        
        return {
            "investments": investments,
            "cash_flows": cash_flows,
            "portfolio_positions": [],
            "liquidity_balances": []
        }

    def _normalize_homunity_key(self, promoter: str, project: str) -> Tuple[str, str]:
        """Normalise le couple (promoteur, projet) pour une liaison fiable."""
        promoter_clean = str(promoter).strip().lower()
        project_clean = str(project).strip().lower()
        project_clean = project_clean.replace("investissement sur le projet", "").replace("remboursement de projet", "").strip()
        return (promoter_clean, project_clean)

    def _parse_homunity_projects(self, df: pd.DataFrame) -> Tuple[List[Dict], Dict[Tuple[str, str], Dict], Dict[Tuple[str, str, str], Dict]]:
        """Parse les projets en gérant les lignes de remboursement multiples pour un même projet."""
        investments = []
        investment_map = {}
        repayment_schedule = {}
        current_lookup_key = None

        for _, row in df.iterrows():
            promoter = safe_get(row, 'Promoteur', '')
            project_name = safe_get(row, 'Projet', '')

            # Si la ligne définit un nouveau projet, on met à jour le projet courant
            if promoter and project_name and "Promoteur" not in promoter:
                current_lookup_key = self._normalize_homunity_key(promoter, project_name)
                
                if current_lookup_key not in investment_map:
                    # Calculate total capital repaid for this project
                    project_rows = df[(df['Promoteur'].astype(str).str.strip().str.lower() == promoter.lower().strip()) &
                                      (df['Projet'].astype(str).str.strip().str.lower() == project_name.lower().strip())]
                    
                    total_capital_repaid_for_project = 0
                    for _, p_row in project_rows.iterrows():
                        remb_val = clean_amount(safe_get(p_row, 'Remb.', 0))
                        interets_nets_val = clean_amount(safe_get(p_row, 'Intérets Nets', 0))
                        total_capital_repaid_for_project += (remb_val - interets_nets_val)

                    invested_amount = clean_amount(safe_get(row, 'Invest.', 0))
                    remaining_capital = invested_amount - total_capital_repaid_for_project

                    status = self._map_homunity_status(safe_get(row, 'Statut', ''))
                    actual_end_date = None

                    # Check if project is completed
                    if abs(invested_amount - total_capital_repaid_for_project) < 0.01 and invested_amount > 0:
                        status = 'completed'
                        repayment_dates = [standardize_date(safe_get(r, 'Date remb.')) for _, r in project_rows.iterrows() if standardize_date(safe_get(r, 'Date remb.'))]
                        if repayment_dates:
                            actual_end_date = max(repayment_dates)

                    investment = {
                        'id': str(uuid.uuid4()),
                        'user_id': self.user_id,
                        'platform': 'Homunity',
                        'investment_type': 'crowdfunding',
                        'asset_class': 'real_estate',
                        'project_name': project_name,
                        'company_name': promoter,
                        'invested_amount': invested_amount,
                        'annual_rate': clean_amount(safe_get(row, 'Taux d’intérêt', 0)),
                        'signature_date': standardize_date(safe_get(row, 'Date de souscription')),
                        'investment_date': None,  # Sera mis à jour depuis le relevé
                        'expected_end_date': standardize_date(safe_get(row, 'Date de remb projet')),
                        'actual_end_date': actual_end_date,
                        'status': status,
                        'capital_repaid': total_capital_repaid_for_project,
                        'remaining_capital': remaining_capital,
                        'created_at': datetime.now().isoformat(),
                        'updated_at': datetime.now().isoformat(),
                    }
                    investments.append(investment)
                    investment_map[current_lookup_key] = investment

            # Si la ligne contient une date de remboursement, on l'ajoute à l'échéancier du projet courant
            repayment_date = standardize_date(safe_get(row, 'Date remb.'))
            remb_amount = clean_amount(safe_get(row, 'Remb.', 0))
            if repayment_date and remb_amount > 0 and current_lookup_key:
                schedule_key = (*current_lookup_key, repayment_date)
                repayment_schedule[schedule_key] = {
                    'remb': remb_amount,
                    'interets_nets': clean_amount(safe_get(row, 'Intérets Nets', 0)),
                    'impots': clean_amount(safe_get(row, 'Impots', 0))
                }
        
        return investments, investment_map, repayment_schedule

    def _parse_homunity_account(self, df: pd.DataFrame, investment_map: Dict[Tuple[str, str], Dict], repayment_schedule: Dict[Tuple[str, str, str], Dict]) -> List[Dict]:
        """Parse le relevé, lie les flux à l'échéancier par (Promoteur, Projet, Date) et effectue les calculs précis."""
        cash_flows = []
        
        for _, row in df.iterrows():
            if pd.isna(safe_get(row, 'Type de mouvement')) or "Type de mouvement" in str(safe_get(row, 'Type de mouvement')):
                continue

            transaction_date = standardize_date(safe_get(row, 'Date'))
            if not transaction_date:
                continue

            move_type = safe_get(row, 'Type de mouvement', '').lower()
            message = safe_get(row, 'Message', '')
            promoter = safe_get(row, 'Nom du promoteur', '')
            net_amount_from_releve = clean_amount(safe_get(row, 'Montant', 0))

            flow_type, linked_investment_id = 'other', None
            flow_direction = 'in' if net_amount_from_releve > 0 else 'out'
            gross_amount, net_amount, tax_amount, capital_amount, interest_amount = 0, 0, 0, 0, 0
            
            lookup_key = self._normalize_homunity_key(promoter, message)
            investment = investment_map.get(lookup_key)

            if 'transfert' in move_type:
                net_amount = abs(net_amount_from_releve)
                if investment:
                    linked_investment_id = investment['id']

                if 'investissement' in message.lower():
                    flow_type = 'investment'
                    flow_direction = 'out'
                    gross_amount = net_amount
                    if investment and not investment.get('investment_date'):
                        investment['investment_date'] = transaction_date
                        investment['signature_date'] = transaction_date

                elif 'remboursement' in message.lower():
                    flow_type = 'repayment'
                    flow_direction = 'in'
                    schedule_key = (*lookup_key, transaction_date)
                    schedule_details = repayment_schedule.get(schedule_key)

                    if schedule_details:
                        remb_from_schedule = schedule_details.get('remb', 0)
                        interets_nets = schedule_details.get('interets_nets', 0)
                        impots = schedule_details.get('impots', 0)

                        tax_amount = impots
                        interest_amount = interets_nets + impots
                        capital_amount = remb_from_schedule - interets_nets
                        gross_amount = remb_from_schedule + impots
                        
                        if abs(net_amount - remb_from_schedule) > 0.01:
                            logging.warning(f"Incohérence de montant pour {schedule_key}: Relevé={net_amount} vs Echéancier={remb_from_schedule}")
                    else:
                        logging.warning(f"Aucun détail d'échéance trouvé pour la clé {schedule_key}. Le flux sera enregistré sans ventilation.")
                        gross_amount = net_amount

            elif 'retrait' in move_type:
                flow_type = 'withdrawal'
                flow_direction = 'out'
                net_amount = abs(net_amount_from_releve)
                gross_amount = net_amount
            
            elif 'approvisionnement' in move_type:
                flow_type = 'deposit'
                flow_direction = 'in'
                net_amount = abs(net_amount_from_releve)
                gross_amount = net_amount
            
            else:
                continue

            cash_flow = {
                'id': str(uuid.uuid4()),
                'investment_id': linked_investment_id,
                'user_id': self.user_id,
                'platform': 'Homunity',
                'flow_type': flow_type,
                'flow_direction': flow_direction,
                'gross_amount': gross_amount,
                'net_amount': net_amount,
                'tax_amount': tax_amount,
                'capital_amount': capital_amount,
                'interest_amount': interest_amount,
                'transaction_date': transaction_date,
                'status': 'completed' if safe_get(row, 'Statut', '').lower() == 'succès' else 'pending',
                'description': message,
                'created_at': datetime.now().isoformat()
            }
            cash_flows.append(cash_flow)

        return cash_flows

    # ===== PRETUP =====
    def _parse_pretup(self, file_path: str) -> Dict[str, List[Dict]]:
        """
        Parser PretUp entièrement revu pour une robustesse et une précision maximales.
        Lit tous les onglets de données en une seule fois pour garantir la cohérence.
        """
        logging.info("Début du parsing PretUp avec la nouvelle méthode robuste.")
        
        try:
            # 1. Charger toutes les données pertinentes en une seule fois
            all_data = self._load_all_pretup_sheets(file_path)
            
            # Normaliser les colonnes du relevé de compte une fois pour toutes
            if 'releve' in all_data and not all_data['releve'].empty:
                all_data['releve'].columns = [normalize_text(col) for col in all_data['releve'].columns]

            # 2. Extraire les informations de base sur les projets
            investments = self._extract_pretup_projects(all_data)
            
            # 4. Parser le relevé de compte pour les flux de trésorerie
            cash_flows = self._parse_pretup_account(all_data['releve'], investments)
            
            # 5. Extraire le solde de liquidités
            liquidity_balance = self._extract_pretup_liquidity(all_data['releve'])

            logging.info(f"Parsing PretUp terminé avec succès. {len(investments)} investissements et {len(cash_flows)} flux trouvés.")
            
            return {
                "investments": investments,
                "cash_flows": cash_flows,
                "portfolio_positions": [],
                "liquidity_balances": [liquidity_balance] if liquidity_balance else []
            }

        except Exception as e:
            logging.exception("Erreur critique lors du parsing de PretUp.")
            return {"investments": [], "cash_flows": [], "portfolio_positions": [], "liquidity_balances": []}

    def _load_all_pretup_sheets(self, file_path: str) -> Dict[str, pd.DataFrame]:
        """
        Charge tous les onglets nécessaires du fichier PretUp de manière robuste.
        Tente de trouver une correspondance même avec de légères variations de nom.
        """
        all_data = {}
        try:
            xls = pd.ExcelFile(file_path)
            actual_sheet_names = xls.sheet_names
            logging.info(f"Onglets détectés dans le fichier : {actual_sheet_names}")
        except Exception as e:
            logging.error(f"Impossible de lire les noms d'onglets du fichier Excel : {e}")
            # Fallback au cas où la lecture des noms d'onglets échoue
            for key in PRETUP_SHEET_NAMES:
                all_data[key] = pd.DataFrame()
            return all_data

        # Normalise les noms pour la correspondance (minuscules, sans espaces superflus)
        normalized_actual_names = {name.strip().lower(): name for name in actual_sheet_names}

        for key, expected_name in PRETUP_SHEET_NAMES.items():
            normalized_expected = expected_name.strip().lower()
            
            # Tente de trouver une correspondance exacte (après normalisation)
            found_name = normalized_actual_names.get(normalized_expected)

            if found_name:
                try:
                    all_data[key] = pd.read_excel(xls, sheet_name=found_name)
                    logging.info(f"Onglet '{found_name}' (attendu: '{expected_name}') chargé avec succès.")
                except Exception as e:
                    logging.warning(f"L'onglet '{found_name}' a été trouvé mais n'a pas pu être chargé. Erreur: {e}. Il sera ignoré.")
                    all_data[key] = pd.DataFrame()
            else:
                logging.warning(f"L'onglet attendu '{expected_name}' n'a pas été trouvé dans le fichier. Il sera ignoré.")
                all_data[key] = pd.DataFrame()
                
        return all_data

    def _extract_pretup_projects(self, all_data: Dict[str, pd.DataFrame]) -> List[Dict]:
        """Extrait et normalise les projets depuis chaque onglet d'offres en utilisant les en-têtes de colonnes fournis."""
        investments_data = []
        investment_map = {} # Initialiser investment_map ici

        # Fonction interne pour traiter une ligne et éviter la répétition de code
        def process_row(row, status, capital_col_name):
            project_name = safe_get(row, 'Nom du Projet')
            if pd.isna(project_name) or "TOTAUX" in str(project_name):
                return None

            invested_amount = clean_amount(safe_get(row, 'Montant Offre', 0))
            remaining_capital = clean_amount(safe_get(row, capital_col_name, 0))
            capital_repaid = invested_amount - remaining_capital

            return {
                'platform_id': str(safe_get(row, 'Numéro Offre', '')),
                'project_name': project_name,
                'company_name': safe_get(row, 'Entreprise'),
                'invested_amount': invested_amount,
                'remaining_capital': remaining_capital,
                'capital_repaid': capital_repaid,
                'status': status
            }

        # Traitement des différents onglets d'offres
        tabs_to_process = {
            'offres_sains': ('active', 'Capital Restant dû sain'),
            'offres_procedures': ('in_procedure', 'Capital Restant dû'),
            'offres_perdus': ('defaulted', 'Capital Restant dû')
        }

        for tab_key, (status, capital_col) in tabs_to_process.items():
            df = all_data.get(tab_key, pd.DataFrame())
            if not df.empty:
                for _, row in df.iterrows():
                    data = process_row(row, status, capital_col)
                    if data:
                        investments_data.append(data)

        # Création finale des objets investissements
        investments = []
        for data in investments_data:
            investment = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'PretUp',
                'investment_type': 'crowdfunding',
                'asset_class': 'fixed_income',
                'investment_date': None,
                'signature_date': None,
                'expected_end_date': None,
                'actual_end_date': None,
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat(),
                **data
            }
            investments.append(investment)
            investment_map[investment['platform_id']] = investment # Remplir investment_map ici

        # 1. Extraire les dates depuis les échéanciers
        all_echeances_df = pd.concat([
            all_data.get('echeances_sains', pd.DataFrame()),
            all_data.get('echeances_procedures', pd.DataFrame()),
            all_data.get('echeances_perdus', pd.DataFrame())
        ], ignore_index=True)

        if not all_echeances_df.empty:
            all_echeances_df.columns = [str(c).strip() for c in all_echeances_df.columns]
            all_echeances_df['Date Encaissement'] = pd.to_datetime(all_echeances_df['Date Encaissement'], dayfirst=True, errors='coerce')
            all_echeances_df = all_echeances_df.sort_values(by=['Numéro Offre', 'Date Encaissement'])
            
            # Calculer duration_months en comptant le nombre d'échéances par projet
            echeance_counts = all_echeances_df.groupby('Numéro Offre').size().to_dict()

            schedule_dates = all_echeances_df.groupby('Numéro Offre')['Date Encaissement'].agg(['min', 'max']).to_dict('index')

            for platform_id, inv in investment_map.items():
                str_platform_id = str(platform_id)
                if str_platform_id in schedule_dates:
                    dates = schedule_dates[str_platform_id]
                    inv['signature_date'] = dates['min'].strftime('%Y-%m-%d') if pd.notna(dates['min']) else None
                    inv['expected_end_date'] = dates['max'].strftime('%Y-%m-%d') if pd.notna(dates['max']) else None
                
                # Mettre à jour duration_months avec le compte des échéances
                if str_platform_id in echeance_counts:
                    inv['duration_months'] = int(echeance_counts[str_platform_id])
                    logging.info(f"PretUp: Duration pour l'offre {str_platform_id} mise à jour à {inv['duration_months']} mois (nombre d'échéances).")
                else:
                    inv['duration_months'] = None

        # 2. Affiner le statut final pour les projets qui ne sont pas déjà en défaut ou en procédure
        for inv in investments:
            # Ne pas modifier les statuts déjà fixés comme 'in_procedure' ou 'defaulted'
            if inv['status'] in ['in_procedure', 'defaulted']:
                continue

            # Si le capital restant est nul, le projet est complété
            if inv.get('remaining_capital', 0) <= 0.01:
                inv['status'] = 'completed'
                if not inv.get('actual_end_date') and inv.get('expected_end_date'):
                    inv['actual_end_date'] = inv['expected_end_date']
            
            # Si le projet est toujours actif mais que la date de fin est passée, il est en retard
            elif inv['status'] == 'active' and inv.get('expected_end_date'):
                try:
                    expected_end = datetime.strptime(inv['expected_end_date'], '%Y-%m-%d')
                    if expected_end.date() < datetime.now().date():
                        inv['status'] = 'delayed'
                except (ValueError, TypeError):
                    pass
        
        return investments

    def _parse_pretup_account(self, df_releve: pd.DataFrame, investments: List[Dict]) -> List[Dict]:
        """
        Parse le relevé de compte PretUp et crée les flux de trésorerie.
        Liaison robuste par Numéro Offre ou par nom d'entreprise/projet.
        """
        logging.info("Début du parsing du relevé de compte PretUp.")
        cash_flows = []
        
        # Créer un dictionnaire pour un accès rapide aux investissements par platform_id
        investment_map_by_platform_id = {inv['platform_id']: inv for inv in investments if 'platform_id' in inv}
        
        # Créer un dictionnaire pour un accès rapide aux investissements par nom de projet/entreprise
        investment_map_by_name = {}
        for inv in investments:
            key = (normalize_text(inv.get('company_name', '')), normalize_text(inv.get('project_name', '')))
            investment_map_by_name[key] = inv

        if df_releve.empty:
            logging.warning("DataFrame du relevé PretUp est vide.")
            return []

        # Normaliser les noms de colonnes (déjà fait dans _parse_pretup maintenant)
        # df_releve.columns = [normalize_text(col) for col in df_releve.columns]

        for _, row in df_releve.iterrows():
            date_str = safe_get(row, 'date')
            type_transaction = safe_get(row, 'type', '') # Extraire le type de la colonne 'Type'
            operation = safe_get(row, 'libelle', '') # Utiliser 'Libellé' pour la description
            montant_debit_str = safe_get(row, 'debit')
            montant_credit_str = safe_get(row, 'credit')

            if pd.isna(date_str) or not operation or (pd.isna(montant_debit_str) and pd.isna(montant_credit_str)):
                continue

            transaction_date = self._parse_pretup_date(date_str)
            if not transaction_date:
                logging.warning(f"Date de transaction invalide pour la ligne: {row.to_dict()}")
                continue

            gross_amount = 0.0
            flow_direction = ''

            if pd.notna(montant_credit_str) and clean_amount(montant_credit_str) > 0:
                gross_amount = clean_amount(montant_credit_str)
                flow_direction = 'in'
            elif pd.notna(montant_debit_str) and clean_amount(montant_debit_str) > 0:
                gross_amount = clean_amount(montant_debit_str)
                flow_direction = 'out'
            
            if gross_amount == 0:
                continue

            flow_type = self._classify_pretup_transaction(type_transaction, flow_direction) # Utiliser le type de transaction
            
            linked_investment_id = None
            # Tenter de lier par Numéro Offre si disponible dans la description
            num_offre_match = re.search(r'offre n°(\d+)', operation, re.IGNORECASE)
            if num_offre_match:
                platform_id_from_op = num_offre_match.group(1)
                if platform_id_from_op in investment_map_by_platform_id:
                    linked_investment_id = investment_map_by_platform_id[platform_id_from_op]['id']
            
            # Si pas lié par Numéro Offre, tenter de lier par nom de projet/entreprise
            if not linked_investment_id:
                # Extraire le nom de l'entreprise/projet de l'opération
                # Exemple: "Remboursement mensuel - Projet XYZ - Entreprise ABC"
                project_name_match = re.search(r'projet (.+?)(?: - |$)', operation, re.IGNORECASE)
                company_name_match = re.search(r'entreprise (.+?)(?: - |$)', operation, re.IGNORECASE)
                
                op_project_name = project_name_match.group(1).strip() if project_name_match else ''
                op_company_name = company_name_match.group(1).strip() if company_name_match else ''

                lookup_key = (normalize_text(op_company_name), normalize_text(op_project_name))
                if lookup_key in investment_map_by_name:
                    linked_investment_id = investment_map_by_name[lookup_key]['id']
                elif op_project_name: # Fallback si seul le nom du projet est trouvé
                    for inv_key, inv_obj in investment_map_by_name.items():
                        if normalize_text(op_project_name) in inv_key[1]:
                            linked_investment_id = inv_obj['id']
                            break
            
            # Initialisation des montants détaillés
            net_amount = gross_amount
            tax_amount = 0.0
            capital_amount = 0.0
            interest_amount = 0.0

            # Récupérer les montants détaillés si disponibles dans le relevé
            capital_amount_releve = clean_amount(safe_get(row, 'part de capital', 0)) # Nom de colonne corrigé
            interest_amount_releve = clean_amount(safe_get(row, 'part interets bruts', 0))
            retenue_sociale_releve = clean_amount(safe_get(row, 'retenue a la source (cotisations sociales)', 0))
            retenue_forfaitaire_releve = clean_amount(safe_get(row, 'retenue a la source (prelevement forfaitaire)', 0))

            if flow_type == 'repayment':
                capital_amount = capital_amount_releve
                interest_amount = interest_amount_releve
                tax_amount = retenue_sociale_releve + retenue_forfaitaire_releve
                net_amount = gross_amount - tax_amount
            elif flow_type == 'tax':
                tax_amount = gross_amount
                net_amount = -gross_amount # Les taxes sont des sorties
            elif flow_type == 'investment':
                net_amount = -gross_amount # Les investissements sont des sorties
            
            # Ajuster le net_amount pour les sorties
            if flow_direction == 'out':
                net_amount = -abs(net_amount)
            else:
                net_amount = abs(net_amount)

            cash_flows.append({
                'id': str(uuid.uuid4()),
                'investment_id': linked_investment_id,
                'user_id': self.user_id,
                'platform': 'PretUp',
                'flow_type': flow_type,
                'flow_direction': flow_direction,
                'gross_amount': round(gross_amount, 2),
                'net_amount': round(net_amount, 2),
                'tax_amount': round(tax_amount, 2),
                'capital_amount': round(capital_amount, 2),
                'interest_amount': round(interest_amount, 2),
                'transaction_date': transaction_date,
                'status': 'completed',
                'description': operation,
                'created_at': datetime.now().isoformat()
            })
        
        logging.info(f"Parsing du relevé de compte PretUp terminé. {len(cash_flows)} flux trouvés.")
        return cash_flows

    def _classify_pretup_transaction(self, type_transaction: str, flow_direction: str) -> str:
        """
        Classifie le type de flux pour les transactions PretUp en se basant sur la colonne 'Type'.
        """
        type_lower = type_transaction.lower()

        if 'echeance' in type_lower or 'remboursement anticipé' in type_lower:
            return 'repayment'
        elif 'offre' in type_lower:
            return 'investment'
        elif 'alimentation' in type_lower:
            return 'deposit'
        elif 'impôts' in type_lower:
            return 'tax'
        elif 'virement sortant' in type_lower or 'retrait' in type_lower:
            return 'withdrawal'
        else:
            return 'other'

    def _extract_pretup_liquidity(self, df_releve: pd.DataFrame) -> Optional[Dict]:
        """
        Extrait le solde de liquidités le plus récent du relevé de compte PretUp.
        """
        logging.info("Extraction du solde de liquidités PretUp...")
        if df_releve.empty:
            logging.warning("DataFrame du relevé PretUp est vide, impossible d'extraire la liquidité.")
            return None

        # Assurer que les colonnes nécessaires existent et sont au bon format
        # Normaliser les noms de colonnes si ce n'est pas déjà fait
        df_releve.columns = [normalize_text(col) for col in df_releve.columns]

        # Trouver la colonne de date et de solde
        date_col = get_column_by_normalized_name(df_releve, 'date')
        solde_col = get_column_by_normalized_name(df_releve, 'solde')

        if not date_col or not solde_col:
            logging.warning(f"Colonnes 'date' ou 'solde' non trouvées dans le relevé PretUp. Colonnes disponibles: {df_releve.columns.tolist()}")
            return None

        df_releve[date_col] = pd.to_datetime(df_releve[date_col], errors='coerce')
        df_releve.dropna(subset=[date_col, solde_col], inplace=True)

        if df_releve.empty:
            logging.warning("Après nettoyage, le DataFrame du relevé PretUp est vide, impossible d'extraire la liquidité.")
            return None

        # Trier par date et prendre la dernière entrée
        latest_balance_row = df_releve.sort_values(by=date_col, ascending=False).iloc[0]
        
        balance_date = latest_balance_row[date_col].strftime('%Y-%m-%d')
        amount = clean_amount(latest_balance_row[solde_col])

        liquidity_balance = {
            'user_id': self.user_id,
            'platform': 'PretUp',
            'balance_date': balance_date,
            'amount': amount,
            'created_at': datetime.now().isoformat(),
            'updated_at': datetime.now().isoformat()
        }
        logging.info(f"Liquidité PretUp extraite : {amount} EUR à la date {balance_date}")
        return liquidity_balance

    # ===== ASSURANCE VIE =====    def _parse_assurance_vie(self, file_path: str) -> Dict[str, List[Dict]]:
        """Parser Assurance Vie ultra-robuste contre les erreurs de type"""
        
        try:
            df = pd.read_excel(file_path, sheet_name='Relevé compte')
        except Exception as e:
            logging.warning(f"Impossible de lire l'onglet 'Relevé compte' pour l'assurance vie : {e}, tentative avec le premier onglet.")
            try:
                df = pd.read_excel(file_path, sheet_name=0)  # Premier onglet
                logging.info("Lecture du premier onglet réussie.")
            except Exception as e_fallback:
                logging.error(f"Impossible de lire le fichier d'assurance vie {file_path}. Erreur : {e_fallback}", exc_info=True)
                return {
                    "investments": [],
                    "cash_flows": [],
                    "portfolio_positions": [],
                    "liquidity_balances": []
                }
        
        flux_tresorerie = []
        logging.info(f"Lecture du fichier d'assurance vie : {len(df)} lignes trouvées")
        
        for idx, row in df.iterrows():
            try:
                # Vérification robuste des lignes vides/headers
                date_raw = safe_get(row, 0)
                if pd.isna(date_raw) or date_raw in ["Date", "Type", None]:
                    continue
                
                # CORRECTION PRINCIPALE : Gestion robuste du type d'opération
                type_operation_raw = safe_get(row, 1, '')
                type_operation = str(type_operation_raw).lower() if type_operation_raw is not None else ''
                
                logging.debug(f"Ligne {idx}: Date={date_raw}, Type={type_operation_raw} -> '{type_operation}'")
                
                date_transaction = standardize_date(date_raw)
                montant = clean_amount(safe_get(row, 2, 0))
                if not date_transaction:
                    logging.warning(f"Ligne {idx}: Date invalide '{date_raw}', ligne ignorée.")
                    continue
                    
                if montant == 0:
                    logging.info(f"Montant nul, ligne ignorée.")
                    continue
                
                # Classification avec gestion des cas numériques
                if any(keyword in type_operation for keyword in ['dividende', 'dividend', 'coupon']):
                    flow_type = 'dividend'
                    flow_direction = 'in'
                    net_amount = montant
                    
                elif any(keyword in type_operation for keyword in ['frais', 'fee', 'commission']):
                    flow_type = 'fee'
                    flow_direction = 'out'
                    net_amount = -abs(montant)
                    
                elif any(keyword in type_operation for keyword in ['arrêté', 'arrete', 'cloture']):
                    continue  # Ignorer
                    
                elif any(keyword in type_operation for keyword in ['arbitrage', 'transfer']):
                    continue  # Ignorer
                    
                elif any(keyword in type_operation for keyword in ['versement', 'depot', 'apport']):
                    flow_type = 'deposit'
                    flow_direction = 'in'
                    net_amount = abs(montant)
                    
                elif type_operation.isdigit():
                    # Cas où c'est juste un code numérique
                    flow_type = 'other'
                    flow_direction = 'in' if montant > 0 else 'out'
                    net_amount = montant
                    
                else:
                    # Cas par défaut
                    flow_type = 'other'
                    flow_direction = 'in' if montant > 0 else 'out'
                    net_amount = montant
                
                # Créer le flux
                flux = {
                    'id': str(uuid.uuid4()),
                    'user_id': self.user_id,
                    'platform': 'Assurance_Vie',
                    
                    'flow_type': flow_type,
                    'flow_direction': flow_direction,
                    
                    'gross_amount': abs(montant),
                    'net_amount': montant, # Le montant a déjà le bon signe
                    'tax_amount': 0.0,
                    
                    'transaction_date': date_transaction,
                    'status': 'completed',
                    
                    'description': f"AV - {clean_string_operation(type_operation_raw, 'Transaction')}",
                    
                    'created_at': datetime.now().isoformat()
                }
                
                flux_tresorerie.append(flux)
                
            except Exception:
                logging.exception(f"Erreur inattendue lors du traitement de la ligne {idx} du fichier d'assurance vie.")
                continue
        
        logging.info(f"Parsing de l'assurance vie terminé : {len(flux_tresorerie)} flux extraits.")
        
        return {
            "investments": [],
            "cash_flows": flux_tresorerie,
            "portfolio_positions": [],
            "liquidity_balances": []
        }

    # ===== PEA =====
    def _parse_pea(self, releve_paths: Optional[List[str]] = None, evaluation_paths: Optional[List[str]] = None) -> Dict[str, List[Dict]]:
        """
        [CORRIGÉ] Parser PEA avec gestion multi-fichiers et portfolio_positions.
        Accepte des listes de chemins de fichiers pour un contrôle externe.
        """
        investments: List[Dict] = []
        cash_flows = []
        all_portfolio_positions = []

        # Parser relevés (transactions → cash_flows)
        if releve_paths:
            for releve_path in releve_paths:
                if os.path.exists(releve_path):
                    logging.info(f"Début du parsing du relevé PEA : {releve_path}")
                    cash_flows.extend(self._parse_pea_releve(releve_path))
                else:
                    logging.warning(f"Fichier de relevé PEA non trouvé : {releve_path}")

        # Parser fichiers d'évaluation PEA
        if evaluation_paths:
            for eval_file in evaluation_paths:
                if os.path.exists(eval_file):
                    logging.info(f"Début du parsing de l'évaluation PEA : {eval_file}")
                    positions = self._parse_pea_evaluation(eval_file)
                    all_portfolio_positions.extend(positions)
                else:
                    logging.warning(f"Fichier d'évaluation PEA non trouvé : {eval_file}")

        # Stocker toutes les positions pour insertion séparée
        self.pea_portfolio_positions = all_portfolio_positions
        self.pea_liquidity_balance = None # Initialiser la liquidité PEA
        self.pretup_liquidity_balance = None # Initialiser la liquidité PretUp

        return {
            "investments": investments,
            "cash_flows": cash_flows,
            "portfolio_positions": all_portfolio_positions,
            "liquidity_balances": [self.pea_liquidity_balance] if self.pea_liquidity_balance else []
        }

    

    def _extract_valuation_date(self, file_path: Optional[str] = None, text: Optional[str] = None) -> Optional[str]:
        """Extraire date de valorisation depuis nom fichier ou contenu"""
        
        logging.debug(f"Tentative d'extraction de la date de valorisation depuis le fichier : {file_path}")
        
        # Priorité 1 : Nom du fichier
        if file_path:
            filename = os.path.basename(file_path).lower()
            logging.debug(f"Nom du fichier pour l'extraction de la date : {filename}")
            
            # Patterns pour différents formats
            patterns = [
                r'(?:evaluation|portefeuille)_(\w+)_(\d{4})',
                r'positions_(\w+)_(\d{4})',
                r'pea_(\d{4})(\d{2})', # Nouveau pattern pour YYYYMM
                r'(\d{4})[_-](\d{2})[_-]',
                r'(\d{4})[_-](\w+)[_-]',
                r'pea_(\d{4})_(\w+)',
                r'(\w+)(\d{4})',
                r'(\w+)[_-]?(\d{2})'
            ]
            
            for pattern_idx, pattern in enumerate(patterns):
                match = re.search(pattern, filename)
                if match:
                    logging.debug(f"Pattern de date trouvé #{pattern_idx}: {match.groups()}")
                    
                    try:
                        group1, group2 = match.groups()
                        
                        # Cas YYYYMM (ex: pea_202312)
                        if pattern_idx == 2: # Index du nouveau pattern r'pea_(\d{4})(\d{2})'
                            annee = int(group1)
                            mois_num = int(group2)
                            if 1 <= mois_num <= 12:
                                if mois_num == 2:
                                    last_day = 29 if annee % 4 == 0 else 28
                                elif mois_num in [4, 6, 9, 11]:
                                    last_day = 30
                                else:
                                    last_day = 31
                                date_obj = datetime(annee, mois_num, last_day)
                                date_result = date_obj.strftime('%Y-%m-%d')
                                logging.info(f"Date de valorisation extraite du nom de fichier (YYYYMM) : {date_result}")
                                return date_result
                            else:
                                logging.warning(f"Mois invalide dans le nom de fichier (YYYYMM): {mois_num}")
                                continue
                        
                        # Cas mois_année
                        if group2.isdigit() and len(group2) == 4:
                            mois_nom = group1
                            annee = int(group2)
                            
                            # Mapping mois
                            mois_mapping = {
                                'janvier': 1, 'jan': 1,
                                'février': 2, 'fevrier': 2, 'fev': 2,
                                'mars': 3, 'mar': 3,
                                'avril': 4, 'avr': 4,
                                'mai': 5,
                                'juin': 6, 'jun': 6,
                                'juillet': 7, 'juil': 7,
                                'août': 8, 'aout': 8,
                                'septembre': 9, 'sept': 9, 'sep': 9,
                                'octobre': 10, 'oct': 10,
                                'novembre': 11, 'nov': 11,
                                'décembre': 12, 'decembre': 12, 'dec': 12
                            }
                            
                            mois_num = mois_mapping.get(mois_nom.lower())
                            if mois_num:
                                # Dernier jour du mois
                                if mois_num == 2:
                                    last_day = 29 if annee % 4 == 0 else 28
                                elif mois_num in [4, 6, 9, 11]:
                                    last_day = 30
                                else:
                                    last_day = 31
                                
                                date_obj = datetime(annee, mois_num, last_day)
                                date_result = date_obj.strftime('%Y-%m-%d')
                                logging.info(f"Date de valorisation extraite du nom de fichier : {date_result}")
                                return date_result
                    
                    except Exception:
                        logging.warning(f"Erreur lors de l'application du pattern de date #{pattern_idx}", exc_info=True)
                        continue
        
        # Priorité 2 : Contenu du fichier
        if text:
            logging.debug("Recherche de la date de valorisation dans le contenu du fichier.")
            date_patterns = [
                r'Le (\d{2}/\d{2}/\d{4})',
                r'le (\d{2}/\d{2}/\d{4})',
                r'Date\s*:\s*(\d{2}/\d{2}/\d{4})',
                r'Arrêté au (\d{2}/\d{2}/\d{4})'
            ]
            
            for pattern in date_patterns:
                match = re.search(pattern, text)
                if match:
                    date_str = match.group(1)
                    try:
                        date_obj = datetime.strptime(date_str, '%d/%m/%Y')
                        date_result = date_obj.strftime('%Y-%m-%d')
                        logging.info(f"Date de valorisation extraite du contenu du fichier : {date_result}")
                        return date_result
                    except:
                        continue
        
        # Fallback
        logging.warning("Aucune date de valorisation n'a pu être extraite, utilisation de la date actuelle.")
        return datetime.now().strftime('%Y-%m-%d')
        
    def _parse_multiligne_synchronized(self, multiline_row: List, pdf_path: str) -> List[Dict]:
        """ Parser multi-lignes vers portfolio_positions """
        positions = []
        
        try:
            # Extraire la date UNE FOIS avec debug
            valuation_date = self._extract_valuation_date(
                file_path=pdf_path
            )
            logging.info(f"Date de valorisation pour toutes les positions : {valuation_date}")
            
            # Diviser les colonnes
            designations = [d.strip() for d in str(multiline_row[0]).split('\n') if d.strip()]
            quantities = [q.strip() for q in str(multiline_row[1]).split('\n') if q.strip()]
            prices = [p.strip() for p in str(multiline_row[2]).split('\n') if p.strip()]
            values = [v.strip() for v in str(multiline_row[3]).split('\n') if v.strip()]
            percentages = [p.strip() for p in str(multiline_row[4]).split('\n') if p.strip()]
            
            logging.debug(f"Lengths: designations={len(designations)}, quantities={len(quantities)}, prices={len(prices)}, values={len(values)}, percentages={len(percentages)}")
            
            # Correction : Utiliser la longueur de la colonne des désignations comme référence
            # et accéder aux autres colonnes de manière sécurisée.
            for i in range(len(designations)):
                designation = designations[i]
                logging.debug(f"Processing designation: '{designation}' (index {i})")
                
                # Valeurs numériques (accès sécurisé)
                quantity_raw = quantities[i] if i < len(quantities) else '0'
                price_raw = prices[i] if i < len(prices) else '0'
                value_raw = values[i] if i < len(values) else '0'
                percentage_raw = percentages[i] if i < len(percentages) else '0'
                
                logging.debug(f"Raw values: Qty='{quantity_raw}', Price='{price_raw}', Value='{value_raw}', Pct='{percentage_raw}'")
                
                # Valeurs numériques
                quantity = clean_amount(quantity_raw)
                current_price = clean_amount(price_raw)
                market_value = clean_amount(value_raw)
                percentage = clean_amount(percentage_raw)
                designation_upper = designation.upper()
                
                logging.debug(f"Test de la ligne {i}: '{designation}'")
                
                # Vérifier ISIN d'abord
                isin_match = re.search(r'([A-Z]{2}[A-Z0-9]{10})', designation)
                
                if isin_match:
                    # Si ISIN trouvé, c'est une vraie position
                    isin = isin_match.group(1)
                    logging.debug(f"ISIN trouvé: {isin} → Position valide")
                    
                    # ✅ PAS de filtrage de section si ISIN présent
                    # TOTALENERGIES SE avec ISIN = position valide
                    
                else:
                    # Pas d'ISIN = vérifier si c'est une section/total
                    if any(keyword in designation_upper for keyword in [
                        'TOTAL PORTEFEUILLE', 'LIQUIDITES', 'SOLDE ESPECES',
                        'ACTIONS FRANCAISES', 'VALEUR EUROPE', 'DIVERS',
                        'SOUS-TOTAL', 'CUMUL'
                    ]):
                        logging.info(f"Ligne filtrée (section sans ISIN): {designation}")
                        continue
                    else:
                        logging.warning(f"Ligne filtrée (pas d'ISIN): {designation}")
                        continue
                
                # À ce stade : on a un ISIN valide
                
                # Nom actif nettoyé
                asset_name = designation.replace(isin, '').strip()
                asset_name = re.sub(r'^\d+\s*', '', asset_name).strip()
                asset_name = re.sub(r'\s*\d+,', '', asset_name).strip()
                
                # Valeurs numériques
                quantity = clean_amount(quantities[i]) if i < len(quantities) else 0
                current_price = clean_amount(prices[i]) if i < len(prices) else 0
                market_value = clean_amount(values[i]) if i < len(values) else 0
                percentage = clean_amount(percentages[i]) if i < len(percentages) else 0
                
                # Validation
                if quantity <= 0 and market_value <= 0:
                    logging.warning(f"Position {i} ignorée: quantité et valorisation nulles")
                    continue
                
                # Position avec date correcte
                position = {
                    'id': str(uuid.uuid4()),
                    'user_id': self.user_id,
                    'platform': 'PEA',
                    'isin': isin,
                    'asset_name': asset_name[:200],
                    'asset_class': self._classify_pea_asset(asset_name),
                    'quantity': quantity,
                    'current_price': current_price,
                    'market_value': market_value,
                    'portfolio_percentage': percentage,
                    'valuation_date': valuation_date,
                    'created_at': datetime.now().isoformat(),
                    'updated_at': datetime.now().isoformat()
                }
                
                positions.append(position)
                logging.debug(f"Position ajoutée: {isin} - {asset_name[:30]}... | {market_value}€ | {valuation_date}")
        
        except Exception:
            logging.exception("Erreur critique lors du parsing des positions multi-lignes.")
        
        return positions

    

    def _parse_pea_releve(self, pdf_path: str) -> List[Dict]:
        """ Parser relevé PEA """
        flux_tresorerie = []
        logging.info(f"Parsing du relevé PEA : {pdf_path}")
        
        self.current_file_path = pdf_path
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                text = page.extract_text()
                if not text:
                    continue
                
                lines = text.split('\n')
                
                for line in lines:
                    line = line.strip()
                    
                    date_match = re.match(r'^(\d{2}/\d{2}/\d{4})\s+(.+)', line)
                    
                    if date_match:
                        date_str = date_match.group(1)
                        rest_of_line = date_match.group(2).strip()
                        
                        date_transaction = standardize_date(date_str)
                        if not date_transaction:
                            continue
                        
                        transaction_data = self._parse_pea_transaction_line(rest_of_line)
                        
                        if transaction_data:
                            transaction_data.update({
                                'id': str(uuid.uuid4()),
                                'user_id': self.user_id,
                                'platform': 'PEA',
                                'transaction_date': date_transaction,
                                'status': 'completed',
                                'created_at': datetime.now().isoformat()
                            })
                            
                            flux_tresorerie.append(transaction_data)
        
        logging.info(f"Parsing du relevé PEA terminé : {len(flux_tresorerie)} transactions trouvées.")
        return flux_tresorerie

    def get_pea_portfolio_positions(self) -> List[Dict]:
        """Récupérer les positions de portefeuille PEA pour insertion séparée"""
        return getattr(self, 'pea_portfolio_positions', [])
    
    def get_pea_liquidity_balance(self) -> Optional[Dict]:
        """Récupérer le solde de liquidités PEA pour insertion séparée"""
        return getattr(self, 'pea_liquidity_balance', None)
    
    def get_pretup_liquidity_balance(self) -> Optional[Dict]:
        """Récupérer le solde de liquidités PretUp pour insertion séparée"""
        return getattr(self, 'pretup_liquidity_balance', None)
    
    def _parse_pea_transaction_line(self, line: str) -> Optional[Dict]:
        """ Extraction montants PEA """
        
        line_upper = line.upper()
        
        # Classification
        if 'COUPONS' in line_upper or 'DIVIDENDE' in line_upper:
            flow_type = 'dividend'
            flow_direction = 'in'
        elif 'ACH CPT' in line_upper or 'ACHAT' in line_upper:
            flow_type = 'purchase'
            flow_direction = 'out'
        elif 'VTE CPT' in line_upper or 'VENTE' in line_upper:
            flow_type = 'sale'
            flow_direction = 'in'
        elif 'TTF' in line_upper or 'TAXE' in line_upper:
            flow_type = 'fee'
            flow_direction = 'out'
        elif 'INVESTISSEMENT ESPECES' in line_upper:
            flow_type = 'deposit'
            flow_direction = 'in'
        elif 'REGULARISATION' in line_upper:
            flow_type = 'adjustment'
            flow_direction = 'in'
        else:
            flow_type = 'other'
            flow_direction = 'in'
        
        logging.debug(f"Ligne de transaction PEA : {line}")
    
        # Nettoyer et diviser
        cleaned = line.replace('\u00A0', ' ').replace('\t', ' ')
        words = cleaned.split()
        
        logging.debug(f"Derniers mots de la ligne : {words[-6:]}")
        
        transaction_amount = 0.0

        # ✅ ÉTAPE 1 : Montants avec espaces - CRITÈRES STRICTS
        for i in range(len(words) - 1, 0, -1):
            if i >= 1:
                word1 = words[i-1]  # Premier mot
                word2 = words[i]    # Deuxième mot
                
                logging.debug(f"Test de la combinaison de mots : '{word1}' + '{word2}'")
                
                # Critères TRÈS stricts pour éviter cours+montant
                # Conditions pour une combinaison valide de milliers :
                combine_ok = (
                    word1.isdigit() and                           # Premier = chiffres purs
                    len(word1) <= 3 and                          # Max 3 chiffres (1-999)
                    int(word1) >= 1 and                          # Au moins 1 (pas 0)
                    ',' in word2 and                             # Deuxième a une virgule
                    len(word2) >= 5 and                          # Au moins "000,X" (5 caractères)
                    word2.startswith(('0', '00', '000')) and     # Commence par des zéros (milliers)
                    word2.count(',') == 1                        # Une seule virgule
                )
                
                if combine_ok:
                    try:
                        combined = word1 + word2  # Ex: "2" + "000,00" = "2000,00"
                        amount = float(combined.replace(',', '.'))
                        
                        # Validation : montant raisonnable
                        if 100 <= amount <= 999999:  # Au moins 100€ pour les milliers
                            transaction_amount = amount
                            logging.debug(f"Montant (milliers) trouvé : {amount} à partir de '{word1}' + '{word2}'")
                            break
                        else:
                            logging.warning(f"Montant hors plage : {amount}")
                            
                    except Exception:
                        logging.error(f"Erreur lors de la combinaison des mots : '{word1}' et '{word2}'", exc_info=True)
                else:
                    logging.debug("Critères non respectés pour la combinaison de mots.")
        
        # ✅ ÉTAPE 2 : Montants simples avec virgule (priorité élevée)
        if transaction_amount == 0:
            logging.debug("Recherche de montants simples...")
            
            for word in reversed(words[-4:]):  # Les 4 derniers mots
                if (',' in word and \
                    not word.startswith(',') and \
                    not word.endswith(',') and\
                    len(word) >= 3):
                    
                    try:
                        # Nettoyer soigneusement
                        clean_word = ''.join(c for c in word if c.isdigit() or c == ',')
                        
                        if ',' in clean_word and clean_word.count(',') == 1:
                            amount = float(clean_word.replace(',', '.'))
                            
                            # Validation plus permissive pour les montants simples
                            if 0.01 <= amount <= 999999:
                                transaction_amount = amount
                                logging.debug(f"Montant (virgule) trouvé : {amount} à partir de '{word}'")
                                break
                    except Exception:
                        logging.warning(f"Erreur lors du parsing du montant simple : '{word}'", exc_info=True)
        
        # ✅ ÉTAPE 3 : Entiers (très restrictif)
        if transaction_amount == 0:
            logging.debug("Recherche d'entiers (restrictif)...")
            
            for word in reversed(words[-2:]):  # Seulement les 2 derniers
                if word.isdigit():
                    try:
                        amount = float(word)
                        # Très restrictif pour éviter les cours
                        if 100 <= amount <= 999999:  # Au moins 100€
                            transaction_amount = amount
                            logging.debug(f"Montant (entier) trouvé : {amount}")
                            break
                    except:
                        pass
        
        # ✅ ÉTAPE 4 : Fallback clean_amount (dernier recours)
        if transaction_amount == 0:
            logging.debug("Utilisation de la méthode de secours clean_amount...")
            
            # Tester seulement les dernières phrases courtes
            for length in [2, 1]:
                if len(words) >= length:
                    phrase = ' '.join(words[-length:])
                    try:
                        amount = clean_amount(phrase)
                        if amount > 0:
                            transaction_amount = amount
                            logging.debug(f"Montant (secours) trouvé : {amount} à partir de '{phrase}'")
                            break
                    except:
                        continue
        
        if transaction_amount <= 0:
            logging.warning(f"Échec de l'extraction du montant pour la ligne : {line}")
            return None
        
        # Calculer les frais de transaction
        fees = 0.0
        # Tentative d'extraction de la quantité et du prix pour le calcul des frais
        try:
            # Cette logique peut être fragile, à encapsuler dans un try-except
            qte_match = re.search(r'Qté\s*:\s*([\d,\.]+)', line)
            cours_match = re.search(r'Cours\s*:\s*([\d,\.]+)', line)
            if qte_match and cours_match:
                quantity = clean_amount(qte_match.group(1))
                unit_price = clean_amount(cours_match.group(1))
                if quantity > 0 and unit_price > 0:
                    theoretical_amount = quantity * unit_price
                    # Les frais sont la différence entre le montant total et la valeur théorique
                    calculated_fees = abs(transaction_amount - theoretical_amount)
                    if calculated_fees < (transaction_amount * 0.1): # Plausibilité : frais < 10% du montant
                        fees = calculated_fees
                        logging.info(f"Frais de transaction calculés : {fees:.2f}€")
        except Exception:
            logging.warning(f"Impossible de calculer les frais pour la ligne : {line}")

        # Description nettoyée
        description = line.split('Qté :')[0].strip() if 'Qté :' in line else line.strip()
        
        # Logique de calcul BRUT/NET basée sur la direction du flux
        if flow_direction == 'out': # Achat, Frais
            # Le montant total débité est le NET. Le BRUT est la valeur de l'actif.
            # net_amount = gross_amount + tax_amount
            net_amount = -transaction_amount # Négatif car sortie
            gross_amount = transaction_amount - fees
        else: # Vente, Dividende
            # Le montant total crédité est le NET. Le BRUT est la valeur avant déduction des frais/taxes.
            # net_amount = gross_amount - tax_amount
            net_amount = transaction_amount # Positif car entrée
            gross_amount = transaction_amount + fees

        logging.info(f"Transaction PEA extraite : {flow_type} | Brut: {gross_amount:.2f}€, Net: {net_amount:.2f}€, Taxe: {fees:.2f}€")
        
        return {
            'flow_type': flow_type,
            'flow_direction': flow_direction,
            'gross_amount': gross_amount,
            'net_amount': net_amount,
            'tax_amount': fees,
            'description': description
        }

    

    def _clean_french_amount(self, amount_str: str) -> float:
        """ Nettoyer montant français avec gestion des espaces """
        if not amount_str or pd.isna(amount_str):
            return 0.0
        
        try:
            # Nettoyer la chaîne
            cleaned = str(amount_str).strip()
            
            # Supprimer les caractères non numériques sauf espace, virgule, point
            cleaned = re.sub(r'[^\d\s,\.]', '', cleaned)
            
            # CORRECTION PRINCIPALE : Gestion format français avec espaces
            # Format: "1 088,41" ou "143,40" ou "1088.41"
            
            if ',' in cleaned:
                # Format français : "1 088,41" ou "143,40"
                if ' ' in cleaned:
                    # Format avec espaces : "1 088,41" → "1088,41" → "1088.41"
                    cleaned = cleaned.replace(' ', '')
                # Remplacer virgule par point : "1088,41" → "1088.41"
                cleaned = cleaned.replace(',', '.')
            
            # Convertir en float
            return float(cleaned) if cleaned else 0.0
            
        except Exception:
            logging.warning(f"Erreur lors du nettoyage du montant '{amount_str}'", exc_info=True)
            return 0.0

    

    

    

    def _extract_pea_description(self, line: str) -> str:
        """Extraire description nettoyée"""
        # Enlever les infos techniques
        cleaned = re.sub(r'Qté\s*:\s*[\d,\.\s]+', '', line)
        cleaned = re.sub(r'Cours\s*:\s*[\d,\.\s]+', '', cleaned)
        
        # Enlever les montants en fin
        cleaned = re.sub(r'[\d\s,\.]+\\', '', cleaned)
        
        # Nettoyer espaces
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned if cleaned else "Transaction PEA"

    def _parse_pea_evaluation(self, pdf_path: str) -> List[Dict]:
        """Debug complet de la date + stockage correct"""
        positions = []
        
        logging.info(f"Parsing de l'évaluation PEA : {pdf_path}")
        
        # Test direct extraction date
        test_date = self._extract_valuation_date(file_path=pdf_path)
        logging.debug(f"Date de valorisation extraite pour le test : {test_date}")
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                logging.debug(f"Parsing de la page {page_num + 1}...")
                
                text = page.extract_text() # Définir text ici
                if not text:
                    continue

                tables = page.extract_tables()
                
                if tables:
                    for table_idx, table in enumerate(tables):
                        if table and len(table) > 1:
                            # Vérifier si c'est un tableau de positions
                            has_isin = any(re.search(r'[A-Z]{2}\d{10}', str(cell)) \
                                        for row in table[:3] for cell in row if cell)
                            
                            if has_isin:
                                logging.info(f"Tableau de positions détecté sur la page {page_num + 1}")
                                
                                # ✅ Vérifier que current_file_path est encore là
                                logging.debug(f"Avant parsing, chemin du fichier courant : {pdf_path}")
                                
                                extracted_positions = self._parse_pea_positions_to_portfolio(table, pdf_path)
                                positions.extend(extracted_positions)

                # Extraire la liquidité de la page actuelle
                liquidity_amount = None
                
                # Trouver la position des mots-clés
                liquidites_idx = text.upper().find('LIQUIDITES')
                solde_especes_idx = text.upper().find('SOLDE ESPECES')

                search_start_idx = -1
                if liquidites_idx != -1 and (solde_especes_idx == -1 or liquidites_idx < solde_especes_idx):
                    search_start_idx = liquidites_idx + len('LIQUIDITES')
                elif solde_especes_idx != -1:
                    search_start_idx = solde_especes_idx + len('SOLDE ESPECES')

                if search_start_idx != -1:
                    # Rechercher un montant après le mot-clé
                    # Chercher un motif comme "1 234,56" ou "123.45"
                    amount_pattern = r'([\d\s,\.]+)(?:\s*EUR)?' # EUR est optionnel
                    
                    # Rechercher dans le texte *après* le mot-clé
                    amount_match = re.search(amount_pattern, text[search_start_idx:])
                    if amount_match:
                        raw_amount_str = amount_match.group(1)
                        logging.debug(f"PEA Liquidity: Raw amount string extracted: '{raw_amount_str}'")
                        liquidity_amount = clean_amount(raw_amount_str)
                        logging.info(f"Liquidité PEA trouvée près du mot-clé: {liquidity_amount} EUR")

                if liquidity_amount is not None:
                    self.pea_liquidity_balance = {
                        'user_id': self.user_id,
                        'platform': 'PEA',
                        'balance_date': test_date,
                        'amount': liquidity_amount
                    }
                    logging.info(f"Liquidité PEA extraite : {liquidity_amount} EUR à la date {test_date}")
                else:
                    logging.warning("Aucune liquidité PEA trouvée dans le PDF d'évaluation.")

        logging.info(f"Parsing de l'évaluation PEA terminé : {len(positions)} positions trouvées.")
        return positions

    def _parse_pea_positions_to_portfolio(self, table: List[List], pdf_path: str) -> List[Dict]:
        """Parser positions PEA"""
        positions = []
        
        if not table or len(table) < 2:
            return positions
        
        data_rows = table[1:]
        
        if data_rows and len(data_rows[0]) >= 4:
            first_row = data_rows[0]
            has_multiline = any('\n' in str(cell) for cell in first_row if cell)
            
            if has_multiline:
                logging.info("Données multi-lignes détectées, utilisation du parser synchronisé.")
                positions = self._parse_multiligne_synchronized(first_row, pdf_path)
            else:
                logging.info("Données normales détectées, utilisation du parser normal.")
                positions = self._parse_normal_to_portfolio(data_rows)
        
        return positions

    def _is_section_header(self, designation: str) -> bool:
        """
        Détecter si une ligne est un en-tête de section ou un total.
        RÈGLE CLEF : Si ça contient un ISIN, ce n'est PAS une section !
        """
        logging.debug(f"_is_section_header: Input designation: '{designation}'")
        designation_clean = designation.strip().upper()
        logging.debug(f"_is_section_header: Cleaned designation: '{designation_clean}'")
        
        # RÈGLE 1 : Si la ligne contient un ISIN, ce n'est PAS une section
        isin_match = re.search(r'[A-Z]{2}[A-Z0-9]{10}', designation_clean)
        if isin_match:
            logging.debug(f"_is_section_header: ISIN found ({isin_match.group(0)}), returning False.")
            return False
        
        # RÈGLE 2 : Sections exactes ou très spécifiques
        sections_exact = [
            'ACTIONS FRANCAISES',
            'VALEUR EUROPE', 
            'ACTIONS ETRANGERES',
            'DIVERS',
            'LIQUIDITES',
            'OBLIGATIONS',
            'SOLDE ESPECES'
        ]
        
        for section in sections_exact:
            if designation_clean == section or designation_clean.startswith(section + ' '):
                logging.debug(f"_is_section_header: Matched exact section '{section}', returning True.")
                return True
        
        # RÈGLE 3 : Lignes de totalisation (sans ISIN)
        total_keywords = ['TOTAL PORTEFEUILLE', 'SOUS-TOTAL', 'CUMUL', 'TOTAL']
        if any(keyword in designation_clean for keyword in total_keywords):
            logging.debug(f"_is_section_header: Matched total keyword, returning True.")
            return True
        
        logging.debug(f"_is_section_header: No match, returning False.")
        return False

    def _clean_pea_designation(self, designation: str) -> str:
        """ Nettoyer la désignation PEA
        Supprime le code "025" à la fin et autres codes internes
        """
        cleaned = designation.strip()
        
        # CORRECTION : Supprimer le code "025" à la fin
        cleaned = re.sub(r'\s+025\s*,', '', cleaned)
        
        # Supprimer autres codes potentiels (3 chiffres à la fin)
        cleaned = re.sub(r'\s+\d{3}\s*,', '', cleaned)
        
        # Nettoyer espaces multiples
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned

    def _classify_pea_asset(self, asset_name: str) -> str:
        """Classifier actif PEA"""
        name_upper = str(asset_name).upper()
        
        if any(keyword in name_upper for keyword in ['ETF', 'TRACKER', 'INDEX']):
            return 'etf'
        elif any(keyword in name_upper for keyword in ['EURO', 'FONDS']):
            return 'fund'
        elif any(keyword in name_upper for keyword in ['BOND', 'OBLIGATION']):
            return 'bond'
        else:
            return 'stock'

    # ===== MÉTHODES UTILITAIRES =====
    def _parse_pretup_date(self, date_str: str) -> str:
        """Parser dates PretUp format spécial"""
        if pd.isna(date_str) or not date_str:
            return None
        
        try:
            if 'à' in str(date_str):
                date_part = str(date_str).split(' à')[0]
            else:
                date_part = str(date_str)
            return standardize_date(date_part)
        except:
            return None
    
    def _map_bienpreter_status(self, status: str) -> str:
        """Mapper statut BienPrêter"""
        status_lower = status.lower()
        if 'en cours' in status_lower:
            return 'active'
        elif 'terminé' in status_lower or 'remboursé' in status_lower or 'clôturé' in status_lower:
            return 'completed'
        elif 'retard' in status_lower:
            return 'delayed'
        else:
            return 'active'
    
    def _map_homunity_status(self, status: str) -> str:
        """Mapper statut Homunity"""
        status_lower = status.lower() if status else ''
        
        if 'en attente' in status_lower or 'en cours' in status_lower:
            return 'active'
        elif 'terminé' in status_lower or 'remboursé' in status_lower:
            return 'completed'
        else:
            return 'active'
    
    def _convert_pea_positions_to_investments(self, positions: List[Dict]) -> List[Dict]:
        """Convertir positions PEA en investissements"""
        investments = []
        
        for position in positions:
            investment = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'PEA',
                'platform_id': position.get('isin', ''),
                'investment_type': 'stocks',
                'asset_class': position.get('asset_class', 'stock'),
                
                'project_name': position.get('asset_name', ''),
                'company_name': position.get('asset_name', ''),
                
                'invested_amount': position.get('market_value', 0),  # Approximation
                'current_value': position.get('market_value', 0),
                
                'investment_date': '2020-01-01',  # À affiner
                'status': 'active',
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investments.append(investment)
        
        return investments