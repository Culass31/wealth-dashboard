# ===== backend/data/unified_parser.py - PARSER UNIFIÉ EXPERT =====
import pandas as pd
import pdfplumber
from typing import List, Dict, Any, Tuple, Optional
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
        """Parser LPB avec fiscalité corrigée"""
        
        # Parser projets
        projects_df = pd.read_excel(file_path, sheet_name='Projets')
        investissements = self._parse_lpb_projects(projects_df)
        
        # Parser relevé avec gestion taxes
        account_df = pd.read_excel(file_path, sheet_name='Relevé compte')
        flux_tresorerie = self._parse_lpb_account(account_df)
        
        return investissements, flux_tresorerie
    
    def _parse_lpb_projects(self, df: pd.DataFrame) -> List[Dict]:
        """Parser projets LPB avec statuts corrigés"""
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
            
            # Statut corrigé
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
            return 'deposit', 'out'  # Argent frais injecté
        elif 'souscription' in nature_lower:
            return 'investment', 'out'  # Investissement projet
        elif 'retrait de l\'épargne' in nature_lower:
            return 'withdrawal', 'in'  # Récupération fonds
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
        """Parser relevé BienPrêter avec calcul taxes correct"""
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
                flow_direction = 'out'
            
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
                flow_direction = 'out'
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
                    flow_direction = 'out'
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
        """Parser PEA avec gestion ISIN/quantités/cours"""
        
        investissements = []
        flux_tresorerie = []
        
        # Parser relevé (transactions)
        if releve_path and os.path.exists(releve_path):
            flux_tresorerie = self._parse_pea_releve(releve_path)
        
        # Parser évaluation (positions)
        if evaluation_path and os.path.exists(evaluation_path):
            positions = self._parse_pea_evaluation(evaluation_path)
            investissements = self._convert_pea_positions_to_investments(positions)
        
        return investissements, flux_tresorerie

    def _parse_pea_releve(self, pdf_path: str) -> List[Dict]:
        """Parser relevé PEA avec extraction intelligente"""
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
    
    def _parse_pea_transaction_line(self, line: str) -> Optional[Dict]:
        """Parser ligne transaction PEA avec extraction montants CORRIGÉE"""
        
        # Extraire date
        date_match = re.match(r'^(\d{2}/\d{2}/\d{4})', line)
        if not date_match:
            return None
        
        date_transaction = standardize_date(date_match.group(1))
        
        # Classification par mots-clés
        line_upper = line.upper()
        
        if 'COUPONS' in line_upper:
            flow_type = 'dividend'
            flow_direction = 'in'
        elif 'ACH CPT' in line_upper:
            flow_type = 'purchase'
            flow_direction = 'out'
        elif 'VTE CPT' in line_upper:
            flow_type = 'sale'
            flow_direction = 'in'
        elif 'TTF' in line_upper:
            flow_type = 'fee'
            flow_direction = 'out'
        elif 'INVESTISSEMENT ESPECES' in line_upper:
            flow_type = 'deposit'
            flow_direction = 'out'
        elif 'REGULARISATION' in line_upper:
            flow_type = 'adjustment'
            flow_direction = 'in'
        else:
            flow_type = 'other'
            flow_direction = 'in'
        
        # CORRECTION : Extraction montants avec regex précises
        # Extraction quantité et cours pour achats/ventes avec délimiteurs
        quantity = 0.0
        unit_price = 0.0
        
        # Regex CORRIGÉE pour quantité - s'arrête avant "Cours" ou espaces multiples
        qty_match = re.search(r'Qté\s*:\s*([\d,\.]+)(?=\s+[A-Za-z]|\s{2,}|$)', line)
        if qty_match:
            quantity = clean_amount(qty_match.group(1))
        
        # Regex CORRIGÉE pour cours - s'arrête avant des espaces multiples ou fin
        cours_match = re.search(r'Cours\s*:\s*([\d,\.]+)(?=\s{2,}|$)', line)
        if cours_match:
            unit_price = clean_amount(cours_match.group(1))
        
        # NOUVELLE APPROCHE : Extraction montants finaux plus intelligente
        debit = 0.0
        credit = 0.0
        
        # Nettoyer la ligne en enlevant les parties "Qté" et "Cours" déjà traitées
        line_for_amounts = line
        if qty_match:
            line_for_amounts = line_for_amounts.replace(qty_match.group(0), ' ')
        if cours_match:
            line_for_amounts = line_for_amounts.replace(cours_match.group(0), ' ')
        
        # Chercher les montants restants (format français avec virgules décimales)
        # Pattern pour montants : nombres avec virgule décimale et possibles espaces pour milliers
        amount_pattern = r'(?:\d{1,3}(?:\s\d{3})*|\d+),\d{2}'
        remaining_amounts = re.findall(amount_pattern, line_for_amounts)
        
        if remaining_amounts:
            # Nettoyer et convertir les montants trouvés
            cleaned_amounts = []
            for amount_str in remaining_amounts:
                try:
                    # Nettoyer les espaces (séparateurs de milliers) et convertir
                    cleaned = amount_str.replace(' ', '').replace(',', '.')
                    amount_val = float(cleaned)
                    cleaned_amounts.append(amount_val)
                except:
                    continue
            
            if cleaned_amounts:
                # Prendre le montant le plus élevé (souvent le montant total de l'opération)
                final_amount = max(cleaned_amounts)
                
                if flow_direction == 'out':
                    debit = final_amount
                else:
                    credit = final_amount
        
        # Si pas de montants trouvés par regex, fallback sur l'ancienne méthode
        if debit == 0.0 and credit == 0.0:
            # Fallback : chercher tous les patterns numériques
            all_amounts = re.findall(r'[\d\s,\.]+', line)
            
            if all_amounts:
                # Prendre le dernier montant et le nettoyer proprement
                last_amount_str = all_amounts[-1]
                try:
                    final_amount = clean_amount(last_amount_str)
                    if final_amount > 0:
                        if flow_direction == 'out':
                            debit = final_amount
                        else:
                            credit = final_amount
                except:
                    pass
        
        # Description nettoyée
        description = self._extract_pea_description(line)
        
        # Montant final pour le flux
        final_amount = credit if credit > 0 else debit
        net_amount = final_amount if flow_direction == 'in' else -final_amount
        
        return {
            'id': str(uuid.uuid4()),
            'user_id': self.user_id,
            'platform': 'PEA',
            
            'flow_type': flow_type,
            'flow_direction': flow_direction,
            
            'gross_amount': final_amount,
            'net_amount': net_amount,
            'tax_amount': 0.0,  # PEA exonéré
            
            'quantity': quantity,
            'unit_price': unit_price,
            
            'transaction_date': date_transaction,
            'status': 'completed',
            
            'description': description,
            'payment_method': 'PEA',
            
            'created_at': datetime.now().isoformat()
        }

    def _extract_pea_description(self, line: str) -> str:
        """AMÉLIORÉE : Extraire description nettoyée PEA"""
        # Enlever date au début
        cleaned = re.sub(r'^\d{2}/\d{2}/\d{4}\s+', '', line)
        
        # Enlever quantité et cours avec leurs valeurs
        cleaned = re.sub(r'Qté\s*:\s*[\d,\.]+(?=\s|$)', '', cleaned)
        cleaned = re.sub(r'Cours\s*:\s*[\d,\.]+(?=\s|$)', '', cleaned)
        
        # Enlever les montants en fin de ligne (garder seulement le texte descriptif)
        cleaned = re.sub(r'(?:\d{1,3}(?:\s\d{3})*|\d+),\d{2}(?:\s|$)', '', cleaned)
        
        # Nettoyer les espaces multiples
        cleaned = re.sub(r'\s+', ' ', cleaned).strip()
        
        return cleaned if cleaned else "Transaction PEA"

    def _parse_pea_evaluation(self, pdf_path: str) -> List[Dict]:
        """Parser évaluation PEA avec extraction tableau améliorée"""
        positions = []
        
        print(f"📄 Parsing PEA évaluation: {pdf_path}")
        
        with pdfplumber.open(pdf_path) as pdf:
            for page_num, page in enumerate(pdf.pages):
                print(f"  📖 Page {page_num + 1}...")
                
                # Méthode 1 : Extraction de tableaux
                tables = page.extract_tables()
                
                if tables:
                    print(f"    📊 {len(tables)} tableau(x) trouvé(s)")
                    
                    for table_idx, table in enumerate(tables):
                        if table and len(table) > 1:
                            print(f"    📋 Tableau {table_idx + 1}: {len(table)} lignes")
                            
                            # Vérifier si c'est un tableau de positions (contient des ISIN)
                            has_isin = False
                            for row in table[:3]:  # Vérifier les 3 premières lignes
                                if any(re.search(r'FR\d{10}', str(cell)) for cell in row if cell):
                                    has_isin = True
                                    break
                            
                            if has_isin:
                                print(f"    ✅ Tableau de positions détecté")
                                extracted_positions = self._parse_pea_positions_table(table)
                                positions.extend(extracted_positions)
                            else:
                                print(f"    ⚠️  Tableau ignoré (pas de positions)")
                
                # Méthode 2 : Fallback texte si pas de tableaux
                if not tables:
                    print(f"    📝 Pas de tableaux, essai extraction texte...")
                    text = page.extract_text()
                    if text and 'EVALUATION' in text.upper():
                        text_positions = self._parse_pea_positions_text(text)
                        positions.extend(text_positions)
        
        print(f"✅ PEA évaluation parsée: {len(positions)} positions totales")
        return positions
    
    def _parse_pea_positions_text(self, text: str) -> List[Dict]:
        """Parser positions PEA depuis texte brut (fallback)"""
        positions = []
        
        print("📝 Extraction PEA depuis texte...")
        
        lines = text.split('\n')
        
        for line_num, line in enumerate(lines):
            # Chercher les lignes avec ISIN
            isin_match = re.search(r'FR\d{10}', line)
            if isin_match:
                isin = isin_match.group(0)
                
                # Extraire nom (après ISIN)
                asset_name = line.replace(isin, '').strip()
                asset_name = re.sub(r'^\d+\s*', '', asset_name)  # Supprimer numéros début
                
                # Chercher les montants dans la ligne
                amounts = re.findall(r'[\d\s,\.]+', line)
                cleaned_amounts = []
                
                for amount_str in amounts:
                    try:
                        amount = clean_amount(amount_str)
                        if amount > 0:
                            cleaned_amounts.append(amount)
                    except:
                        continue
                
                # Assigner les montants selon l'ordre attendu: quantité, cours, valorisation
                quantity = cleaned_amounts[0] if len(cleaned_amounts) > 0 else 0
                price = cleaned_amounts[1] if len(cleaned_amounts) > 1 else 0
                market_value = cleaned_amounts[2] if len(cleaned_amounts) > 2 else 0
                
                if quantity > 0 or market_value > 0:
                    position = {
                        'id': str(uuid.uuid4()),
                        'user_id': self.user_id,
                        'platform': 'PEA',
                        'isin': isin,
                        'asset_name': asset_name or f"Asset_{isin}",
                        'quantity': quantity,
                        'current_price': price,
                        'market_value': market_value,
                        'portfolio_percentage': 0.0,
                        'asset_class': self._classify_pea_asset(asset_name),
                        'valuation_date': datetime.now().strftime('%Y-%m-%d'),
                        'created_at': datetime.now().isoformat()
                    }
                    
                    positions.append(position)
                    print(f"  ✅ Position texte: {isin} - {asset_name[:20]}...")
        
        return positions

    def _parse_pea_positions_table(self, table: List[List]) -> List[Dict]:
        """Parser tableau positions PEA CORRIGÉ pour traitement ligne par ligne"""
        positions = []
        
        print(f"📊 Analyse tableau PEA: {len(table)} lignes")
        
        if not table or len(table) < 2:
            print("⚠️  Tableau PEA vide ou trop petit")
            return positions
        
        # Analyser l'en-tête pour comprendre la structure
        header = table[0] if table[0] else []
        print(f"📋 En-tête détecté: {header}")
        
        # Détecter les colonnes
        col_mapping = {
            'designation': 0,  # Colonne ISIN + Nom
            'quantity': 1,     # Quantité  
            'price': 2,        # Cours
            'value': 3,        # Valorisation
            'percentage': 4    # %
        }
        
        # Parser chaque ligne individuellement
        for row_idx, row in enumerate(table[1:], 1):  # Skip header
            if not row or not any(cell for cell in row):
                continue
            
            try:
                print(f"  📄 Ligne {row_idx}: {row[:5]}...")  # Debug: afficher début de ligne
                
                # 1. Extraction ISIN et nom (colonne 0)
                designation_cell = row[col_mapping['designation']] if len(row) > col_mapping['designation'] else ''
                designation = str(designation_cell) if designation_cell else ''
                
                # Extraction ISIN
                isin_match = re.search(r'FR\d{10}', designation)
                isin = isin_match.group(0) if isin_match else None
                
                if not isin:  # Ignorer les lignes sans ISIN
                    print(f"    ⚠️  Pas d'ISIN trouvé dans: {designation}")
                    continue
                
                # Nom de l'actif (nettoyer)
                asset_name = designation.replace(isin, '').strip()
                asset_name = re.sub(r'^\d{3}\s*', '', asset_name).strip()  # Supprimer codes numériques
                
                # 2. Extraction quantité (colonne 1) - LIGNE PAR LIGNE
                quantity_cell = row[col_mapping['quantity']] if len(row) > col_mapping['quantity'] else 0
                quantity = clean_amount(quantity_cell) if quantity_cell is not None else 0
                
                # 3. Extraction cours (colonne 2) - LIGNE PAR LIGNE 
                price_cell = row[col_mapping['price']] if len(row) > col_mapping['price'] else 0
                price = clean_amount(price_cell) if price_cell is not None else 0
                
                # 4. Extraction valorisation (colonne 3) - LIGNE PAR LIGNE
                value_cell = row[col_mapping['value']] if len(row) > col_mapping['value'] else 0
                market_value = clean_amount(value_cell) if value_cell is not None else 0
                
                # 5. Extraction pourcentage (colonne 4) - LIGNE PAR LIGNE
                percentage_cell = row[col_mapping['percentage']] if len(row) > col_mapping['percentage'] else 0
                percentage = clean_amount(percentage_cell) if percentage_cell is not None else 0
                
                # Debug pour cette ligne
                print(f"    ✅ {isin} | {asset_name[:15]}... | Qté:{quantity} | Cours:{price} | Val:{market_value}")
                
                # Validation des données
                if quantity <= 0 and market_value <= 0:
                    print(f"    ⚠️  Ligne ignorée: quantité et valorisation nulles")
                    continue
                
                # Créer la position
                position = {
                    'id': str(uuid.uuid4()),
                    'user_id': self.user_id,
                    'platform': 'PEA',
                    
                    'isin': isin,
                    'asset_name': asset_name or f"Asset_{isin}",
                    'quantity': quantity,
                    'current_price': price,
                    'market_value': market_value,
                    'portfolio_percentage': percentage,
                    
                    'asset_class': self._classify_pea_asset(asset_name),
                    'valuation_date': datetime.now().strftime('%Y-%m-%d'),
                    
                    'created_at': datetime.now().isoformat()
                }
                
                positions.append(position)
                
            except Exception as e:
                print(f"    ❌ Erreur ligne {row_idx}: {e}")
                print(f"       Contenu ligne: {row}")
                continue
        
        print(f"✅ PEA tableau parsé: {len(positions)} positions extraites")
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