# ===== backend/analytics/patrimoine_calculator.py - MOTEUR DE CALCUL DU DASHBOARD (v1.9.5 - CORRECTION TRI & BENCHMARK) =====
import logging
import sys
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [%(funcName)s] %(message)s')
import pandas as pd
from typing import Dict, List, Tuple, Any
from datetime import datetime
from scipy.optimize import fsolve

import warnings
import yfinance as yf

warnings.filterwarnings('ignore', category=FutureWarning)



# Bloc d'import robuste
try:
    from backend.models.database import ExpertDatabaseManager
except ImportError:
    import sys
    from pathlib import Path
    project_root = Path(__file__).resolve().parent.parent.parent
    if str(project_root) not in sys.path:
        sys.path.append(str(project_root))
    from backend.models.database import ExpertDatabaseManager

class PatrimoineCalculator:
    """
    Moteur de calcul centralisé pour le Wealth Dashboard.
    """

    def __init__(self, user_id: str):
        self.user_id = user_id
        self.db = ExpertDatabaseManager()
        self.benchmarks_cache = {}
        self._load_data()

    def _load_data(self):
        logging.info(f"Chargement des données pour l'utilisateur {self.user_id}...")
        self.investments_df = self.db.get_user_investments(self.user_id)
        self.cash_flows_df = self.db.get_user_cash_flows(self.user_id)
        self.positions_df = self.db.get_portfolio_positions(self.user_id)
        self.liquidity_df = self.db.get_liquidity_balances(self.user_id)

        # Assurer que les colonnes de date sont de type datetime et gérer les erreurs
        if not self.cash_flows_df.empty and 'transaction_date' in self.cash_flows_df.columns:
            self.cash_flows_df['transaction_date'] = pd.to_datetime(self.cash_flows_df['transaction_date'], errors='coerce')
            self.cash_flows_df = self.cash_flows_df.dropna(subset=['transaction_date'])
        
        if not self.investments_df.empty:
            for col in ['investment_date', 'signature_date', 'expected_end_date', 'actual_end_date']:
                if col in self.investments_df.columns:
                    self.investments_df[col] = pd.to_datetime(self.investments_df[col], errors='coerce')
        logging.info("Données chargées.")
        logging.debug(f"Investments DF head:\n{self.investments_df.head()}")
        logging.debug(f"Investments DF info:\n{self.investments_df.info()}")
        logging.debug(f"Cash Flows DF head:\n{self.cash_flows_df.head()}")
        logging.debug(f"Cash Flows DF info:\n{self.cash_flows_df.info()}")
        logging.debug(f"Positions DF head:\n{self.positions_df.head()}")
        logging.debug(f"Positions DF info:\n{self.positions_df.info()}")
        logging.debug(f"Liquidity DF head:\n{self.liquidity_df.head()}")
        logging.debug(f"Liquidity DF info:\n{self.liquidity_df.info()}")

    def _get_benchmark_data(self, start_date: datetime, end_date: datetime, ticker: str = "CW8.PA") -> pd.Series:
        """
        Récupère les données historiques d'un benchmark (ex: ETF World) via yfinance.
        Retourne une série Pandas avec DatetimeIndex.
        """
        logging.info(f"Récupération des données benchmark pour {ticker} de {start_date.strftime('%Y-%m-%d')} à {end_date.strftime('%Y-%m-%d')}")
        try:
            # Utiliser .tz_localize(None) pour supprimer les informations de fuseau horaire si présentes
            # Cela aide à éviter les problèmes de comparaison avec des DatetimeIndex sans fuseau horaire
            data = yf.download(ticker, start=start_date, end=end_date, progress=False)
            if data.empty:
                logging.warning(f"Aucune donnée trouvée pour le ticker {ticker} entre {start_date} et {end_date}.")
                return pd.Series(dtype=float)
            
            # Utiliser la colonne 'Adj Close' pour les prix ajustés
            if 'Adj Close' in data.columns:
                benchmark_series = data['Adj Close'].dropna()
            elif 'Close' in data.columns:
                logging.warning(f"La colonne 'Adj Close' est manquante pour {ticker}. Utilisation de la colonne 'Close' à la place.")
                benchmark_series = data['Close'].dropna()
            else:
                logging.error(f"Ni 'Adj Close' ni 'Close' ne sont disponibles dans les données récupérées pour {ticker}. Colonnes disponibles: {data.columns.tolist()}")
                return pd.Series(dtype=float)
            
            # S'assurer que l'index est un DatetimeIndex sans informations de fuseau horaire
            if benchmark_series.index.tz is not None:
                benchmark_series.index = benchmark_series.index.tz_localize(None)
            
            # Normaliser la série pour qu'elle commence à 100 au début de la période
            if not benchmark_series.empty:
                benchmark_series = (benchmark_series / benchmark_series.iloc[0]) * 100
            
            logging.info(f"Données benchmark récupérées pour {ticker}. Premières dates: {benchmark_series.index.min()}, Dernières dates: {benchmark_series.index.max()}")
            return benchmark_series
        except Exception as e:
            logging.error(f"Erreur lors de la récupération des données benchmark pour {ticker}: {e}")
            return pd.Series(dtype=float)

    def _xirr(self, cash_flows: List[Tuple[datetime, float]]) -> float:
        if len(cash_flows) < 2:
            return 0.0

        # Trier les flux par date
        cash_flows = sorted(cash_flows, key=lambda x: x[0])

        # Fonction pour calculer la valeur actuelle nette (VAN)
        def npv(rate):
            return sum(amount / (1 + rate)**((date - cash_flows[0][0]).days / 365.25) for date, amount in cash_flows)

        # Recherche itérative du TRI
        try:
            rate = fsolve(npv, 0.1)[0]
            return rate if -0.99 <= rate <= 5.0 else 0.0
        except (RuntimeError, TypeError):
            # Essayer une autre estimation initiale si la première échoue
            try:
                rate = fsolve(npv, -0.1)[0]
                return rate if -0.99 <= rate <= 5.0 else 0.0
            except (RuntimeError, TypeError):
                return 0.0

    def _prepare_flows_for_tri(self, df: pd.DataFrame, amount_col: str) -> List[Tuple[datetime, float]]:
        flows = []
        for _, row in df.iterrows():
            if pd.isna(row['transaction_date']): continue
            signed_amount = row[amount_col] if row['flow_direction'] == 'in' else -row[amount_col]
            flows.append((row['transaction_date'], signed_amount))
        return flows

    def get_global_kpis(self) -> Dict[str, Any]:
        logging.info("Calcul des KPIs globaux...")
        total_encours_cf = self.investments_df['remaining_capital'].sum() if 'remaining_capital' in self.investments_df.columns else 0
        logging.debug(f"total_encours_cf: {total_encours_cf}")
        pea_av_value = self.positions_df['market_value'].sum() if 'market_value' in self.positions_df.columns else 0
        logging.debug(f"pea_av_value: {pea_av_value}")
        total_liquidity = 0
        if not self.liquidity_df.empty and 'balance_date' in self.liquidity_df.columns:
            latest_liquidity = self.liquidity_df.sort_values('balance_date').drop_duplicates('platform', keep='last')
            total_liquidity = latest_liquidity['amount'].sum()
        logging.debug(f"total_liquidity: {total_liquidity}")

        patrimoine_total = total_encours_cf + pea_av_value + total_liquidity
        logging.debug(f"patrimoine_total: {patrimoine_total}")
        total_apports = self.cash_flows_df[self.cash_flows_df['flow_type'] == 'deposit']['gross_amount'].sum() if not self.cash_flows_df.empty else 0
        plus_value_nette = patrimoine_total - total_apports
        
        # --- Construction robuste des flux pour le TRI global ---
        all_flows_for_tri = pd.DataFrame(columns=['transaction_date', 'gross_amount', 'net_amount', 'flow_direction'])
        
        # 1. Ajouter tous les flux de trésorerie existants
        if not self.cash_flows_df.empty:
            all_flows_for_tri = pd.concat([all_flows_for_tri, self.cash_flows_df], ignore_index=True)

        # 2. Ajouter les investissements initiaux qui ne sont pas déjà des flux 'investment' (out)
        # Cela couvre les cas où l'investissement initial n'est pas dans cash_flows_df
        if not self.investments_df.empty:
            for _, inv in self.investments_df.iterrows():
                # Vérifier si cet investissement a déjà un flux de type 'investment' (out) dans cash_flows_df
                is_covered = False
                if not self.cash_flows_df.empty:
                    covered_flows = self.cash_flows_df[
                        (self.cash_flows_df['investment_id'] == inv['id']) &
                        (self.cash_flows_df['flow_type'] == 'investment') &
                        (self.cash_flows_df['flow_direction'] == 'out')
                    ]
                    if not covered_flows.empty:
                        is_covered = True
                
                if not is_covered and inv['invested_amount'] > 0 and pd.notna(inv['investment_date']):
                    initial_investment_flow = pd.DataFrame([{
                        'transaction_date': pd.Timestamp(inv['investment_date']),
                        'gross_amount': inv['invested_amount'],
                        'net_amount': inv['invested_amount'], # Pour l'investissement initial, brut = net
                        'flow_direction': 'out',
                        'flow_type': 'investment_initial' # Nouveau type pour distinguer
                    }])
                    all_flows_for_tri = pd.concat([all_flows_for_tri, initial_investment_flow], ignore_index=True)

        # 3. Ajouter la valeur actuelle du patrimoine comme flux final
        if patrimoine_total > 0:
            final_valuation_flow = pd.DataFrame([{
                'transaction_date': pd.Timestamp(datetime.now()),
                'gross_amount': patrimoine_total,
                'net_amount': patrimoine_total,
                'flow_direction': 'in',
                'flow_type': 'valuation'
            }])
            all_flows_for_tri = pd.concat([all_flows_for_tri, final_valuation_flow], ignore_index=True)
        
        # S'assurer que les dates sont au bon format et trier
        all_flows_for_tri['transaction_date'] = pd.to_datetime(all_flows_for_tri['transaction_date'])
        all_flows_for_tri = all_flows_for_tri.sort_values('transaction_date').reset_index(drop=True)

        logging.debug(f"Flux pour TRI global (brut):\n{all_flows_for_tri[['transaction_date', 'gross_amount', 'flow_direction']].to_string()}")
        logging.debug(f"Flux pour TRI global (net):\n{all_flows_for_tri[['transaction_date', 'net_amount', 'flow_direction']].to_string()}")

        tri_brut = self._xirr(self._prepare_flows_for_tri(all_flows_for_tri, 'gross_amount'))
        tri_net = self._xirr(self._prepare_flows_for_tri(all_flows_for_tri, 'net_amount'))
        
        herfindahl_index = self.calculate_herfindahl_index()
        
        return {"patrimoine_total": patrimoine_total, 
                "plus_value_nette": plus_value_nette, 
                "total_apports": total_apports, 
                "tri_global_brut": tri_brut * 100, 
                "tri_global_net": tri_net * 100,
                "herfindahl_index": herfindahl_index}

    def get_platform_details(self) -> Dict[str, Dict[str, Any]]:
        logging.info("Calcul des métriques par plateforme...")
        details = {}
        platform_list = []
        
        if not self.investments_df.empty and 'platform' in self.investments_df.columns: platform_list.extend(self.investments_df['platform'].unique())
        if not self.positions_df.empty and 'platform' in self.positions_df.columns: platform_list.extend(self.positions_df['platform'].unique())
        platforms = pd.unique(platform_list).tolist()

        for p in platforms:
            logging.debug(f"Calcul pour la plateforme: {p}")
            is_cf = p not in ['PEA', 'Assurance_Vie']
            
            # Correction: Inclure tous les statuts pertinents
            inv_p = self.investments_df[
                (self.investments_df['platform'] == p) & 
                (self.investments_df['status'].isin(['active', 'completed', 'delayed', 'in_procedure']))
            ] if not self.investments_df.empty else pd.DataFrame()

            flows_p = self.cash_flows_df[self.cash_flows_df['platform'] == p] if not self.cash_flows_df.empty else pd.DataFrame()
            pos_p = self.positions_df[self.positions_df['platform'] == p] if not self.positions_df.empty else pd.DataFrame()
            
            logging.debug(f"  inv_p head:\n{inv_p.head()}")
            logging.debug(f"  flows_p head:\n{flows_p.head()}")
            logging.debug(f"  pos_p head:\n{pos_p.head()}")

            cap_investi = inv_p['invested_amount'].sum() if is_cf and not inv_p.empty else (flows_p[flows_p['flow_type'] == 'deposit']['gross_amount'].sum() if not flows_p.empty else 0)
            cap_encours = inv_p['remaining_capital'].sum() if is_cf and not inv_p.empty else (pos_p['market_value'].sum() if not pos_p.empty else 0)
            int_bruts = flows_p[flows_p['flow_type'].isin(['interest', 'dividend', 'repayment'])]['interest_amount'].sum() if not flows_p.empty else 0
            taxes = flows_p['tax_amount'].sum() if not flows_p.empty else 0

            logging.debug(f"  cap_investi: {cap_investi}")
            logging.debug(f"  cap_encours: {cap_encours}")
            logging.debug(f"  int_bruts: {int_bruts}")
            logging.debug(f"  taxes: {taxes}")

            # Calculate Unrealized Gain/Loss and Total Net Gain for platform
            unrealized_gain_loss = 0.0
            if p in ['PEA', 'Assurance_Vie']:
                # For PEA/AV, unrealized gain/loss is market_value - total_invested_via_cash_flows
                invested_via_flows = flows_p[
                    (flows_p['flow_type'] == 'investment') &
                    (flows_p['flow_direction'] == 'out')
                ]['gross_amount'].sum()
                unrealized_gain_loss = cap_encours - invested_via_flows
            else: # Crowdfunding platforms
                # For crowdfunding, it's remaining_capital - invested_amount for active investments
                active_cf_investments = inv_p[inv_p['status'] == 'active']
                unrealized_gain_loss = active_cf_investments['remaining_capital'].sum() - active_cf_investments['invested_amount'].sum()

            total_gain_net_platform = (int_bruts - taxes) + unrealized_gain_loss
            
            # --- Construction robuste des flux pour le TRI par plateforme ---
            flows_tri_platform = pd.DataFrame(columns=['transaction_date', 'gross_amount', 'net_amount', 'flow_direction'])
            
            # 1. Ajouter les flux de trésorerie spécifiques à la plateforme
            if not flows_p.empty:
                flows_tri_platform = pd.concat([flows_tri_platform, flows_p], ignore_index=True)

            # 2. Ajouter les investissements initiaux de cette plateforme
            if not inv_p.empty:
                for _, inv in inv_p.iterrows():
                    is_covered = False
                    if not flows_p.empty:
                        covered_flows = flows_p[
                            (flows_p['investment_id'] == inv['id']) &
                            (flows_p['flow_type'] == 'investment') &
                            (flows_p['flow_direction'] == 'out')
                        ]
                        if not covered_flows.empty:
                            is_covered = True
                    
                    if not is_covered and inv['invested_amount'] > 0 and pd.notna(inv['investment_date']):
                        initial_investment_flow = pd.DataFrame([{
                            'transaction_date': pd.Timestamp(inv['investment_date']),
                            'gross_amount': inv['invested_amount'],
                            'net_amount': inv['invested_amount'],
                            'flow_direction': 'out',
                            'flow_type': 'investment_initial'
                        }])
                        flows_tri_platform = pd.concat([flows_tri_platform, initial_investment_flow], ignore_index=True)

            # 3. Ajouter la valeur actuelle de la plateforme comme flux final
            if cap_encours > 0:
                final_valuation_flow = pd.DataFrame([{
                    'transaction_date': pd.Timestamp(datetime.now()),
                    'gross_amount': cap_encours,
                    'net_amount': cap_encours,
                    'flow_direction': 'in',
                    'flow_type': 'valuation'
                }])
                flows_tri_platform = pd.concat([flows_tri_platform, final_valuation_flow], ignore_index=True)
            
            # S'assurer que les dates sont au bon format et trier
            flows_tri_platform['transaction_date'] = pd.to_datetime(flows_tri_platform['transaction_date'])
            flows_tri_platform = flows_tri_platform.sort_values('transaction_date').reset_index(drop=True)

            logging.debug(f"Flux pour TRI {p} (brut):\n{flows_tri_platform[['transaction_date', 'gross_amount', 'flow_direction']].to_string()}")
            logging.debug(f"Flux pour TRI {p} (net):\n{flows_tri_platform[['transaction_date', 'net_amount', 'flow_direction']].to_string()}")

            tri_brut = self._xirr(self._prepare_flows_for_tri(flows_tri_platform, 'gross_amount'))
            tri_net = self._xirr(self._prepare_flows_for_tri(flows_tri_platform, 'net_amount'))

            # Calcul du capital remboursé et du taux de remboursement par plateforme
            total_invested_platform = inv_p['invested_amount'].sum() if not inv_p.empty else 0
            total_repaid_platform = inv_p['capital_repaid'].sum() if not inv_p.empty else 0
            repayment_rate_platform = (total_repaid_platform / total_invested_platform) * 100 if total_invested_platform > 0 else 0

            # Calcul des métriques de liquidité et de duration
            liquidity_duration_metrics = self.get_liquidity_and_duration_metrics(inv_p)

            details[p] = {
                "capital_investi_encours": (cap_investi, cap_encours),
                "plus_value_realisee_nette": int_bruts - taxes,
                "tri_brut": tri_brut * 100,
                "tri_net": tri_net * 100,
                "interets_bruts_recus": int_bruts,
                "impots_et_frais": taxes,
                "nombre_projets": len(inv_p) if is_cf else len(pos_p),
                "total_invested_platform": total_invested_platform,
                "total_repaid_platform": total_repaid_platform,
                "repayment_rate_platform": repayment_rate_platform,
                "projected_liquidity_6m": liquidity_duration_metrics["projected_liquidity_6m"],
                "projected_liquidity_12m": liquidity_duration_metrics["projected_liquidity_12m"],
                "projected_liquidity_24m": liquidity_duration_metrics["projected_liquidity_24m"],
                "weighted_average_duration": liquidity_duration_metrics["weighted_average_duration"],
                "duration_distribution": liquidity_duration_metrics["duration_distribution"],
                "reinvestment_rate": self.get_reinvestment_rate(flows_p),
                "unrealized_gain_loss": unrealized_gain_loss,
                "total_gain_net_platform": total_gain_net_platform,
            }
            # Calculer maturity_indicator après que details[p] soit entièrement défini
            details[p]["maturity_indicator"] = self.calculate_maturity_indicator(details[p])
        
        return details

    def get_performance_attribution_by_platform(self) -> List[Dict[str, Any]]:
        logging.info("Calcul de l'attribution de performance par plateforme...")
        attribution_data = []

        global_kpis = self.get_global_kpis()
        total_patrimoine = global_kpis.get('patrimoine_total', 0)
        total_apports = global_kpis.get('total_apports', 0)
        global_tri_net = global_kpis.get('tri_global_net', 0) / 100 # Convertir en décimal

        platform_details = self.get_platform_details()

        if total_patrimoine == 0:
            logging.warning("Patrimoine total est zéro, impossible de calculer l'attribution de performance.")
            return []

        for platform, details in platform_details.items():
            platform_tri_net = details.get('tri_net', 0) / 100 # Convertir en décimal
            
            # Utiliser le capital investi pour la pondération
            # Pour PEA/AV, utiliser la valeur de marché actuelle comme proxy pour le capital investi pondéré
            if platform in ['PEA', 'Assurance_Vie']:
                platform_invested_amount = self.positions_df[self.positions_df['platform'] == platform]['market_value'].sum()
            else:
                platform_invested_amount = details.get('capital_investi_encours', (0,0))[0] # Capital investi

            if total_apports > 0:
                # Contribution = (TRI_plateforme - TRI_global) * (Poids_plateforme)
                # Poids_plateforme = Capital_investi_plateforme / Total_apports_globaux
                weight = platform_invested_amount / total_apports
                contribution = (platform_tri_net - global_tri_net) * weight * 100 # En pourcentage
            else:
                contribution = 0.0 # Pas de contribution si pas d'apports

            attribution_data.append({
                "platform": platform,
                "platform_tri_net": platform_tri_net * 100,
                "platform_invested_amount": platform_invested_amount,
                "contribution_to_global_tri": contribution
            })
        
        # Trier par contribution décroissante
        attribution_data = sorted(attribution_data, key=lambda x: x['contribution_to_global_tri'], reverse=True)

        return attribution_data

    def get_performance_attribution_by_asset_class(self) -> List[Dict[str, Any]]:
        logging.info("Calcul de l'attribution de performance par classe d'actifs...")
        attribution_data = []

        global_kpis = self.get_global_kpis()
        total_patrimoine = global_kpis.get('patrimoine_total', 0)
        total_apports = global_kpis.get('total_apports', 0)
        global_tri_net = global_kpis.get('tri_global_net', 0) / 100 # Convertir en décimal

        if total_patrimoine == 0:
            logging.warning("Patrimoine total est zéro, impossible de calculer l'attribution de performance par classe d'actifs.")
            return []

        # Regrouper les investissements par classe d'actifs
        # Utiliser les investissements et les positions pour couvrir toutes les classes
        all_investments = self.investments_df.copy()
        all_positions = self.positions_df.copy()

        # Assurer la colonne asset_class pour les positions (si manquante)
        if 'asset_class' not in all_positions.columns:
            all_positions['asset_class'] = all_positions['platform'].apply(lambda x: 'equity' if x == 'PEA' else 'mixed') # Default for AV

        # Concaténer et calculer les flux pour chaque classe d'actifs
        # C'est une simplification, un calcul de TRI par classe d'actifs serait plus complexe
        # et nécessiterait de regrouper les flux par classe. Pour l'instant, on agrège les montants.
        
        # Créer un DataFrame combiné pour faciliter l'agrégation
        combined_df = pd.DataFrame()

        if not all_investments.empty:
            investments_for_attribution = all_investments[['user_id', 'platform', 'asset_class', 'invested_amount', 'remaining_capital']].copy()
            investments_for_attribution['current_value'] = investments_for_attribution['remaining_capital']
            combined_df = pd.concat([combined_df, investments_for_attribution], ignore_index=True)

        if not all_positions.empty:
            positions_for_attribution = all_positions[['user_id', 'platform', 'asset_class', 'market_value']].copy()
            positions_for_attribution.rename(columns={'market_value': 'current_value'}, inplace=True)
            positions_for_attribution['invested_amount'] = positions_for_attribution['current_value'] # Approximation for weighting
            positions_for_attribution['remaining_capital'] = positions_for_attribution['current_value']
            combined_df = pd.concat([combined_df, positions_for_attribution], ignore_index=True)

        if combined_df.empty:
            return []

        # Calculer le TRI par classe d'actifs (simplifié pour l'exemple)
        # Une approche plus rigoureuse nécessiterait de filtrer les cash_flows par asset_class
        # et de recalculer le TRI pour chaque classe. Ici, on utilise une approximation.
        asset_class_summary = combined_df.groupby('asset_class').agg(
            total_invested=('invested_amount', 'sum'),
            current_value=('current_value', 'sum')
        ).reset_index()

        for _, row in asset_class_summary.iterrows():
            asset_class = row['asset_class']
            total_invested_ac = row['total_invested']
            current_value_ac = row['current_value']

            # Approximation du TRI pour la classe d'actifs
            # Idéalement, il faudrait un TRI réel par classe d'actifs
            if total_invested_ac > 0:
                # Simple return for now, not XIRR
                asset_class_return = (current_value_ac - total_invested_ac) / total_invested_ac
            else:
                asset_class_return = 0.0

            if total_apports > 0:
                weight = total_invested_ac / total_apports
                contribution = (asset_class_return - global_tri_net) * weight * 100 # En pourcentage
            else:
                contribution = 0.0

            attribution_data.append({
                "asset_class": asset_class,
                "asset_class_return": asset_class_return * 100,
                "asset_class_invested_amount": total_invested_ac,
                "contribution_to_global_tri": contribution
            })
        
        # Trier par contribution décroissante
        attribution_data = sorted(attribution_data, key=lambda x: x['contribution_to_global_tri'], reverse=True)

        return attribution_data

    def get_rolling_returns(self, periods: List[int] = [1, 3, 5]) -> Dict[str, Dict[str, float]]:
        logging.info("Calcul des performances glissantes...")
        rolling_returns = {}

        if self.cash_flows_df.empty:
            return {str(p) + "Y": {"start_date": None, "end_date": None, "tri_net": 0.0} for p in periods}

        # Assurer que les dates sont au bon format et trier
        df = self.cash_flows_df.copy()
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        df = df.sort_values('transaction_date').reset_index(drop=True)

        # Ajouter la valorisation actuelle comme flux final pour le calcul du TRI
        global_kpis = self.get_global_kpis()
        patrimoine_total = global_kpis.get('patrimoine_total', 0)
        
        if patrimoine_total > 0:
            final_valuation_flow = pd.DataFrame([
                {
                    'transaction_date': pd.Timestamp(datetime.now()),
                    'gross_amount': patrimoine_total,
                    'net_amount': patrimoine_total,
                    'flow_direction': 'in',
                    'flow_type': 'valuation'
                }
            ])
            df = pd.concat([df, final_valuation_flow], ignore_index=True)
            df = df.sort_values('transaction_date').reset_index(drop=True)

        for period_years in periods:
            end_date = df['transaction_date'].max()
            start_date = end_date - pd.DateOffset(years=period_years)

            # Filtrer les flux pour la période glissante
            period_flows_df = df[(df['transaction_date'] >= start_date) & (df['transaction_date'] <= end_date)]

            if not period_flows_df.empty:
                # S'assurer qu'il y a au moins un flux entrant et un flux sortant (ou une valorisation finale)
                # pour que le TRI soit calculable
                if len(period_flows_df['flow_direction'].unique()) > 1 or \
                   ('valuation' in period_flows_df['flow_type'].values and len(period_flows_df) > 1):
                    
                    tri_net = self._xirr(self._prepare_flows_for_tri(period_flows_df, 'net_amount')) * 100
                else:
                    tri_net = 0.0
            else:
                tri_net = 0.0

            rolling_returns[str(period_years) + "Y"] = {
                "start_date": start_date.strftime('%Y-%m-%d'),
                "end_date": end_date.strftime('%Y-%m-%d'),
                "tri_net": tri_net
            }

        return rolling_returns

    def get_crowdfunding_project_details(self) -> Dict[str, pd.DataFrame]:
        logging.info("Calcul des détails par projet de crowdfunding...")
        project_details = {}
        if self.investments_df.empty or 'platform' not in self.investments_df.columns: return project_details
        cf_platforms = [p for p in self.investments_df['platform'].unique() if p not in ['PEA', 'Assurance_Vie']]
        for p in cf_platforms:
            inv_p = self.investments_df[self.investments_df['platform'] == p]
            project_list = []
            for _, inv in inv_p.iterrows():
                flows_proj = self.cash_flows_df[self.cash_flows_df['investment_id'] == inv['id']] if not self.cash_flows_df.empty else pd.DataFrame()
                flows_tri = flows_proj.copy()
                if inv['remaining_capital'] > 0:
                    final_flow = pd.DataFrame([{'transaction_date': pd.Timestamp(datetime.now()), 'flow_type': 'valuation', 'flow_direction': 'in', 'gross_amount': inv['remaining_capital'], 'net_amount': inv['remaining_capital']}])
                    flows_tri = pd.concat([flows_tri, final_flow], ignore_index=True) if not flows_tri.empty else final_flow
                project_list.append({
                    "Nom du Projet": inv['project_name'], "Montant Investi": inv['invested_amount'], "Statut": inv['status'],
                    "Capital Restant Dû": inv['remaining_capital'], "Intérêts Reçus (Nets)": (flows_proj['interest_amount'].sum() - flows_proj['tax_amount'].sum()) if not flows_proj.empty else 0,
                    "TRI du Projet (%)": self._xirr(self._prepare_flows_for_tri(flows_tri, 'net_amount')) * 100
                })
            project_details[p] = pd.DataFrame(project_list)
        return project_details

    def get_periodic_performance(self) -> Dict[str, pd.DataFrame]:
        logging.info("Calcul de la performance périodique...")
        if self.cash_flows_df.empty: 
            return {"monthly": pd.DataFrame(columns=['Period', 'net_gain'], index=pd.DatetimeIndex([])), 
                    "annual": pd.DataFrame(columns=['Period', 'net_gain'], index=pd.DatetimeIndex([]))}
        
        df = self.cash_flows_df.copy()
        
        # Assurer que la colonne 'transaction_date' est de type datetime et gérer les erreurs
        df['transaction_date'] = pd.to_datetime(df['transaction_date'], errors='coerce')
        df.dropna(subset=['transaction_date'], inplace=True) # Supprimer les lignes avec dates invalides

        if df.empty: 
            return {"monthly": pd.DataFrame(columns=['Period', 'net_gain'], index=pd.DatetimeIndex([])), 
                    "annual": pd.DataFrame(columns=['Period', 'net_gain'], index=pd.DatetimeIndex([]))}

        df['net_gain'] = df['interest_amount'].fillna(0) - df['tax_amount'].fillna(0)
        fee_flows = df['flow_type'] == 'fee'
        df.loc[fee_flows, 'net_gain'] = -df.loc[fee_flows, 'gross_amount'].fillna(0)
        
        monthly_perf = df.set_index('transaction_date').resample('M')['net_gain'].sum()
        monthly_perf = monthly_perf.to_frame(name='net_gain') # Convertir Series en DataFrame
        monthly_perf['Period'] = monthly_perf.index.strftime('%Y-%m') # Ajouter la colonne Period pour l'affichage

        annual_perf = df.set_index('transaction_date').resample('Y')['net_gain'].sum()
        annual_perf = annual_perf.to_frame(name='net_gain') # Convertir Series en DataFrame
        annual_perf['Period'] = annual_perf.index.strftime('%Y') # Ajouter la colonne Period pour l'affichage

        # S'assurer que l'index est DatetimeIndex avant de retourner
        monthly_perf.index = pd.to_datetime(monthly_perf.index)
        annual_perf.index = pd.to_datetime(annual_perf.index)
        
        return {"monthly": monthly_perf, "annual": annual_perf}

    def get_charts_data(self) -> Dict[str, Any]:
        logging.info("Préparation des données pour les graphiques...")
        total_encours_cf = self.investments_df['remaining_capital'].sum() if 'remaining_capital' in self.investments_df.columns else 0
        pea_av_value = self.positions_df['market_value'].sum() if 'market_value' in self.positions_df.columns else 0
        total_liquidity = 0
        if not self.liquidity_df.empty and 'balance_date' in self.liquidity_df.columns:
            total_liquidity = self.liquidity_df.sort_values('balance_date').drop_duplicates('platform', keep='last')['amount'].sum()
        repartition = {"Bourse (PEA/AV)": pea_av_value, "Crowdfunding": total_encours_cf, "Liquidités": total_liquidity}

        # --- Préparation des Séries Temporelles ---
        empty_ts = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
        apports_cumules = empty_ts.copy()
        patrimoine_total_evolution = empty_ts.copy()
        benchmark_data = empty_ts.copy()

        df_cash_flows_processed = self.cash_flows_df.copy()
        if df_cash_flows_processed.empty or 'transaction_date' not in df_cash_flows_processed.columns:
            return {"repartition_data": repartition, "evolution_data": {"apports_cumules": apports_cumules, "patrimoine_total_evolution": patrimoine_total_evolution, "benchmark": benchmark_data}}

        df_cash_flows_processed['transaction_date'] = pd.to_datetime(df_cash_flows_processed['transaction_date'], errors='coerce')
        df_cash_flows_processed.dropna(subset=['transaction_date'], inplace=True)

        if df_cash_flows_processed.empty:
            return {"repartition_data": repartition, "evolution_data": {"apports_cumules": apports_cumules, "patrimoine_total_evolution": patrimoine_total_evolution, "benchmark": benchmark_data}}

        # --- Calcul des Apports Cumulés ---
        apports_df = df_cash_flows_processed[df_cash_flows_processed['flow_type'] == 'deposit']
        if not apports_df.empty:
            daily_apports = apports_df.set_index('transaction_date')['gross_amount'].resample('D').sum()
            apports_cumules = daily_apports.cumsum().ffill()

        # --- Calcul de l'Évolution du Patrimoine ---
        df_temp = df_cash_flows_processed.copy()
        df_temp['signed_net_amount'] = df_temp.apply(
            lambda row: row['net_amount'] if row['flow_direction'] == 'in' else -row['net_amount'], axis=1
        )
        daily_net_flows = df_temp.set_index('transaction_date')['signed_net_amount'].resample('D').sum()
        patrimoine_total_evolution = daily_net_flows.cumsum().ffill()
        logging.debug(f"[DEBUG] Patrimoine total evolution après cumsum et ffill:\n{patrimoine_total_evolution.head()}\n{patrimoine_total_evolution.tail()}")
        logging.debug(f"[DEBUG] Patrimoine total evolution info:\n{patrimoine_total_evolution.info()}")
        logging.debug(f"[DEBUG] Patrimoine total evolution index duplicated: {patrimoine_total_evolution.index.duplicated().any()}")

        # --- Ajout de la valeur actuelle et fiabilisation de l'index ---
        today = pd.Timestamp(datetime.now().date())
        current_total = self.get_global_kpis()['patrimoine_total']
        logging.debug(f"[DEBUG] Valeur actuelle du patrimoine: {current_total} à la date: {today}")

        # Créer une série pour la valeur actuelle avec la date d'aujourd'hui
        current_day_series = pd.Series([current_total], index=[today])
        logging.debug(f"[DEBUG] Série du jour actuel:\n{current_day_series}")

        # Concaténer la série d'évolution avec la valeur du jour actuel
        # et résoudre les doublons en prenant la dernière valeur pour chaque jour
        patrimoine_total_evolution = pd.concat([patrimoine_total_evolution, current_day_series])
        logging.debug(f"[DEBUG] Patrimoine total evolution après concat:\n{patrimoine_total_evolution.head()}\n{patrimoine_total_evolution.tail()}")
        logging.debug(f"[DEBUG] Patrimoine total evolution index duplicated après concat: {patrimoine_total_evolution.index.duplicated().any()}")

        patrimoine_total_evolution = patrimoine_total_evolution.groupby(level=0).last()
        logging.debug(f"[DEBUG] Patrimoine total evolution après groupby.last():\n{patrimoine_total_evolution.head()}\n{patrimoine_total_evolution.tail()}")
        logging.debug(f"[DEBUG] Patrimoine total evolution index duplicated après groupby.last(): {patrimoine_total_evolution.index.duplicated().any()}")

        # Re-sampler pour assurer la continuité de l'index quotidien et remplir les valeurs manquantes
        patrimoine_total_evolution = patrimoine_total_evolution.resample('D').ffill()
        logging.debug(f"[DEBUG] Patrimoine total evolution final après resample.ffill():\n{patrimoine_total_evolution.head()}\n{patrimoine_total_evolution.tail()}")
        logging.debug(f"[DEBUG] Patrimoine total evolution final info:\n{patrimoine_total_evolution.info()}")
        logging.debug(f"[DEBUG] Patrimoine total evolution final index duplicated: {patrimoine_total_evolution.index.duplicated().any()}")

        # --- Normalisation du Patrimoine à 100 ---
        if not patrimoine_total_evolution.empty and not patrimoine_total_evolution.isnull().all():
            first_patrimoine_value = patrimoine_total_evolution.iloc[0]
            if first_patrimoine_value != 0:
                patrimoine_total_evolution = (patrimoine_total_evolution / first_patrimoine_value) * 100
            else:
                logging.warning("La première valeur du patrimoine est zéro, impossible de normaliser à 100.")
                patrimoine_total_evolution = empty_ts.copy()
        else:
            logging.warning("Patrimoine total evolution est vide ou contient uniquement des NaN après normalisation initiale. Impossible de normaliser à 100.")
            patrimoine_total_evolution = empty_ts.copy()


        # --- Récupération et Alignement du Benchmark ---
        logging.debug(f"[DEBUG] Début récupération et alignement benchmark. Patrimoine total evolution empty: {patrimoine_total_evolution.empty}, isnull.all: {patrimoine_total_evolution.isnull().all()}")
        if not patrimoine_total_evolution.empty and not patrimoine_total_evolution.isnull().all():
            start_date = patrimoine_total_evolution.index.min()
            end_date = patrimoine_total_evolution.index.max()
            logging.debug(f"[DEBUG] Dates pour benchmark: start={start_date}, end={end_date}")
            raw_benchmark = self._get_benchmark_data(start_date, end_date)
            logging.debug(f"[DEBUG] Raw benchmark data head:\n{raw_benchmark.head()}")
            logging.debug(f"[DEBUG] Raw benchmark data tail:\n{raw_benchmark.tail()}")
            logging.debug(f"[DEBUG] Raw benchmark data info:\n{raw_benchmark.info()}")

            if not raw_benchmark.empty:
                benchmark_data = raw_benchmark.reindex(patrimoine_total_evolution.index).interpolate(method='linear')
                logging.debug(f"[DEBUG] Benchmark data après reindex et interpolate:\n{benchmark_data.head()}\n{benchmark_data.tail()}")
                logging.debug(f"[DEBUG] Benchmark data info après reindex et interpolate:\n{benchmark_data.info()}")

                # --- Normalisation du Benchmark à 100 ---
                if not benchmark_data.empty and not benchmark_data['CW8.PA'].isnull().all().item():
                    first_benchmark_value = benchmark_data['CW8.PA'].iloc[0]
                    if first_benchmark_value != 0:
                        benchmark_data['CW8.PA'] = (benchmark_data['CW8.PA'] / first_benchmark_value) * 100
                    else:
                        logging.warning("La première valeur du benchmark est zéro, impossible de normaliser à 100.")
                        benchmark_data = empty_ts.copy()
                else:
                    logging.warning("Données benchmark vides ou contiennent uniquement des NaN après normalisation initiale. Impossible de normaliser à 100.")
                    benchmark_data = empty_ts.copy()
            else:
                logging.warning("Données benchmark brutes vides. Benchmark non calculé.")
        else:
            logging.warning("Patrimoine total evolution est vide ou contient uniquement des NaN. Benchmark non calculé.")

        # --- Vérification Finale ---
        logging.debug(f"[DEBUG] Final apports_cumules empty: {apports_cumules.empty}, type: {type(apports_cumules)}")
        logging.debug(f"[DEBUG] Final patrimoine_total_evolution empty: {patrimoine_total_evolution.empty}, type: {type(patrimoine_total_evolution)}")
        logging.debug(f"[DEBUG] Final benchmark empty: {benchmark_data.empty}, type: {type(benchmark_data)}")

        final_evolution_data = {
            "apports_cumules": apports_cumules,
            "patrimoine_total_evolution": patrimoine_total_evolution,
            "benchmark": benchmark_data
        }

        return {"repartition_data": repartition, "evolution_data": final_evolution_data}

    def calculate_herfindahl_index(self) -> float:
        """
        Calcule l'indice de Herfindahl-Hirschman (HHI) pour la concentration des investissements
        par émetteur (company_name).
        L'HHI est calculé comme la somme des carrés des parts de marché (ici, parts d'investissement)
        de chaque émetteur.
        Un HHI inférieur à 1500 indique une faible concentration, entre 1500 et 2500 une concentration modérée,
        et supérieur à 2500 une forte concentration.
        """
        logging.info("Calcul de l'indice de Herfindahl...")
        if self.investments_df.empty or 'company_name' not in self.investments_df.columns or 'invested_amount' not in self.investments_df.columns:
            logging.warning("Données d'investissement insuffisantes pour calculer l'indice de Herfindahl.")
            return 0.0

        # Filtrer les investissements avec un montant investi > 0
        active_investments = self.investments_df[self.investments_df['invested_amount'] > 0].copy()

        if active_investments.empty:
            logging.warning("Aucun investissement actif avec un montant investi > 0 pour calculer l'indice de Herfindahl.")
            return 0.0

        # Calculer le montant total investi
        total_invested_amount = active_investments['invested_amount'].sum()
        
        if total_invested_amount == 0:
            logging.warning("Le montant total investi est zéro, impossible de calculer l'indice de Herfindahl.")
            return 0.0

        # Calculer la part de chaque émetteur
        company_investments = active_investments.groupby('company_name')['invested_amount'].sum().reset_index()
        company_investments['share'] = company_investments['invested_amount'] / total_invested_amount

        # Calculer l'indice de Herfindahl
        hhi = (company_investments['share'] ** 2).sum() * 10000 # Multiplier par 10000 pour avoir l'échelle standard

        logging.info(f"Indice de Herfindahl calculé : {hhi:.2f}")
        return hhi

    def get_liquidity_and_duration_metrics(self, inv_p: pd.DataFrame) -> Dict[str, Any]:
        """
        Calcule les projections de liquidité et la duration moyenne pondérée pour une plateforme donnée.
        """
        metrics = {
            "projected_liquidity_6m": 0.0,
            "projected_liquidity_12m": 0.0,
            "projected_liquidity_24m": 0.0,
            "weighted_average_duration": 0.0,
            "duration_distribution": {"<6m": 0.0, "6-12m": 0.0, ">12m": 0.0}
        }

        if inv_p.empty: return metrics

        # --- Projections de Liquidité (2.2) ---
        today_timestamp = pd.Timestamp(datetime.now().date()) # Convertir en Timestamp
        future_investments = inv_p[
            (inv_p['status'] == 'active') &
            (inv_p['expected_end_date'].notna())
        ].copy()
        
        if not future_investments.empty:
            future_investments['expected_end_date'] = pd.to_datetime(future_investments['expected_end_date'])
            
            # Filtrer les investissements dont la date de fin est supérieure ou égale à aujourd'hui
            future_investments = future_investments[future_investments['expected_end_date'] >= today_timestamp]

            # Calcul des projections
            end_6m = today_timestamp + pd.DateOffset(months=6)
            end_12m = today_timestamp + pd.DateOffset(months=12)
            end_24m = today_timestamp + pd.DateOffset(months=24)

            metrics["projected_liquidity_6m"] = future_investments[
                future_investments['expected_end_date'] <= end_6m
            ]['remaining_capital'].sum()

            metrics["projected_liquidity_12m"] = future_investments[
                future_investments['expected_end_date'] <= end_12m
            ]['remaining_capital'].sum()

            metrics["projected_liquidity_24m"] = future_investments[
                future_investments['expected_end_date'] <= end_24m
            ]['remaining_capital'].sum()

        # --- Duration Moyenne Pondérée et Répartition par Échéance (2.3) ---
        duration_investments = inv_p[
            (inv_p['duration_months'].notna()) &
            (inv_p['invested_amount'] > 0)
        ].copy()

        if not duration_investments.empty:
            # Duration moyenne pondérée
            total_invested_for_duration = duration_investments['invested_amount'].sum()
            if total_invested_for_duration > 0:
                metrics["weighted_average_duration"] = (
                    (duration_investments['duration_months'] * duration_investments['invested_amount']).sum() /
                    total_invested_for_duration
                )
            
            # Répartition par échéance
            total_investments_count = len(duration_investments)
            if total_investments_count > 0:
                metrics["duration_distribution"]["<6m"] = (
                    len(duration_investments[duration_investments['duration_months'] < 6]) /
                    total_investments_count
                ) * 100
                metrics["duration_distribution"]["6-12m"] = (
                    len(duration_investments[
                        (duration_investments['duration_months'] >= 6) &
                        (duration_investments['duration_months'] <= 12)
                    ]) / total_investments_count
                ) * 100
                metrics["duration_distribution"][">12m"] = (
                    len(duration_investments[duration_investments['duration_months'] > 12]) /
                    total_investments_count
                ) * 100

        return metrics

    def get_reinvestment_rate(self, flows_p: pd.DataFrame) -> float:
        """
        Calcule le taux de réinvestissement pour une plateforme donnée.
        Taux de réinvestissement = (Nouveaux investissements) / (Capital remboursé + Intérêts/Dividendes reçus)
        """
        logging.info("Calcul du taux de réinvestissement...")
        if flows_p.empty: return 0.0

        # Capital remboursé + Intérêts/Dividendes reçus
        capital_returned = flows_p[
            flows_p['flow_type'].isin(['repayment', 'interest', 'dividend']) &
            (flows_p['flow_direction'] == 'in')
        ]['gross_amount'].sum()

        # Nouveaux investissements
        new_investments = flows_p[
            (flows_p['flow_type'] == 'investment') &
            (flows_p['flow_direction'] == 'out')
        ]['gross_amount'].sum()

        if capital_returned > 0:
            reinvestment_rate = (new_investments / capital_returned) * 100
        else:
            reinvestment_rate = 0.0

        return reinvestment_rate

    def calculate_maturity_indicator(self, platform_details: Dict[str, Any]) -> float:
        """
        Calcule un indicateur composite de maturité du portefeuille pour une plateforme.
        Un score plus élevé indique un portefeuille plus 'jeune' et dynamique.
        """
        logging.info("Calcul de l'indicateur de maturité...")

        # Récupération des métriques existantes
        repayment_rate = platform_details.get("repayment_rate_platform", 0.0)
        projected_liquidity_6m = platform_details.get("projected_liquidity_6m", 0.0)
        weighted_average_duration = platform_details.get("weighted_average_duration", 0.0)
        reinvestment_rate = platform_details.get("reinvestment_rate", 0.0)
        cap_encours = platform_details.get("capital_investi_encours", (0.0, 0.0))[1] # Le deuxième élément du tuple

        # Normalisation et pondération des scores (les poids peuvent être ajustés)
        # Score de Liquidité (0-100)
        liquidity_score = (projected_liquidity_6m / cap_encours) * 100 if cap_encours > 0 else 0

        # Score de Duration (0-100, plus la duration est faible, plus le score est élevé)
        # Assumons une duration max de 60 mois pour la normalisation
        MAX_DURATION_MONTHS = 60 
        duration_score = (1 - (weighted_average_duration / MAX_DURATION_MONTHS)) * 100 if weighted_average_duration > 0 else 0
        duration_score = max(0, min(100, duration_score)) # S'assurer que le score est entre 0 et 100

        # Score de Réinvestissement (0-100)
        reinvestment_score = min(100, reinvestment_rate) # Capper à 100% si > 100

        # Score de Remboursement (0-100)
        repayment_score = min(100, repayment_rate) # Capper à 100% si > 100

        # Indicateur composite (moyenne des scores)
        maturity_indicator = (liquidity_score + duration_score + reinvestment_score + repayment_score) / 4
        maturity_indicator = round(maturity_indicator, 2)

        logging.info(f"Indicateur de maturité calculé : {maturity_indicator:.2f}")
        return maturity_indicator

    def analyze_tax_optimization_of_flows(self) -> Dict[str, Any]:
        """
        Analyse les flux de trésorerie pour identifier les opportunités d'optimisation fiscale.
        """
        logging.info("Analyse de l'optimisation fiscale des flux...")
        
        if self.cash_flows_df.empty: 
            return {
                "total_deposits": 0.0,
                "total_reinvestments": 0.0,
                "total_taxes_paid": 0.0,
                "tax_optimization_insights": "Aucun flux de trésorerie pour l'analyse fiscale."
            }

        # Convertir la colonne 'transaction_date' en datetime si ce n'est pas déjà fait
        self.cash_flows_df['transaction_date'] = pd.to_datetime(self.cash_flows_df['transaction_date'])

        # Flux de dépôts (argent frais entrant)
        deposits = self.cash_flows_df[
            (self.cash_flows_df['flow_type'] == 'deposit') &
            (self.cash_flows_df['flow_direction'] == 'in')
        ]
        total_deposits = deposits['gross_amount'].sum()

        # Flux de réinvestissements (argent sortant pour de nouveaux investissements)
        # On considère ici les flux de type 'investment' qui sont des sorties
        reinvestments = self.cash_flows_df[
            (self.cash_flows_df['flow_type'] == 'investment') &
            (self.cash_flows_df['flow_direction'] == 'out')
        ]
        total_reinvestments = reinvestments['gross_amount'].sum()

        # Taxes payées (flux de type 'tax' ou 'fee' qui sont des sorties, ou tax_amount dans les remboursements)
        taxes_from_flows = self.cash_flows_df[
            (self.cash_flows_df['flow_type'] == 'tax') &
            (self.cash_flows_df['flow_direction'] == 'out')
        ]['gross_amount'].sum()
        
        fees_from_flows = self.cash_flows_df[
            (self.cash_flows_df['flow_type'] == 'fee') &
            (self.cash_flows_df['flow_direction'] == 'out')
        ]['gross_amount'].sum()

        # Somme des tax_amount dans tous les flux (pour couvrir les taxes prélevées sur les intérêts/dividendes)
        taxes_from_amounts = self.cash_flows_df['tax_amount'].sum()

        total_taxes_paid = taxes_from_flows + fees_from_flows + taxes_from_amounts

        # Insights d'optimisation (exemples basés sur des règles simples)
        insights = []
        if total_deposits > 0 and total_reinvestments > 0:
            if (total_reinvestments / total_deposits) > 0.5: # Si plus de 50% des dépôts sont réinvestis
                insights.append("Vous avez une bonne dynamique de réinvestissement. Considérez l'utilisation d'enveloppes fiscales (PEA, Assurance Vie) pour optimiser la fiscalité sur le long terme.")
            else:
                insights.append("Votre taux de réinvestissement est modéré. Explorez les opportunités de réinvestissement pour maximiser l'effet boule de neige et potentiellement bénéficier d'avantages fiscaux.")
        
        if total_taxes_paid > 0:
            insights.append(f"Un total de {total_taxes_paid:.2f}€ de taxes et frais a été payé. Une analyse détaillée par type d'investissement pourrait révéler des pistes d'optimisation (ex: arbitrage PEA après 5 ans).")

        if not insights: # Si aucune insight spécifique n'est générée
            insights.append("Aucune recommandation fiscale spécifique identifiée pour le moment. Continuez à suivre vos flux.")

        return {
            "total_deposits": total_deposits,
            "total_reinvestments": total_reinvestments,
            "total_taxes_paid": total_taxes_paid,
            "tax_optimization_insights": " ".join(insights)
        }

    def get_flow_contribution_breakdown(self) -> Dict[str, pd.DataFrame]:
        logging.info("Calcul de la répartition des flux par type...")
        if self.cash_flows_df.empty:
            return {"revenues": pd.DataFrame(), "expenses": pd.DataFrame()}

        df = self.cash_flows_df.copy()
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])

        # Revenus (flux entrants)
        revenues_df = df[df['flow_direction'] == 'in']
        revenues_breakdown = revenues_df.groupby('flow_type')['gross_amount'].sum().reset_index()
        revenues_breakdown.rename(columns={'gross_amount': 'amount'}, inplace=True)
        revenues_breakdown['percentage'] = (revenues_breakdown['amount'] / revenues_breakdown['amount'].sum()) * 100

        # Dépenses (flux sortants)
        expenses_df = df[df['flow_direction'] == 'out']
        expenses_breakdown = expenses_df.groupby('flow_type')['gross_amount'].sum().reset_index()
        expenses_breakdown.rename(columns={'gross_amount': 'amount'}, inplace=True)
        expenses_breakdown['percentage'] = (expenses_breakdown['amount'] / expenses_breakdown['amount'].sum()) * 100

        return {
            "revenues": revenues_breakdown,
            "expenses": expenses_breakdown
        }

    def get_projected_liquidity_timeline(self, num_months: int = 24) -> Dict[str, pd.DataFrame]:
        logging.info(f"Calcul des projections de liquidité sur {num_months} mois...")
        
        projected_flows = []
        today = pd.Timestamp(datetime.now().date())

        # Projections basées sur les investissements actifs avec expected_end_date
        active_investments = self.investments_df[
            (self.investments_df['status'] == 'active') &
            (self.investments_df['expected_end_date'].notna())
        ].copy()

        if not active_investments.empty:
            active_investments['expected_end_date'] = pd.to_datetime(active_investments['expected_end_date'])
            
            # Filtrer les investissements dont la date de fin est dans le futur proche
            future_investments = active_investments[active_investments['expected_end_date'] > today]

            for _, inv in future_investments.iterrows():
                # Simplification: Assumer que le remaining_capital est remboursé à expected_end_date
                # Une logique plus complexe pourrait distribuer les remboursements mensuels
                if inv['remaining_capital'] > 0:
                    projected_flows.append({
                        'date': inv['expected_end_date'],
                        'platform': inv['platform'],
                        'amount': inv['remaining_capital'],
                        'type': 'Remboursement Capital'
                    })
                # Si monthly_payment est disponible, on pourrait projeter les intérêts aussi
                # Pour l'instant, on se concentre sur le capital pour la liquidité

        # Convertir en DataFrame
        if not projected_flows:
            return {"total": pd.DataFrame(), "by_platform": pd.DataFrame()}

        df_projected = pd.DataFrame(projected_flows)
        df_projected['date'] = pd.to_datetime(df_projected['date'])
        df_projected = df_projected.sort_values('date')

        # Agréger par mois
        df_projected['month'] = df_projected['date'].dt.to_period('M')
        
        # Total par mois
        total_monthly_projection = df_projected.groupby('month')['amount'].sum().reset_index()
        total_monthly_projection['month'] = total_monthly_projection['month'].dt.to_timestamp()
        total_monthly_projection.rename(columns={'amount': 'projected_amount'}, inplace=True)

        # Par plateforme et par mois
        platform_monthly_projection = df_projected.groupby(['month', 'platform'])['amount'].sum().unstack(fill_value=0).reset_index()
        platform_monthly_projection['month'] = platform_monthly_projection['month'].dt.to_timestamp()

        # Filtrer pour les num_months prochains mois
        end_date_filter = today + pd.DateOffset(months=num_months)
        total_monthly_projection = total_monthly_projection[total_monthly_projection['month'] <= end_date_filter]
        platform_monthly_projection = platform_monthly_projection[platform_monthly_projection['month'] <= end_date_filter]

        return {
            "total": total_monthly_projection,
            "by_platform": platform_monthly_projection
        }

    def get_volatility_and_drawdown(self) -> Dict[str, Any]:
        logging.info("Calcul de la volatilité et du drawdown...")
        metrics = {
            "global_annualized_volatility": 0.0,
            "global_max_drawdown": 0.0,
            "drawdown_series": pd.Series(dtype=float)
        }

        charts_data = self.get_charts_data()
        patrimoine_evolution = charts_data['evolution_data']['patrimoine_total_evolution']

        if patrimoine_evolution.empty or len(patrimoine_evolution) < 2:
            logging.warning("Données d'évolution du patrimoine insuffisantes pour calculer la volatilité et le drawdown.")
            return metrics

        # Calcul des rendements quotidiens
        returns = patrimoine_evolution.pct_change().dropna()

        if returns.empty:
            logging.warning("Rendements quotidiens non calculables.")
            return metrics

        # Volatilité annualisée (en supposant 252 jours de trading par an)
        annualized_volatility = returns.std() * (252**0.5) * 100
        metrics["global_annualized_volatility"] = annualized_volatility

        # Calcul du Drawdown
        # 1. Calculer la série des pics (valeur maximale atteinte jusqu'à ce jour)
        peak = patrimoine_evolution.expanding(min_periods=1).max()
        # 2. Calculer le drawdown (pourcentage de chute par rapport au pic)
        drawdown = (patrimoine_evolution - peak) / peak * 100
        # 3. Trouver le drawdown maximum
        max_drawdown = drawdown.min()

        metrics["global_max_drawdown"] = max_drawdown
        metrics["drawdown_series"] = drawdown

        return metrics

    def get_delayed_and_defaulted_projects(self) -> pd.DataFrame:
        logging.info("Récupération des projets en retard ou en défaut...")
        if self.investments_df.empty:
            return pd.DataFrame()

        # Filtrer les investissements dont le statut est 'delayed' ou 'defaulted'
        delayed_defaulted_projects = self.investments_df[
            self.investments_df['status'].isin(['delayed', 'defaulted'])
        ].copy()

        if not delayed_defaulted_projects.empty:
            # Sélectionner les colonnes pertinentes pour l'affichage
            delayed_defaulted_projects = delayed_defaulted_projects[[
                'platform', 'project_name', 'company_name', 'status', 
                'invested_amount', 'remaining_capital', 'expected_end_date', 'actual_end_date'
            ]]
            # Trier pour une meilleure lisibilité
            delayed_defaulted_projects = delayed_defaulted_projects.sort_values(by=['status', 'expected_end_date'], ascending=[True, True])
        
        return delayed_defaulted_projects