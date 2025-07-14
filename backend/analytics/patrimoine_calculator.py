# ===== backend/analytics/patrimoine_calculator.py - MOTEUR DE CALCUL DU DASHBOARD (v1.9.5 - CORRECTION TRI & BENCHMARK) =====
import logging
import pandas as pd
from typing import Dict, List, Tuple, Any
from datetime import datetime
from scipy.optimize import fsolve

import warnings
import yfinance as yf

warnings.filterwarnings('ignore', category=FutureWarning)

# Configuration du logging
# Configuration du logging
# logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - [%(funcName)s] %(message)s') # Niveau DEBUG pour plus de détails

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
            self.cash_flows_df.dropna(subset=['transaction_date'], inplace=True)
        
        if not self.investments_df.empty:
            for col in ['investment_date', 'signature_date', 'expected_end_date', 'actual_end_date']:
                if col in self.investments_df.columns:
                    self.investments_df[col] = pd.to_datetime(self.investments_df[col], errors='coerce')
                    self.investments_df.dropna(subset=[col], inplace=True)
        logging.info("Données chargées.")
        logging.debug(f"Investments DF head:\n{self.investments_df.head()}")
        logging.debug(f"Cash Flows DF head:\n{self.cash_flows_df.head()}")
        logging.debug(f"Positions DF head:\n{self.positions_df.head()}")
        logging.debug(f"Liquidity DF head:\n{self.liquidity_df.head()}")

    def _get_benchmark_data(self, start_date: datetime, end_date: datetime, ticker: str = "IWDA.AS") -> pd.Series:
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
            if 'Adj Close' not in data.columns:
                logging.error(f"La colonne 'Adj Close' est manquante dans les données récupérées pour {ticker}. Colonnes disponibles: {data.columns.tolist()}")
                return pd.Series(dtype=float)
            benchmark_series = data['Adj Close'].dropna()
            
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
        logging.debug(f"_xirr appelé avec {len(cash_flows)} flux: {cash_flows}")
        if len(cash_flows) < 2: 
            logging.debug("_xirr: Moins de 2 flux, retourne 0.0")
            return 0.0
        try:
            df = pd.DataFrame(cash_flows, columns=['date', 'amount'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            if df['date'].nunique() <= 1: 
                logging.debug("_xirr: Toutes les dates sont identiques, retourne 0.0")
                return 0.0
            base_date = df['date'].iloc[0]
            df['days'] = (df['date'] - base_date).dt.days
            def npv_function(rate): return (df['amount'] / ((1 + rate) ** (df['days'] / 365.25))).sum()
            
            # --- Tentative avec plusieurs points de départ pour fsolve ---
            initial_guesses = [0.1, 0.0, 0.5, -0.1, 1.0, 0.05, -0.05] # Essayer différentes valeurs
            rate = 0.0
            converged = False
            for guess in initial_guesses:
                try:
                    solution, _, convergence, _ = fsolve(npv_function, guess, full_output=True)
                    if convergence == 1:
                        rate = solution[0]
                        converged = True
                        logging.debug(f"_xirr: Convergence réussie avec guess {guess}, TRI: {rate * 100:.2f}%")
                        break
                except Exception:
                    pass # Ignorer les erreurs de fsolve pour essayer d'autres guesses
            
            if converged:
                # On garde une plage raisonnable pour éviter des TRI aberrants
                return rate if -0.99 <= rate <= 5.0 else 0.0 
            logging.debug("_xirr: Pas de convergence après plusieurs tentatives, retourne 0.0")
            return 0.0
        except Exception as e:
            logging.error(f"_xirr: Erreur de calcul XIRR: {e}")
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
        pea_av_value = self.positions_df['market_value'].sum() if 'market_value' in self.positions_df.columns else 0
        total_liquidity = 0
        if not self.liquidity_df.empty and 'balance_date' in self.liquidity_df.columns:
            latest_liquidity = self.liquidity_df.sort_values('balance_date').drop_duplicates('platform', keep='last')
            total_liquidity = latest_liquidity['amount'].sum()

        patrimoine_total = total_encours_cf + pea_av_value + total_liquidity
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
            is_cf = p not in ['PEA', 'Assurance_Vie']
            inv_p = self.investments_df[self.investments_df['platform'] == p] if not self.investments_df.empty else pd.DataFrame()
            flows_p = self.cash_flows_df[self.cash_flows_df['platform'] == p] if not self.cash_flows_df.empty else pd.DataFrame()
            pos_p = self.positions_df[self.positions_df['platform'] == p] if not self.positions_df.empty else pd.DataFrame()
            cap_investi = inv_p['invested_amount'].sum() if is_cf and not inv_p.empty else (flows_p[flows_p['flow_type'] == 'deposit']['gross_amount'].sum() if not flows_p.empty else 0)
            cap_encours = inv_p['remaining_capital'].sum() if is_cf and not inv_p.empty else (pos_p['market_value'].sum() if not pos_p.empty else 0)
            int_bruts = flows_p[flows_p['flow_type'].isin(['interest', 'dividend', 'repayment'])]['interest_amount'].sum() if not flows_p.empty else 0
            taxes = flows_p['tax_amount'].sum() if not flows_p.empty else 0
            
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
            }
            # Calculer maturity_indicator après que details[p] soit entièrement défini
            details[p]["maturity_indicator"] = self.calculate_maturity_indicator(details[p])
        
        return details

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
        if not self.liquidity_df.empty and 'balance_date' in self.liquidity_df.columns: total_liquidity = self.liquidity_df.sort_values('balance_date').drop_duplicates('platform', keep='last')['amount'].sum()
        repartition = {"Bourse (PEA/AV)": pea_av_value, "Crowdfunding": total_encours_cf, "Liquidités": total_liquidity}

        # Assurer que cash_flows_df a une colonne 'transaction_date' de type datetime
        df_cash_flows_processed = self.cash_flows_df.copy()
        if not df_cash_flows_processed.empty and 'transaction_date' in df_cash_flows_processed.columns:
            df_cash_flows_processed['transaction_date'] = pd.to_datetime(df_cash_flows_processed['transaction_date'], errors='coerce')
            df_cash_flows_processed.dropna(subset=['transaction_date'], inplace=True) # Supprimer les lignes avec dates invalides

        apports_cumules = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
        if not df_cash_flows_processed.empty:
            apports_df = df_cash_flows_processed[df_cash_flows_processed['flow_type'] == 'deposit'].copy()
            if not apports_df.empty:
                apports_cumules = apports_df.set_index('transaction_date')['gross_amount'].resample('D').sum().cumsum().ffill()
                # Ensure apports_cumules index is DatetimeIndex (already done by resample, but explicit for safety)
                apports_cumules.index = pd.to_datetime(apports_cumules.index)
        
        # --- Calcul du patrimoine total pour le graphique d'évolution ---
        patrimoine_total_evolution = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
        if not df_cash_flows_processed.empty:
            df_temp = df_cash_flows_processed.copy()
            df_temp['signed_net_amount'] = df_temp.apply(
                lambda row: row['net_amount'] if row['flow_direction'] == 'in' else -row['net_amount'], axis=1
            )
            patrimoine_total_evolution = df_temp.set_index('transaction_date')['signed_net_amount'].resample('D').sum().cumsum().ffill()
            # S'assurer explicitement que l'index est un DatetimeIndex ici
            patrimoine_total_evolution.index = pd.to_datetime(patrimoine_total_evolution.index)

            # Ajouter la valeur actuelle du patrimoine à la dernière date
            if not patrimoine_total_evolution.empty:
                # Utilise pd.Timestamp pour la cohérence avec l'index
                patrimoine_total_evolution.loc[pd.Timestamp(datetime.now().date())] = self.get_global_kpis()['patrimoine_total'] 
                patrimoine_total_evolution = patrimoine_total_evolution.resample('D').ffill()

        # --- Récupération et alignement des données benchmark ---
        benchmark_data = pd.Series(dtype=float, index=pd.DatetimeIndex([]))
        if not patrimoine_total_evolution.empty: # Récupérer le benchmark seulement si des données de portefeuille existent
            start_date = patrimoine_total_evolution.index.min()
            end_date = patrimoine_total_evolution.index.max()
            benchmark_data = self._get_benchmark_data(start_date, end_date)
            
            # Aligner l'index du benchmark avec celui du patrimoine total
            if not benchmark_data.empty and isinstance(benchmark_data.index, pd.DatetimeIndex):
                # Re-échantillonner le benchmark pour avoir les mêmes dates que patrimoine_total_evolution
                # Utiliser interpolate(method='linear') pour remplir les jours manquants
                benchmark_data = benchmark_data.reindex(patrimoine_total_evolution.index).interpolate(method='linear')
                # Normaliser le benchmark pour qu'il commence au même point que le patrimoine total
                # au début de la période commune
                common_start_date = max(patrimoine_total_evolution.index.min(), benchmark_data.index.min())
                if common_start_date in patrimoine_total_evolution.index and common_start_date in benchmark_data.index:
                    patrimoine_start_value = patrimoine_total_evolution.loc[common_start_date]
                    benchmark_start_value = benchmark_data.loc[common_start_date]
                    if benchmark_start_value != 0:
                        benchmark_data = (benchmark_data / benchmark_start_value) * patrimoine_start_value
                    else:
                        logging.warning("Valeur de départ du benchmark est zéro, impossible de normaliser.")
                        benchmark_data = pd.Series(dtype=float, index=patrimoine_total_evolution.index)
                else:
                    logging.warning("Dates de début communes non trouvées pour la normalisation du benchmark.")
                    benchmark_data = pd.Series(dtype=float, index=patrimoine_total_evolution.index)
            else:
                logging.warning("Données benchmark vides ou index non DatetimeIndex, impossible de normaliser.")
                benchmark_data = pd.Series(dtype=float, index=patrimoine_total_evolution.index)

        # Assurer que tous les index sont des DatetimeIndex avant de retourner
        apports_cumules.index = pd.to_datetime(apports_cumules.index, errors='coerce')
        patrimoine_total_evolution.index = pd.to_datetime(patrimoine_total_evolution.index, errors='coerce')
        benchmark_data.index = pd.to_datetime(benchmark_data.index, errors='coerce')

        return {"repartition_data": repartition, 
                "evolution_data": {"apports_cumules": apports_cumules,
                                   "patrimoine_total_evolution": patrimoine_total_evolution,
                                   "benchmark": benchmark_data}}

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