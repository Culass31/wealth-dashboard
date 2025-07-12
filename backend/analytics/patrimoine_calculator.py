# ===== backend/analytics/patrimoine_calculator.py - MOTEUR DE CALCUL DU DASHBOARD (v1.9.5 - CORRECTION TRI & BENCHMARK) =====
import logging
import pandas as pd
from typing import Dict, List, Tuple, Any
from datetime import datetime
from scipy.optimize import fsolve
import yfinance as yf
import warnings

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
        logging.info("Données chargées.")
        logging.debug(f"Investments DF head:\n{self.investments_df.head()}")
        logging.debug(f"Cash Flows DF head:\n{self.cash_flows_df.head()}")
        logging.debug(f"Positions DF head:\n{self.positions_df.head()}")
        logging.debug(f"Liquidity DF head:\n{self.liquidity_df.head()}")

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
        
        return {"patrimoine_total": patrimoine_total, "plus_value_nette": plus_value_nette, "total_apports": total_apports, "tri_global_brut": tri_brut * 100, "tri_global_net": tri_net * 100}

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

            details[p] = {
                "capital_investi_encours": (cap_investi, cap_encours), "plus_value_realisee_nette": int_bruts - taxes,
                "tri_brut": tri_brut * 100,
                "tri_net": tri_net * 100,
                "interets_bruts_recus": int_bruts, "impots_et_frais": taxes,
                "nombre_projets": len(inv_p) if is_cf else len(pos_p)
            }
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
        if self.cash_flows_df.empty: return {"monthly": pd.DataFrame(), "annual": pd.DataFrame()}
        df = self.cash_flows_df.copy()
        df['transaction_date'] = pd.to_datetime(df['transaction_date'])
        df['net_gain'] = df['interest_amount'].fillna(0) - df['tax_amount'].fillna(0)
        fee_flows = df['flow_type'] == 'fee'
        df.loc[fee_flows, 'net_gain'] = -df.loc[fee_flows, 'gross_amount'].fillna(0)
        monthly_perf = df.set_index('transaction_date').resample('M')['net_gain'].sum().reset_index()
        monthly_perf['Period'] = monthly_perf['transaction_date'].dt.strftime('%Y-%m')
        annual_perf = df.set_index('transaction_date').resample('Y')['net_gain'].sum().reset_index()
        annual_perf['Period'] = annual_perf['transaction_date'].dt.strftime('%Y')
        return {"monthly": monthly_perf[['Period', 'net_gain']], "annual": annual_perf[['Period', 'net_gain']]}

    def get_charts_data(self) -> Dict[str, Any]:
        logging.info("Préparation des données pour les graphiques...")
        total_encours_cf = self.investments_df['remaining_capital'].sum() if 'remaining_capital' in self.investments_df.columns else 0
        pea_av_value = self.positions_df['market_value'].sum() if 'market_value' in self.positions_df.columns else 0
        total_liquidity = 0
        if not self.liquidity_df.empty and 'balance_date' in self.liquidity_df.columns: total_liquidity = self.liquidity_df.sort_values('balance_date').drop_duplicates('platform', keep='last')['amount'].sum()
        repartition = {"Bourse (PEA/AV)": pea_av_value, "Crowdfunding": total_encours_cf, "Liquidités": total_liquidity}
        apports_cumules = pd.Series(dtype=float)
        if not self.cash_flows_df.empty:
            apports_df = self.cash_flows_df[self.cash_flows_df['flow_type'] == 'deposit'].copy()
            if not apports_df.empty:
                apports_cumules = apports_df.set_index('transaction_date')['gross_amount'].resample('D').sum().cumsum().ffill()
                # Ensure apports_cumules index is DatetimeIndex
                apports_cumules.index = pd.to_datetime(apports_cumules.index)
        
        # --- CORRECTION MAJEURE : Calcul du patrimoine total pour le graphique d'évolution ---
        patrimoine_total_evolution = pd.Series(dtype=float)
        if not self.cash_flows_df.empty:
            # Calculer le patrimoine total à chaque date de transaction
            # C'est une simplification, l'idéal serait d'avoir des valorisations quotidiennes
            # Pour l'instant, on cumule les flux nets pour estimer l'évolution du patrimoine
            df_temp = self.cash_flows_df.copy()
            df_temp['transaction_date'] = pd.to_datetime(df_temp['transaction_date'])
            df_temp['signed_net_amount'] = df_temp.apply(
                lambda row: row['net_amount'] if row['flow_direction'] == 'in' else -row['net_amount'], axis=1
            )
            patrimoine_total_evolution = df_temp.set_index('transaction_date')['signed_net_amount'].resample('D').sum().cumsum().ffill()
            # Ajouter la valeur actuelle du patrimoine à la dernière date
            if not patrimoine_total_evolution.empty:
                # Utilise pd.Timestamp pour la cohérence avec l'index
                patrimoine_total_evolution.loc[pd.Timestamp(datetime.now().date())] = self.get_global_kpis()['patrimoine_total'] 
                patrimoine_total_evolution = patrimoine_total_evolution.resample('D').ffill()

        benchmark_data = pd.Series(dtype=float)
        if not apports_cumules.empty:
            start, end, ticker = apports_cumules.index.min(), datetime.now(), "EWLD.PA"
            logging.info(f"Téléchargement du benchmark {ticker} de {start} à {end}")
            try:
                prices = yf.download(ticker, start=start, end=end, progress=False, auto_adjust=True)['Close'].squeeze() # auto_adjust=True
                # S'assurer que l'index des prix est un DatetimeIndex
                prices.index = pd.to_datetime(prices.index)
                logging.debug(f"Prices after yf.download for {ticker}:\n{prices.head()}") # Nouveau log
                if prices.empty: raise ValueError("Aucune donnée de prix retournée par yfinance.")
                
                # --- CORRECTION MAJEURE : Normalisation du benchmark par rapport aux apports réels ---
                # Créer une série d'investissements dans le benchmark aux dates des apports réels
                # Utiliser apports_cumules et le réindexer aux dates des prix du benchmark
                invested_on_benchmark = apports_cumules.reindex(prices.index).ffill().fillna(0)
                logging.debug(f"""Invested on benchmark (head):
{str(invested_on_benchmark.head())}""") # Nouveau log
                
                # Calculer la valeur du portefeuille benchmark
                shares_bought = invested_on_benchmark / prices
                logging.debug(f"Shares bought (head):\n{shares_bought.head()}") # Nouveau log
                total_shares = shares_bought.cumsum()
                logging.debug(f"Total shares (head):\n{total_shares.head()}") # Nouveau log
                benchmark_data = (total_shares * prices).ffill()
                logging.debug(f"Benchmark data before normalization (head):\n{benchmark_data.head()}") # Nouveau log
                # Normaliser pour que le point de départ corresponde au premier apport
                if not apports_cumules.empty and not benchmark_data.empty:
                    # Trouver les dates où les deux séries ont des données
                    # Et où les apports cumulés sont positifs

                    # Conversion défensive en DatetimeIndex juste avant l'intersection
                    if not isinstance(apports_cumules.index, pd.DatetimeIndex):
                        apports_cumules.index = pd.to_datetime(apports_cumules.index)
                        print(f"DEBUG (backend): Converti apports_cumules.index en DatetimeIndex avant intersection. Nouveau type: {type(apports_cumules.index)}") # DEBUG
                    if not isinstance(benchmark_data.index, pd.DatetimeIndex):
                        benchmark_data.index = pd.to_datetime(benchmark_data.index)
                        print(f"DEBUG (backend): Converti benchmark_data.index en DatetimeIndex avant intersection. Nouveau type: {type(benchmark_data.index)}") # DEBUG

                    print(f"DEBUG (backend): Type of apports_cumules.index before intersection: {type(apports_cumules.index)}") # DEBUG
                    print(f"DEBUG (backend): Type of benchmark_data.index before intersection: {type(benchmark_data.index)}") # DEBUG
                    valid_dates_for_normalization = apports_cumules.index.intersection(benchmark_data.index)
                    valid_dates_for_normalization = valid_dates_for_normalization[apports_cumules.loc[valid_dates_for_normalization] > 0]
                    print(f"DEBUG (backend): valid_dates_for_normalization: {valid_dates_for_normalization}") # DEBUG

                    if not valid_dates_for_normalization.empty:
                        first_normalization_date = valid_dates_for_normalization.min()
                        print(f"DEBUG (backend): first_normalization_date: {first_normalization_date}") # DEBUG
                        normalization_factor = benchmark_data.loc[first_normalization_date]
                        print(f"DEBUG (backend): normalization_factor: {normalization_factor}") # DEBUG
                        first_deposit_value_at_norm_date = apports_cumules.loc[first_normalization_date]

                        if normalization_factor != 0:
                            benchmark_data = (benchmark_data / normalization_factor) * first_deposit_value_at_norm_date
                        else:
                            logging.warning("Facteur de normalisation du benchmark est zéro, impossible de normaliser.")
                            benchmark_data = pd.Series(dtype=float) # Vider le benchmark si normalisation impossible
                    else:
                        logging.warning("Aucune date de dépôt valide trouvée dans la plage du benchmark pour la normalisation.")
                        benchmark_data = pd.Series(dtype=float) # Vider le benchmark si pas de point de normalisation
                else:
                    logging.warning("Apports cumulés ou données du benchmark vides, impossible de normaliser.")
                    benchmark_data = pd.Series(dtype=float) # Vider le benchmark si pas de dates communes

                logging.info("Données du benchmark calculées avec succès.") # Nouveau log
                logging.debug(f"Benchmark data head:\n{benchmark_data.head()}") # Nouveau log
            except Exception as e:
                logging.warning(f"Impossible de calculer le benchmark {ticker}: {e}")
        
        return {"repartition_data": repartition, 
                "evolution_data": {"apports_cumules": apports_cumules,
                                   "patrimoine_total_evolution": patrimoine_total_evolution,
                                   "benchmark": benchmark_data}}