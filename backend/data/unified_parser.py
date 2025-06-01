# ===== backend/data/unified_parser.py - PARSER UNIFIÉ EXPERT =====
import pandas as pd
import pdfplumber
from typing import List, Dict, Tuple, Optional
from datetime import datetime
import uuid
import re
import os
from backend.utils.file_helpers import standardize_date, clean_amount, clean_string_operation, safe_get

class UnifiedPortfolioParser:
    """Parser unifié pour toutes les plateformes d'investissement"""
    
    def __init__(self, user_id: str):
        self.user_id = user_id
        self.platform_methods = {
            'lpb': self._parse_lpb,
            'pretup': self._parse_pretup, 
            'bienpreter': self._parse_bienpreter,
            'homunity': self._parse_homunity,
            'assurance_vie': self._parse_assurance_vie,
            'pea': self._parse_pea
        }
    
    def parse_platform(self, file_path: str, platform: str) -> Tuple[List[Dict], List[Dict]]:
        """Point d'entrée principal pour parser une plateforme"""
        print(f"🔍 Parsing {platform.upper()} : {file_path}")
        
        if platform.lower() not in self.platform_methods:
            raise ValueError(f"Plateforme non supportée : {platform}")
        
        try:
            return self.platform_methods[platform.lower()](file_path)
        except Exception as e:
            print(f"❌ Erreur parsing {platform}: {e}")
            import traceback
            traceback.print_exc()
            return [], []

    # ===== LPB (LA PREMIÈRE BRIQUE) =====
    def _parse_lpb(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Parser LPB"""
        
        # Parser projets
        projects_df = pd.read_excel(file_path, sheet_name='Projets')
        investissements = self._parse_lpb_projects(projects_df)
        
        # Parser relevé avec gestion taxes
        account_df = pd.read_excel(file_path, sheet_name='Relevé compte')
        flux_tresorerie = self._parse_lpb_account(account_df)
        
        return investissements, flux_tresorerie
    
    def _parse_lpb_projects(self, df: pd.DataFrame) -> List[Dict]:
        """Parser projets LPB"""
        investissements = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 1)) or safe_get(row, 1) == "Nom du projet":
                continue
            
            # Dates critiques pour TRI
            date_collecte = standardize_date(safe_get(row, 0))  # investment_date
            date_signature = standardize_date(safe_get(row, 5))  # signature_date
            date_remb_max = standardize_date(safe_get(row, 7))   # expected_end_date
            date_remb_effective = standardize_date(safe_get(row, 8))  # actual_end_date
            
            # Détection retard
            is_delayed = False
            if date_remb_max and date_remb_effective:
                if date_remb_effective > date_remb_max:
                    is_delayed = True
            elif date_remb_max and not date_remb_effective:
                if datetime.now().strftime('%Y-%m-%d') > date_remb_max:
                    is_delayed = True
            
            # Statut
            statut_raw = safe_get(row, 2, '')
            if 'Remboursée' in statut_raw:
                status = 'completed'
            elif 'Finalisée' in statut_raw:
                status = 'delayed' if is_delayed else 'active'
            else:
                status = 'active'
            
            # Duration en mois
            if date_collecte and date_remb_max:
                start = pd.to_datetime(date_collecte)
                end = pd.to_datetime(date_remb_max)
                months = (end.year - start.year) * 12 + (end.month - start.month)
                if end.day < start.day:
                    months -= 1
                duration_months = max(0, months)
            else:
                duration_months = None
            
            investissement = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'La Première Brique',
                'platform_id': f"LPB_{idx}",
                'investment_type': 'crowdfunding',
                'asset_class': 'real_estate',
                
                'project_name': safe_get(row, 1, ''),
                'company_name': safe_get(row, 1, ''),
                
                'invested_amount': clean_amount(safe_get(row, 3, 0)),
                'annual_rate': safe_get(row, 4, 0),
                'duration_months': duration_months,
                'capital_repaid': clean_amount(safe_get(row, 3, 0)) - clean_amount(safe_get(row, 9, 0)),  # Capital remboursé
                'remaining_capital': clean_amount(safe_get(row, 9, 0)) if len(row) > 9 else None,  # Capital restant dû
                
                'investment_date': date_collecte,      # Pour TRI
                'signature_date': date_signature,      # Pour suivi admin
                'expected_end_date': date_remb_max,
                'actual_end_date': date_remb_effective,
                
                'status': status,
                'is_delayed': is_delayed,
                'is_short_term': duration_months and duration_months < 6,
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investissements.append(investissement)
        
        return investissements
    
    def _parse_lpb_account(self, df: pd.DataFrame) -> List[Dict]:
        """Parser relevé LPB avec gestion taxes CSG/CRDS + IR"""
        flux_tresorerie = []
        
        # Pré-processing pour identifier les groupes de taxes
        df_with_index = df.reset_index()
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Nature de la transaction":
                continue
            
            nature = safe_get(row, 0, '')
            montant = clean_amount(safe_get(row, 3, 0))
            date_transaction = standardize_date(safe_get(row, 5))
            
            if not date_transaction:
                continue
            
            # Classification et gestion taxes
            flow_type, flow_direction = self._classify_lpb_transaction(nature)
            
            # Gestion spéciale pour remboursements avec taxes
            tax_amount = 0.0
            if 'Remboursement mensualité' in nature:
                # Chercher les 2 lignes précédentes pour taxes
                tax_amount = self._extract_lpb_taxes(df, idx)
            
            # Calcul net
            if flow_direction == 'in' and tax_amount > 0:
                net_amount = montant - tax_amount
                gross_amount = montant
            else:
                net_amount = montant if flow_direction == 'in' else -abs(montant)
                gross_amount = abs(montant)
            
            flux = {
                'id': str(uuid.uuid4()),
                'investment_id': None,  # À lier plus tard
                'user_id': self.user_id,
                'platform': 'La Première Brique',
                
                'flow_type': flow_type,
                'flow_direction': flow_direction,
                
                'gross_amount': gross_amount,
                'net_amount': net_amount,
                'tax_amount': tax_amount,
                
                'transaction_date': date_transaction,
                'status': 'completed' if safe_get(row, 4) == 'Réussi' else 'failed',
                
                'description': nature,
                'payment_method': safe_get(row, 1, ''),
                
                'created_at': datetime.now().isoformat()
            }
            
            flux_tresorerie.append(flux)
        
        return flux_tresorerie
    
    def _extract_lpb_taxes(self, df: pd.DataFrame, current_idx: int) -> float:
        """Extraire les taxes des 2 lignes précédentes"""
        tax_amount = 0.0
        
        # Vérifier les 2 lignes précédentes
        for i in range(max(0, current_idx - 2), current_idx):
            if i < len(df):
                nature_tax = safe_get(df.iloc[i], 0, '').lower()
                if any(keyword in nature_tax for keyword in ['csg', 'crds', 'ir', 'prélèvement']):
                    tax_amount += abs(clean_amount(safe_get(df.iloc[i], 3, 0)))
        
        return tax_amount
    
    def _classify_lpb_transaction(self, nature: str) -> Tuple[str, str]:
        """Classification LPB corrigée"""
        nature_lower = nature.lower()
        
        if 'crédit du compte' in nature_lower:
            return 'deposit', 'in'  # Argent frais injecté
        elif 'souscription' in nature_lower:
            return 'investment', 'out'  # Investissement projet
        elif 'retrait de l\'épargne' in nature_lower:
            return 'withdrawal', 'out'  # Récupération fonds
        elif 'rémunération' in nature_lower or 'code cadeau' in nature_lower:
            return 'interest', 'in'  # Bonus/intérêts
        elif 'remboursement mensualité' in nature_lower:
            return 'repayment', 'in'  # Remboursement
        elif 'annulation' in nature_lower:
            return 'cancellation', 'in'  # Annulation
        else:
            return 'other', 'in'

    # ===== BIENPRÊTER =====
    def _parse_bienpreter(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Parser BienPrêter avec toutes les infos fiscales"""
        
        projects_df = pd.read_excel(file_path, sheet_name='Projets')
        account_df = pd.read_excel(file_path, sheet_name='Relevé compte')
        
        investissements = self._parse_bienpreter_projects(projects_df)
        flux_tresorerie = self._parse_bienpreter_account(account_df, projects_df)
        
        return investissements, flux_tresorerie
    
    def _parse_bienpreter_projects(self, df: pd.DataFrame) -> List[Dict]:
        """Parser projets BienPrêter"""
        investissements = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 1)) or safe_get(row, 1) == "Projet":
                continue
            
            date_financement = standardize_date(safe_get(row, 6))
            if not date_financement:
                date_financement = "2023-01-01"
            
            investissement = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'BienPrêter',
                'platform_id': safe_get(row, 0, ''),
                'investment_type': 'crowdfunding',
                'asset_class': 'real_estate',
                
                'project_name': safe_get(row, 1, ''),
                'company_name': safe_get(row, 2, ''),
                
                'invested_amount': clean_amount(safe_get(row, 3, 0)),
                'annual_rate': safe_get(row, 4, 0),
                'duration_months': safe_get(row, 5, 0),
                'monthly_payment': clean_amount(safe_get(row, 10, 0)) if len(row) > 10 else None,  # Mensualité
                
                'investment_date': date_financement,
                'expected_end_date': standardize_date(safe_get(row, 7)),
                
                'status': self._map_bienpreter_status(safe_get(row, 10, '')),
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investissements.append(investissement)
        
        return investissements
    
    def _parse_bienpreter_account(self, df: pd.DataFrame, projects_df: pd.DataFrame) -> List[Dict]:
        """Parser relevé BienPrêter avec calcul taxes"""
        flux_tresorerie = []
        
        # Créer un mapping projet_id -> mensualité pour calcul brut
        project_monthly_map = {}
        for _, row in projects_df.iterrows():
            project_id = safe_get(row, 0, '')
            monthly_payment = clean_amount(safe_get(row, 10, 0)) if len(row) > 10 else 0
            if project_id and monthly_payment > 0:
                project_monthly_map[project_id] = monthly_payment
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Opération":
                continue
            
            operation = safe_get(row, 0, '')
            date_transaction = standardize_date(safe_get(row, 3))
            
            if not date_transaction:
                continue
            
            # Lecture des montants depuis les colonnes appropriées
            if 'remboursement' in operation.lower():
                # Remboursement : brut/net/taxes disponibles
                gross_amount = clean_amount(safe_get(row, 7, 0))  # Intérêts remb
                tax_amount = clean_amount(safe_get(row, 8, 0))    # Prélèvements
                net_amount = clean_amount(safe_get(row, 4, 0))    # Montant net
                
                flow_type = 'repayment'
                flow_direction = 'in'
                
                # Validation : net_amount = gross_amount - tax_amount
                if abs(net_amount - (gross_amount - tax_amount)) > 0.01:
                    print(f"⚠️  Incohérence fiscale BienPrêter ligne {idx}")
            
            elif 'bonus' in operation.lower():
                # Bonus sans taxes
                net_amount = clean_amount(safe_get(row, 4, 0))
                gross_amount = net_amount
                tax_amount = 0.0
                flow_type = 'interest'
                flow_direction = 'in'
            
            elif 'dépôt' in operation.lower():
                # Argent frais
                gross_amount = clean_amount(safe_get(row, 4, 0))
                net_amount = gross_amount
                tax_amount = 0.0
                flow_type = 'deposit'
                flow_direction = 'in'
            
            elif 'offre acceptée' in operation.lower():
                # Investissement
                gross_amount = clean_amount(safe_get(row, 4, 0))
                net_amount = gross_amount
                tax_amount = 0.0
                flow_type = 'investment'
                flow_direction = 'out'
            
            else:
                continue
            
            flux = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'BienPrêter',
                
                'flow_type': flow_type,
                'flow_direction': flow_direction,
                
                'gross_amount': gross_amount,
                'net_amount': net_amount,
                'tax_amount': tax_amount,
                
                'transaction_date': date_transaction,
                'status': 'completed',
                
                'description': f"{operation} - {safe_get(row, 2, '')}",
                
                'created_at': datetime.now().isoformat()
            }
            
            flux_tresorerie.append(flux)
        
        return flux_tresorerie

    # ===== HOMUNITY =====
    def _parse_homunity(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Parser Homunity avec distinction dates souscription/investissement"""
        
        projects_df = pd.read_excel(file_path, sheet_name='Projets')
        account_df = pd.read_excel(file_path, sheet_name='Relevé compte')
        
        investissements = self._parse_homunity_projects(projects_df)
        flux_tresorerie = self._parse_homunity_account(account_df)
        
        return investissements, flux_tresorerie
    
    def _parse_homunity_projects(self, df: pd.DataFrame) -> List[Dict]:
        """Parser projets Homunity"""
        investissements = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Date de souscription":
                continue
            
            date_souscription = standardize_date(safe_get(row, 0))  # signature_date
            # investment_date sera récupéré du relevé compte
            
            investissement = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'Homunity',
                'platform_id': f"HOM_{idx}",
                'investment_type': 'crowdfunding',
                'asset_class': 'real_estate',
                
                'project_name': safe_get(row, 2, ''),
                'company_name': safe_get(row, 1, ''),
                
                'invested_amount': clean_amount(safe_get(row, 3, 0)),
                'annual_rate': clean_amount(safe_get(row, 5, 0)),
                
                'signature_date': date_souscription,    # Date souscription
                'investment_date': None,                 # À récupérer du relevé
                'expected_end_date': standardize_date(safe_get(row, 4)),
                
                'status': self._map_homunity_status(safe_get(row, 6, '')),
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investissements.append(investissement)
        
        return investissements
    
    def _parse_homunity_account(self, df: pd.DataFrame) -> List[Dict]:
        """Parser relevé Homunity avec calcul brut = net + impôts (17,2%)"""
        flux_tresorerie = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Type de mouvement":
                continue
            
            type_mouvement = safe_get(row, 0, '')
            date_transaction = standardize_date(safe_get(row, 1))
            message = safe_get(row, 4, '')
            
            if not date_transaction:
                continue
            
            # Parsing montant et direction
            montant_str = safe_get(row, 3, '')
            direction = 'in' if '+' in str(montant_str) else 'out'
            montant_abs = clean_amount(str(montant_str).replace('+', '').replace('-', '').strip())
            
            # Classification
            if 'approvisionnement' in type_mouvement.lower():
                flow_type = 'deposit'
                gross_amount = montant_abs
                net_amount = -montant_abs  # Sortie argent frais
                tax_amount = 0.0
            
            elif 'transfert' in type_mouvement.lower():
                # Analyser le message pour distinguer investissement vs remboursement
                if any(keyword in message.lower() for keyword in ['investissement', 'souscription']):
                    flow_type = 'investment'
                    gross_amount = montant_abs
                    net_amount = -montant_abs  # Sortie
                    tax_amount = 0.0
                else:
                    # Remboursement avec calcul fiscal
                    flow_type = 'repayment'
                    # Note : Vous avez mentionné colonnes "Intérêt net" et "impots"
                    # À adapter selon la structure exacte de votre fichier
                    net_amount = montant_abs
                    tax_amount = 0.0  # À calculer si colonnes disponibles
                    gross_amount = net_amount + tax_amount
            
            else:
                flow_type = 'other'
                gross_amount = montant_abs
                net_amount = montant_abs if direction == 'in' else -montant_abs
                tax_amount = 0.0
            
            flux = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'Homunity',
                
                'flow_type': flow_type,
                'flow_direction': direction,
                
                'gross_amount': gross_amount,
                'net_amount': net_amount,
                'tax_amount': tax_amount,
                
                'transaction_date': date_transaction,
                'status': 'completed' if safe_get(row, 2) == 'Succès' else 'failed',
                
                'description': message,
                
                'created_at': datetime.now().isoformat()
            }
            
            flux_tresorerie.append(flux)
        
        return flux_tresorerie

    # ===== PRETUP =====
    def _parse_pretup(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Parser PretUp avec gestion complète échéances"""
        
        # Parser les différents onglets de projets
        investissements = []
        investissements.extend(self._parse_pretup_sheet(file_path, 'Projet Sains - Offres', 'active'))
        investissements.extend(self._parse_pretup_sheet(file_path, 'Procédures - Offres', 'in_procedure'))
        investissements.extend(self._parse_pretup_sheet(file_path, 'Perdu - Offres', 'defaulted'))
        
        # Parser relevé avec calcul taxes (CSG+CRDS + PF)
        flux_tresorerie = self._parse_pretup_account(file_path)
        
        return investissements, flux_tresorerie
    
    def _parse_pretup_sheet(self, file_path: str, sheet_name: str, status: str) -> List[Dict]:
        """Parser un onglet de projets PretUp"""
        try:
            df = pd.read_excel(file_path, sheet_name=sheet_name)
        except:
            return []
        
        investissements = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) in ["Nom du Projet", "TOTAUX :"]:
                continue
            
            # Montants offre et capital restant
            montant_offre = clean_amount(safe_get(row, 3, 0))
            capital_restant = clean_amount(safe_get(row, 4, 0))
            
            investissement = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'PretUp',
                'platform_id': str(safe_get(row, 2, '')),
                'investment_type': 'crowdfunding',
                'asset_class': 'real_estate',
                
                'project_name': safe_get(row, 0, ''),
                'company_name': safe_get(row, 1, ''),
                
                'invested_amount': montant_offre,
                'remaining_capital': capital_restant,
                'capital_repaid': montant_offre - capital_restant,
                
                'status': status,
                'investment_date': "2022-08-01",  # À affiner avec relevé
                
                'created_at': datetime.now().isoformat(),
                'updated_at': datetime.now().isoformat()
            }
            
            investissements.append(investissement)
        
        return investissements
    
    def _parse_pretup_account(self, file_path: str) -> List[Dict]:
        """Parser relevé PretUp avec gestion taxes complète"""
        try:
            df = pd.read_excel(file_path, sheet_name='Relevé compte')
        except:
            return []
        
        flux_tresorerie = []
        
        for idx, row in df.iterrows():
            if pd.isna(safe_get(row, 0)) or safe_get(row, 0) == "Date":
                continue
            
            # Parser date PretUp
            date_transaction = self._parse_pretup_date(safe_get(row, 0, ''))
            if not date_transaction:
                continue
            
            type_transaction = safe_get(row, 1, '')
            statut = safe_get(row, 6, '')
            
            # Ignorer les transactions non abouties
            if 'Non abouti' in statut:
                continue
            
            # Parsing montants
            debit = clean_amount(safe_get(row, 4, 0))
            credit = clean_amount(safe_get(row, 5, 0))
            
            # Classification et calcul fiscal
            if 'Echéance' in type_transaction:
                # Échéance avec taxes flat tax 30%
                gross_amount = clean_amount(safe_get(row, 7, 0))  # Montant échéance
                net_amount = clean_amount(safe_get(row, 13, 0))   # Intérêts net
                
                # Taxes = CSG/CRDS + PF
                csg_crds = clean_amount(safe_get(row, 11, 0))
                pf = clean_amount(safe_get(row, 12, 0))
                tax_amount = csg_crds + pf
                
                flow_type = 'repayment'
                flow_direction = 'in'
                final_amount = net_amount
            
            elif 'Remboursement anticipé' in type_transaction:
                # Remboursement sans taxes
                gross_amount = credit
                net_amount = credit
                tax_amount = 0.0
                flow_type = 'repayment'
                flow_direction = 'in'
                final_amount = net_amount
            
            elif 'Alimentation' in type_transaction:
                # Argent frais
                gross_amount = credit
                net_amount = -credit  # Sortie
                tax_amount = 0.0
                flow_type = 'deposit'
                flow_direction = 'in'
                final_amount = net_amount
            
            elif 'Offre' in type_transaction:
                # Investissement
                gross_amount = debit
                net_amount = -debit  # Sortie
                tax_amount = 0.0
                flow_type = 'investment'
                flow_direction = 'out'
                final_amount = net_amount
            
            else:
                continue
            
            flux = {
                'id': str(uuid.uuid4()),
                'user_id': self.user_id,
                'platform': 'PretUp',
                
                'flow_type': flow_type,
                'flow_direction': flow_direction,
                
                'gross_amount': gross_amount,
                'net_amount': final_amount,
                'tax_amount': tax_amount,
                
                'capital_amount': clean_amount(safe_get(row, 9, 0)),
                'interest_amount': clean_amount(safe_get(row, 13, 0)),
                
                'transaction_date': date_transaction,
                'status': 'completed',
                
                'description': safe_get(row, 3, ''),
                
                'created_at': datetime.now().isoformat()
            }
            
            flux_tresorerie.append(flux)
        
        return flux_tresorerie

    # ===== ASSURANCE VIE =====
    def _parse_assurance_vie(self, file_path: str) -> Tuple[List[Dict], List[Dict]]:
        """Parser Assurance Vie ultra-robuste contre les erreurs de type"""
        
        try:
            df = pd.read_excel(file_path, sheet_name='Relevé compte')
        except Exception as e:
            print(f"❌ Impossible de lire l'assurance vie: {e}")
            
            # Essayer d'autres noms d'onglets possibles
            try:
                df = pd.read_excel(file_path, sheet_name=0)  # Premier onglet
                print("✅ Utilisation du premier onglet comme fallback")
            except:
                print("❌ Impossible de lire le fichier d'assurance vie")
                return [], []
        
        flux_tresorerie = []
        
        print(f"📊 Lecture assurance vie: {len(df)} lignes trouvées")
        
        for idx, row in df.iterrows():
            try:
                # Vérification robuste des lignes vides/headers
                date_raw = safe_get(row, 0)
                if pd.isna(date_raw) or date_raw in ["Date", "Type", None]:
                    continue
                
                # CORRECTION PRINCIPALE : Gestion robuste du type d'opération
                type_operation_raw = safe_get(row, 1, '')
                type_operation = str(type_operation_raw).lower() if type_operation_raw is not None else ''
                
                # Debug pour comprendre le contenu
                if idx < 3:  # Afficher les 3 premières lignes pour debug
                    print(f"  Ligne {idx}: Date={date_raw}, Type={type_operation_raw} -> '{type_operation}'")
                
                date_transaction = standardize_date(date_raw)
                montant = clean_amount(safe_get(row, 2, 0))
                
                if not date_transaction:
                    print(f"  ⚠️  Ligne {idx}: Date invalide '{date_raw}'")
                    continue
                    
                if montant == 0:
                    print(f"  ⚠️  Ligne {idx}: Montant nul")
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
                    net_amount = -abs(montant)
                    
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
                    'net_amount': net_amount,
                    'tax_amount': 0.0,
                    
                    'transaction_date': date_transaction,
                    'status': 'completed',
                    
                    'description': f"AV - {clean_string_operation(type_operation_raw, 'Transaction')}",
                    
                    'created_at': datetime.now().isoformat()
                }
                
                flux_tresorerie.append(flux)
                
            except Exception as e:
                print(f"  ❌ Erreur ligne {idx}: {e}")
                continue
        
        print(f"✅ Assurance Vie parsed: {len(flux_tresorerie)} flux extraits")
        
        return [], flux_tresorerie

    # ===== PEA =====
    def _parse_pea(self, releve_path: str = None, evaluation_path: str = None) -> Tuple[List[Dict], List[Dict]]:
        """Parser PEA avec portfolio_positions pour l'évaluation"""
        
        investments = []  # Vide maintenant - pas utilisé pour les positions
        cash_flows = []
        
        # Parser relevé (transactions → cash_flows)
        if releve_path and os.path.exists(releve_path):
            print("📄 Parsing relevé PEA vers cash_flows...")
            cash_flows = self._parse_pea_releve(releve_path)
        
        # Parser évaluation (positions → portfolio_positions)
        if evaluation_path and os.path.exists(evaluation_path):
            print("📊 Parsing évaluation PEA vers portfolio_positions...")
            portfolio_positions = self._parse_pea_evaluation(evaluation_path)
            
            # Stocker dans une variable de classe pour insertion séparée
            self.pea_portfolio_positions = portfolio_positions
        
        return investments, cash_flows

    def _parse_pea_releve(self, pdf_path: str) -> List[Dict]:
        """Parser relevé PEA avec extraction intelligente CORRIGÉE"""
        flux_tresorerie = []
        
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                text = page.extract_text()
                if not text:
                    continue
                
                lines = text.split('\n')
                
                for line in lines:
                    if re.match(r'^\d{2}/\d{2}/\d{4}', line):
                        transaction = self._parse_pea_transaction_line(line)
                        if transaction:
                            flux_tresorerie.append(transaction)
        
        return flux_tresorerie
    
    def get_pea_portfolio_positions(self) -> List[Dict]:
        """Récupérer les positions de portefeuille PEA pour insertion séparée"""
        return getattr(self, 'pea_portfolio_positions', [])
    
    def _parse_pea_transaction_line(self, line: str) -> Optional[Dict]:
        """
        CORRIGÉ : Parser transaction PEA avec gestion améliorée des montants français
        """
        
        # Extraire date
        date_match = re.match(r'^(\d{2}/\d{2}/\d{4})', line)
        if not date_match:
            return None
        
        date_transaction = standardize_date(date_match.group(1))
        line_upper = line.upper()
        
        # Classification des opérations CORRIGÉE
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
        
        # EXTRACTION CORRIGÉE des montants français
        transaction_amount = self._extract_pea_transaction_amount_french(line, flow_type)
        
        # Description nettoyée
        description = self._extract_pea_description(line)
        
        # Montant net final pour le flux
        net_amount = transaction_amount if flow_direction == 'in' else -transaction_amount
        
        return {
            'id': str(uuid.uuid4()),
            'user_id': self.user_id,
            'platform': 'PEA',
            
            'flow_type': flow_type,
            'flow_direction': flow_direction,
            
            'gross_amount': transaction_amount,
            'net_amount': net_amount,
            'tax_amount': 0.0,  # PEA exonéré d'impôts
            
            'transaction_date': date_transaction,
            'status': 'completed',
            
            'description': description,
            'payment_method': 'PEA',
            
            'created_at': datetime.now().isoformat()
        }

    def _extract_pea_financial_data(self, line: str, flow_type: str) -> Tuple[float, float, float, float]:
        """
        CORRIGÉ : Extraction intelligente des données financières PEA
        Gestion des montants avec espaces et format français
        """
        quantity = 0.0
        unit_price = 0.0
        transaction_amount = 0.0
        fees = 0.0
        
        try:
            # 1. Extraire quantité si présente
            qty_match = re.search(r'Qté\s*:\s*([\d\s,\.]+)', line)
            if qty_match:
                quantity = self._clean_french_amount(qty_match.group(1))
            
            # 2. Extraire cours si présent
            cours_match = re.search(r'Cours\s*:\s*([\d\s,\.]+)', line)
            if cours_match:
                unit_price = self._clean_french_amount(cours_match.group(1))
            
            # 3. Extraction du montant selon le type d'opération
            if flow_type in ['purchase', 'sale']:
                # Achat/Vente : chercher le montant final (pas le cours)
                transaction_amount = self._extract_pea_transaction_amount_french(line, flow_type)
                
                # Calculer les frais si on a quantité × cours
                if quantity > 0 and unit_price > 0:
                    theoretical_amount = quantity * unit_price
                    if transaction_amount > theoretical_amount:
                        fees = transaction_amount - theoretical_amount
                        print(f"    💰 Frais détectés: {fees:.2f}€")
            
            elif flow_type == 'dividend':
                # Dividende : prendre le montant final
                transaction_amount = self._extract_last_amount_french(line)
            
            elif flow_type == 'deposit':
                # Dépôt : montant simple
                transaction_amount = self._extract_last_amount_french(line)
            
            elif flow_type == 'fee':
                # Frais/taxes : montant simple
                transaction_amount = self._extract_last_amount_french(line)
            
            else:
                # Autres : prendre le dernier montant
                transaction_amount = self._extract_last_amount_french(line)
        
        except Exception as e:
            print(f"⚠️  Erreur extraction données financières: {e}")
        
        return quantity, unit_price, transaction_amount, fees

    def _clean_french_amount(self, amount_str: str) -> float:
        """
        NOUVEAU : Nettoyer montant français avec gestion des espaces
        Exemples : "1 088,41" → 1088.41, "143,40" → 143.40
        """
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
            
        except Exception as e:
            print(f"⚠️  Erreur nettoyage montant '{amount_str}': {e}")
            return 0.0

    def _extract_last_amount_french(self, line: str) -> float:
        """
        NOUVEAU : Extraire le dernier montant d'une ligne en format français
        """
        try:
            # Chercher tous les patterns de montants français
            # Patterns : "1 088,41", "143,40", "1088.41", etc.
            patterns = [
                r'(\d{1,3}(?:\s\d{3})*),(\d{2})',  # 1 088,41
                r'(\d+),(\d{2})',                   # 143,40
                r'(\d+)\.(\d{2})',                  # 1088.41
                r'(\d+)'                            # 1088
            ]
            
            all_amounts = []
            
            for pattern in patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    if isinstance(match, tuple):
                        if len(match) == 2:
                            # Format avec décimales
                            integer_part = match[0].replace(' ', '')
                            decimal_part = match[1]
                            amount_str = f"{integer_part}.{decimal_part}"
                        else:
                            # Entier simple
                            amount_str = match[0].replace(' ', '')
                    else:
                        # Match simple
                        amount_str = match.replace(' ', '')
                    
                    try:
                        amount = float(amount_str)
                        if amount > 0:
                            all_amounts.append(amount)
                    except:
                        continue
            
            # Retourner le plus gros montant (souvent le montant de transaction)
            return max(all_amounts) if all_amounts else 0.0
            
        except Exception as e:
            print(f"⚠️  Erreur extraction dernier montant: {e}")
            return 0.0

    def _extract_pea_transaction_amount_french(self, line: str, flow_type: str) -> float:
        """
        NOUVEAU : Extraire montant transaction PEA en format français
        Gestion spéciale pour purchase/deposit vs dividend/fee
        """
        try:
            # Supprimer les parties "Cours :" et "Qté :" pour éviter confusion
            line_cleaned = line
            
            # Supprimer partie cours
            cours_match = re.search(r'Cours\s*:\s*[\d\s,\.]+', line)
            if cours_match:
                line_cleaned = line_cleaned.replace(cours_match.group(0), '')
            
            # Supprimer partie quantité  
            qty_match = re.search(r'Qté\s*:\s*[\d\s,\.]+', line_cleaned)
            if qty_match:
                line_cleaned = line_cleaned.replace(qty_match.group(0), '')
            
            # Extraction selon type de transaction
            if flow_type in ['purchase', 'sale']:
                # Pour achat/vente : chercher le montant le plus important (transaction totale)
                return self._extract_largest_amount_french(line_cleaned)
            
            elif flow_type in ['dividend', 'fee', 'deposit']:
                # Pour dividende/frais/dépôt : prendre le dernier montant
                return self._extract_last_amount_french(line_cleaned)
            
            else:
                # Autres : dernier montant
                return self._extract_last_amount_french(line_cleaned)
        
        except Exception as e:
            print(f"⚠️  Erreur extraction montant transaction: {e}")
            return 0.0

    def _extract_largest_amount_french(self, line: str) -> float:
        """
        NOUVEAU : Extraire le plus gros montant d'une ligne (pour transactions)
        """
        try:
            # Chercher tous les montants français possibles
            patterns = [
                r'(\d{1,3}(?:\s\d{3})*),(\d{2})',  # 1 088,41
                r'(\d+),(\d{2})',                   # 143,40  
                r'(\d+)\.(\d{2})',                  # 1088.41
            ]
            
            all_amounts = []
            
            for pattern in patterns:
                matches = re.findall(pattern, line)
                for match in matches:
                    if len(match) == 2:
                        integer_part = match[0].replace(' ', '')
                        decimal_part = match[1]
                        amount_str = f"{integer_part}.{decimal_part}"
                        
                        try:
                            amount = float(amount_str)
                            if amount > 0:
                                all_amounts.append(amount)
                        except:
                            continue
            
            # Retourner le plus gros montant (montant de la transaction)
            return max(all_amounts) if all_amounts else 0.0
            
        except Exception as e:
            print(f"⚠️  Erreur extraction plus gros montant: {e}")
            return 0.0

    def _extract_pea_description(self, line: str) -> str:
        """AMÉLIORÉE : Extraire description nettoyée PEA"""
        # Enlever date au début
        cleaned = re.sub(r'^\d{2}/\d{2}/\d{4}\s+', '', line)
        
        # Enlever quantité et cours avec leurs valeurs
        cleaned = re.sub(r'Qté\s*:\s*[\d\s,\.]+(?=\s|$)', '', cleaned)
        cleaned = re.sub(r'Cours\s*:\s*[\d\s,\.]+(?=\s|$)', '', cleaned)
        
        # Enlever les montants en fin de ligne (garder seulement le texte descriptif)
        cleaned = re.sub(r'(?:\d{1,3}(?:\s\d{3})*|\d+),\d{2}(?:\s|$)', '', cleaned)
        
        # Nettoyer les espaces multiples
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned if cleaned else "Transaction PEA"

    def _parse_pea_evaluation(self, pdf_path: str) -> List[Dict]:
        """
        Parser évaluation PEA vers portfolio_positions 
        """
        positions = []
        
        print(f"📄 Parsing PEA évaluation vers portfolio_positions: {pdf_path}")
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                print(f"  📖 Page {page_num + 1}...")
                
                tables = page.extract_tables()
                
                if tables:
                    for table_idx, table in enumerate(tables):
                        if table and len(table) > 1:
                            # Vérifier si c'est un tableau de positions
                            has_isin = any(re.search(r'[A-Z]{2}\d{10}', str(cell)) 
                                        for row in table[:3] for cell in row if cell)
                            
                            if has_isin:
                                print(f"    ✅ Tableau de positions détecté")
                                extracted_positions = self._parse_pea_positions_to_portfolio(table)
                                positions.extend(extracted_positions)
        
        print(f"✅ PEA évaluation parsée: {len(positions)} positions portfolio")
        return positions

    def _parse_pea_positions_to_portfolio(self, table: List[List]) -> List[Dict]:
        """
        Parser positions PEA vers portfolio_positions 
        Structure optimisée pour la valorisation mensuelle
        """
        positions = []
        
        print(f"📊 Conversion vers portfolio_positions...")
        
        if not table or len(table) < 2:
            return positions
        
        header = table[0]
        data_rows = table[1:]
        
        # Détecter le cas multi-lignes
        if data_rows and len(data_rows[0]) >= 4:
            first_row = data_rows[0]
            has_multiline = any('\n' in str(cell) for cell in first_row if cell)
            
            if has_multiline:
                print("🔧 Données multi-lignes détectées pour portfolio")
                positions = self._parse_multiline_pea_data(first_row)
            else:
                print("📄 Données normales pour portfolio")
                positions = self._parse_normal_pea_data(data_rows)
        
        return positions

    def _parse_multiline_pea_data(self, multiline_row: List) -> List[Dict]:
        """
        CORRIGÉ : Parser données PEA multi-lignes avec nettoyage des codes et montants
        """
        positions = []
        
        print("🔧 Parsing données multi-lignes PEA corrigé...")
        
        try:
            # Extraire et diviser chaque colonne
            designations_raw = str(multiline_row[0]) if len(multiline_row) > 0 else ''
            designations = [d.strip() for d in designations_raw.split('\n') if d.strip()]
            
            quantities_raw = str(multiline_row[1]) if len(multiline_row) > 1 else ''
            quantities = [q.strip() for q in quantities_raw.split('\n') if q.strip()]
            
            prices_raw = str(multiline_row[2]) if len(multiline_row) > 2 else ''
            prices = [p.strip() for p in prices_raw.split('\n') if p.strip()]
            
            values_raw = str(multiline_row[3]) if len(multiline_row) > 3 else ''
            values = [v.strip() for v in values_raw.split('\n') if v.strip()]
            
            percentages_raw = str(multiline_row[4]) if len(multiline_row) > 4 else ''
            percentages = [p.strip() for p in percentages_raw.split('\n') if p.strip()]
            
            print(f"  📊 Lignes extraites: {len(designations)} désignations")
            
            # Filtrer et nettoyer les désignations
            cleaned_designations = []
            for i, designation in enumerate(designations):
                # CORRECTION 1 : Ignorer les sections en gras
                if self._is_section_header(designation):
                    print(f"    ⚠️  Section ignorée: {designation}")
                    continue
                
                # CORRECTION 2 : Vérifier présence ISIN
                if not re.search(r'[A-Z]{2}\d{10}', designation):
                    print(f"    ⚠️  Ligne sans ISIN ignorée: {designation}")
                    continue
                
                # CORRECTION 3 : Supprimer le code "025" à la fin
                cleaned_designation = self._clean_pea_designation(designation)
                cleaned_designations.append((i, cleaned_designation))
            
            print(f"  ✅ Positions valides: {len(cleaned_designations)}")
            
            # Créer les positions
            for original_index, designation in cleaned_designations:
                try:
                    # Extraire ISIN
                    isin_match = re.search(r'[A-Z]{2}\d{10}', designation)
                    isin = isin_match.group(0) if isin_match else None
                    
                    if not isin:
                        continue
                    
                    # Extraire nom de l'actif
                    asset_name = designation.replace(isin, '').strip()
                    asset_name = re.sub(r'^\d+\s*', '', asset_name).strip()
                    
                    # CORRECTION 4 : Nettoyer les valeurs avec format français
                    quantity = self._clean_french_amount(quantities[original_index]) if original_index < len(quantities) else 0
                    price = self._clean_french_amount(prices[original_index]) if original_index < len(prices) else 0
                    market_value = self._clean_french_amount(values[original_index]) if original_index < len(values) else 0
                    percentage = self._clean_french_amount(percentages[original_index]) if original_index < len(percentages) else 0
                    
                    # Validation
                    if quantity <= 0 and market_value <= 0:
                        print(f"    ⚠️  Position ignorée (valeurs nulles): {asset_name}")
                        continue
                    
                    # Créer la position
                    position = {
                        'id': str(uuid.uuid4()),
                        'user_id': self.user_id,
                        'platform': 'PEA',
                        
                        'isin': isin,
                        'asset_name': asset_name[:250],
                        'quantity': quantity,
                        'current_price': price,
                        'market_value': market_value,
                        'portfolio_percentage': percentage,
                        
                        'asset_class': self._classify_pea_asset(asset_name),
                        'valuation_date': datetime.now().strftime('%Y-%m-%d'),
                        
                        'created_at': datetime.now().isoformat()
                    }
                    
                    positions.append(position)
                    print(f"    ✅ Position: {isin} - {asset_name[:30]}... | Qté:{quantity} | Val:{market_value}€")
                    
                except Exception as e:
                    print(f"    ❌ Erreur position {original_index}: {e}")
                    continue
            
            print(f"✅ Parsing multi-lignes terminé: {len(positions)} positions créées")
            
        except Exception as e:
            print(f"❌ Erreur parsing multi-lignes: {e}")
        
        return positions

    def _is_section_header(self, designation: str) -> bool:
        """
        NOUVEAU : Détecter si une ligne est un en-tête de section
        """
        sections_keywords = [
            'ACTIONS FRANCAISES',
            'VALEUR EUROPE', 
            'ACTIONS ETRANGERES',
            'Divers',
            'LIQUIDITES',
            'OBLIGATIONS',
            'TOTAL PORTEFEUILLE',
            'SOLDE ESPECES'
        ]
        
        designation_upper = designation.upper()
        
        return any(keyword in designation_upper for keyword in sections_keywords)

    def _clean_pea_designation(self, designation: str) -> str:
        """
        NOUVEAU : Nettoyer la désignation PEA
        Supprime le code "025" à la fin et autres codes internes
        """
        cleaned = designation.strip()
        
        # CORRECTION : Supprimer le code "025" à la fin
        cleaned = re.sub(r'\s+025\s*$', '', cleaned)
        
        # Supprimer autres codes potentiels (3 chiffres à la fin)
        cleaned = re.sub(r'\s+\d{3}\s*$', '', cleaned)
        
        # Nettoyer espaces multiples
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned

    def _parse_normal_pea_data(self, data_rows: List[List]) -> List[Dict]:
        """Parser données PEA normales (une ligne par position) CORRIGÉ"""
        positions = []
        
        print("📄 Parsing données normales...")
        
        for row_idx, row in enumerate(data_rows):
            if not row or not any(cell for cell in row):
                continue
            
            try:
                # Extraction normale
                designation = str(row[0]) if len(row) > 0 else ''
                
                # Ignorer sections
                if self._is_section_header(designation):
                    continue
                
                # Extraire ISIN
                isin_match = re.search(r'[A-Z]{2}\d{10}', designation)
                isin = isin_match.group(0) if isin_match else None
                
                if not isin:
                    continue
                
                # Nettoyer désignation
                designation = self._clean_pea_designation(designation)
                
                # Nom de l'actif
                asset_name = designation.replace(isin, '').strip()
                asset_name = re.sub(r'^\d+\s*', '', asset_name).strip()
                
                # Valeurs numériques CORRIGÉES
                quantity = self._clean_french_amount(row[1]) if len(row) > 1 else 0
                price = self._clean_french_amount(row[2]) if len(row) > 2 else 0
                market_value = self._clean_french_amount(row[3]) if len(row) > 3 else 0
                percentage = self._clean_french_amount(row[4]) if len(row) > 4 else 0
                
                # Validation
                if quantity <= 0 and market_value <= 0:
                    continue
                
                position = {
                    'id': str(uuid.uuid4()),
                    'user_id': self.user_id,
                    'platform': 'PEA',
                    
                    'isin': isin,
                    'asset_name': asset_name[:250],
                    'quantity': quantity,
                    'current_price': price,
                    'market_value': market_value,
                    'portfolio_percentage': percentage,
                    
                    'asset_class': self._classify_pea_asset(asset_name),
                    'valuation_date': datetime.now().strftime('%Y-%m-%d'),
                    
                    'created_at': datetime.now().isoformat()
                }
                
                positions.append(position)
                print(f"  ✅ Position {row_idx}: {isin} - {asset_name[:30]}...")
                
            except Exception as e:
                print(f"  ❌ Erreur ligne {row_idx}: {e}")
                continue
        
        return positions

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
        if 'en cours' in status.lower():
            return 'active'
        elif 'terminé' in status.lower() or 'remboursé' in status.lower():
            return 'completed'
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