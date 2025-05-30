import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
import yfinance as yf
from scipy.optimize import fsolve
from scipy import stats
import warnings
warnings.filterwarnings('ignore')

class AdvancedMetricsCalculator:
    """Calculateur de métriques financières avancées"""
    
    def __init__(self):
        self.risk_free_rate = 0.035  # OAT 10 ans France ~3.5%
        self.benchmarks_cache = {}
    
    def calculate_irr(self, cash_flows: List[Tuple[str, float]]) -> float:
        """
        Calculer le TRI (Taux de Rendement Interne)
        cash_flows: Liste de (date, montant) où montant < 0 = sortie, > 0 = entrée
        """
        if not cash_flows or len(cash_flows) < 2:
            return 0.0
        
        try:
            # Convertir en DataFrame pour faciliter les calculs
            df = pd.DataFrame(cash_flows, columns=['date', 'amount'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Calculer les jours depuis le premier investissement
            start_date = df['date'].min()
            df['days'] = (df['date'] - start_date).dt.days
            
            # Fonction objectif pour le TRI (NPV = 0)
            def npv_func(rate):
                return sum(row['amount'] / ((1 + rate) ** (row['days'] / 365.0)) for _, row in df.iterrows())
            
            # Résoudre pour TRI
            irr = fsolve(npv_func, 0.1)[0]  # Estimation initiale à 10%
            
            # Validation: TRI entre -100% et +1000%
            if -1 <= irr <= 10:
                return irr * 100  # Convertir en pourcentage
            else:
                return 0.0
                
        except Exception as e:
            print(f"⚠️  Erreur calcul TRI: {e}")
            return 0.0
    
    def calculate_platform_irr(self, investments_df: pd.DataFrame, cash_flows_df: pd.DataFrame, platform: str) -> Dict:
        """Calculer le TRI pour une plateforme spécifique"""
        
        # Filtrer par plateforme
        platform_investments = investments_df[investments_df['platform'] == platform].copy()
        platform_cash_flows = cash_flows_df[cash_flows_df['description'].str.contains(platform, case=False, na=False)].copy()
        
        if platform_investments.empty:
            return {'irr': 0, 'total_invested': 0, 'total_returned': 0, 'nb_projects': 0}
        
        # Préparer les flux de trésorerie pour le TRI
        cash_flows_list = []
        
        # Ajouter les investissements (sorties)
        for _, inv in platform_investments.iterrows():
            if pd.notna(inv['investment_date']) and inv['invested_amount'] > 0:
                cash_flows_list.append((inv['investment_date'], -inv['invested_amount']))
        
        # Ajouter les retours (entrées)
        for _, cf in platform_cash_flows.iterrows():
            if pd.notna(cf['transaction_date']) and cf['flow_direction'] == 'in' and cf['net_amount'] > 0:
                cash_flows_list.append((cf['transaction_date'], cf['net_amount']))
        
        # Calculer le TRI
        irr = self.calculate_irr(cash_flows_list)
        
        # Métriques complémentaires
        total_invested = platform_investments['invested_amount'].sum()
        total_returned = platform_cash_flows[platform_cash_flows['flow_direction'] == 'in']['net_amount'].sum()
        nb_projects = len(platform_investments)
        
        return {
            'irr': irr,
            'total_invested': total_invested,
            'total_returned': total_returned,
            'nb_projects': nb_projects,
            'multiple': total_returned / total_invested if total_invested > 0 else 0
        }
    
    def calculate_global_irr(self, investments_df: pd.DataFrame, cash_flows_df: pd.DataFrame) -> Dict:
        """Calculer le TRI global du portefeuille"""
        
        # Tous les flux de trésorerie
        cash_flows_list = []
        
        # Investissements (sorties)
        for _, inv in investments_df.iterrows():
            if pd.notna(inv['investment_date']) and inv['invested_amount'] > 0:
                cash_flows_list.append((inv['investment_date'], -inv['invested_amount']))
        
        # Retours (entrées)
        for _, cf in cash_flows_df.iterrows():
            if pd.notna(cf['transaction_date']) and cf['flow_direction'] == 'in' and cf['net_amount'] > 0:
                cash_flows_list.append((cf['transaction_date'], cf['net_amount']))
        
        # TRI global
        global_irr = self.calculate_irr(cash_flows_list)
        
        # Métriques globales
        total_invested = investments_df['invested_amount'].sum()
        total_returned = cash_flows_df[cash_flows_df['flow_direction'] == 'in']['net_amount'].sum()
        
        return {
            'global_irr': global_irr,
            'total_invested': total_invested,
            'total_returned': total_returned,
            'net_profit': total_returned - total_invested,
            'profit_margin': (total_returned - total_invested) / total_invested * 100 if total_invested > 0 else 0
        }
    
    def calculate_sharpe_ratio(self, returns: List[float], risk_free_rate: float = None) -> float:
        """Calculer le ratio de Sharpe"""
        if not returns or len(returns) < 2:
            return 0.0
        
        if risk_free_rate is None:
            risk_free_rate = self.risk_free_rate
        
        try:
            returns_array = np.array(returns)
            excess_returns = returns_array - risk_free_rate / 12  # Mensuel
            
            if np.std(excess_returns) == 0:
                return 0.0
            
            sharpe = np.mean(excess_returns) / np.std(excess_returns) * np.sqrt(12)  # Annualisé
            return float(sharpe)
            
        except Exception as e:
            print(f"⚠️  Erreur calcul Sharpe: {e}")
            return 0.0
    
    def calculate_var(self, returns: List[float], confidence_level: float = 0.05) -> float:
        """Calculer la Value at Risk (VaR)"""
        if not returns or len(returns) < 10:
            return 0.0
        
        try:
            returns_array = np.array(returns)
            var = np.percentile(returns_array, confidence_level * 100)
            return float(var)
        except Exception as e:
            print(f"⚠️  Erreur calcul VaR: {e}")
            return 0.0
    
    def calculate_max_drawdown(self, values: List[float]) -> float:
        """Calculer le drawdown maximum"""
        if not values or len(values) < 2:
            return 0.0
        
        try:
            values_array = np.array(values)
            peak = np.maximum.accumulate(values_array)
            drawdown = (values_array - peak) / peak
            max_drawdown = np.min(drawdown)
            return float(max_drawdown * 100)  # En pourcentage
        except Exception as e:
            print(f"⚠️  Erreur calcul drawdown: {e}")
            return 0.0
    
    def get_benchmark_data(self, symbol: str, period: str = "2y") -> pd.DataFrame:
        """Récupérer les données de benchmark"""
        if symbol in self.benchmarks_cache:
            return self.benchmarks_cache[symbol]
        
        try:
            ticker = yf.Ticker(symbol)
            data = ticker.history(period=period)
            
            if not data.empty:
                # Calculer les rendements mensuels
                data = data.resample('M').last()
                data['returns'] = data['Close'].pct_change().dropna()
                self.benchmarks_cache[symbol] = data
                return data
            else:
                return pd.DataFrame()
        except Exception as e:
            print(f"⚠️  Erreur récupération benchmark {symbol}: {e}")
            return pd.DataFrame()
    
    def compare_to_benchmarks(self, portfolio_returns: List[float]) -> Dict:
        """Comparer la performance aux benchmarks"""
        
        benchmarks = {
            'CAC40': '^FCHI',
            'S&P500': '^GSPC', 
            'MSCI_World': 'URTH',
            'Euro_Stoxx_50': '^STOXX50E',
            'OAT_10Y': '^TNX'  # Approximation
        }
        
        comparisons = {}
        
        for name, symbol in benchmarks.items():
            try:
                benchmark_data = self.get_benchmark_data(symbol)
                
                if not benchmark_data.empty and 'returns' in benchmark_data.columns:
                    benchmark_returns = benchmark_data['returns'].dropna().tolist()
                    
                    # Aligner les périodes (prendre les N derniers)
                    min_length = min(len(portfolio_returns), len(benchmark_returns))
                    if min_length > 0:
                        port_returns = portfolio_returns[-min_length:]
                        bench_returns = benchmark_returns[-min_length:]
                        
                        # Calculer les métriques comparatives
                        portfolio_annual = (np.prod([1 + r for r in port_returns]) ** (12/len(port_returns)) - 1) * 100
                        benchmark_annual = (np.prod([1 + r for r in bench_returns]) ** (12/len(bench_returns)) - 1) * 100
                        
                        # Alpha (performance excédentaire)
                        alpha = portfolio_annual - benchmark_annual
                        
                        # Beta (corrélation avec le marché)
                        if len(port_returns) > 1 and len(bench_returns) > 1:
                            correlation = np.corrcoef(port_returns, bench_returns)[0, 1]
                            beta = correlation * (np.std(port_returns) / np.std(bench_returns))
                        else:
                            beta = 1.0
                        
                        comparisons[name] = {
                            'benchmark_return': benchmark_annual,
                            'alpha': alpha,
                            'beta': beta,
                            'correlation': correlation if 'correlation' in locals() else 0
                        }
                        
            except Exception as e:
                print(f"⚠️  Erreur comparaison {name}: {e}")
                continue
        
        return comparisons
    
    def calculate_crowdfunding_metrics(self, investments_df: pd.DataFrame, cash_flows_df: pd.DataFrame) -> Dict:
        """Métriques spécifiques au crowdfunding immobilier"""
        
        if investments_df.empty:
            return {}
        
        # Filtrer le crowdfunding immobilier
        crowdfunding_df = investments_df[investments_df['investment_type'] == 'crowdfunding'].copy()
        
        if crowdfunding_df.empty:
            return {}
        
        metrics = {}
        
        # Durée moyenne des projets
        if 'investment_date' in crowdfunding_df.columns and 'expected_end_date' in crowdfunding_df.columns:
            crowdfunding_df['investment_date'] = pd.to_datetime(crowdfunding_df['investment_date'])
            crowdfunding_df['expected_end_date'] = pd.to_datetime(crowdfunding_df['expected_end_date'])
            
            durations = (crowdfunding_df['expected_end_date'] - crowdfunding_df['investment_date']).dt.days / 365
            metrics['avg_duration_years'] = durations.mean()
        
        # Taux de défaut
        total_projects = len(crowdfunding_df)
        defaulted_projects = len(crowdfunding_df[crowdfunding_df['status'] == 'defaulted'])
        metrics['default_rate'] = (defaulted_projects / total_projects * 100) if total_projects > 0 else 0
        
        # Taux de retard
        delayed_projects = len(crowdfunding_df[crowdfunding_df['status'] == 'delayed'])
        metrics['delay_rate'] = (delayed_projects / total_projects * 100) if total_projects > 0 else 0
        
        # Diversification par promoteur
        if 'company_name' in crowdfunding_df.columns:
            promoter_concentration = crowdfunding_df.groupby('company_name')['invested_amount'].sum()
            total_invested = crowdfunding_df['invested_amount'].sum()
            
            # Indice de Herfindahl (concentration)
            if total_invested > 0:
                shares = promoter_concentration / total_invested
                herfindahl_index = (shares ** 2).sum()
                metrics['concentration_index'] = herfindahl_index
                metrics['top_promoter_share'] = shares.max() * 100
        
        # Rendement moyen pondéré
        if 'annual_rate' in crowdfunding_df.columns:
            valid_rates = crowdfunding_df[crowdfunding_df['annual_rate'] > 0]
            if not valid_rates.empty:
                weighted_rate = np.average(valid_rates['annual_rate'], weights=valid_rates['invested_amount'])
                metrics['weighted_avg_rate'] = weighted_rate
        
        # Répartition par montant d'investissement
        if 'invested_amount' in crowdfunding_df.columns:
            amounts = crowdfunding_df['invested_amount']
            metrics['avg_investment_size'] = amounts.mean()
            metrics['median_investment_size'] = amounts.median()
            metrics['investment_std'] = amounts.std()
        
        return metrics
    
    def calculate_monthly_returns(self, investments_df: pd.DataFrame, cash_flows_df: pd.DataFrame) -> List[float]:
        """Calculer les rendements mensuels du portefeuille"""
        
        if cash_flows_df.empty:
            return []
        
        try:
            # Préparer les données
            cf_df = cash_flows_df.copy()
            cf_df['transaction_date'] = pd.to_datetime(cf_df['transaction_date'])
            cf_df['year_month'] = cf_df['transaction_date'].dt.to_period('M')
            
            # Flux mensuels nets
            monthly_flows = cf_df.groupby('year_month')['net_amount'].sum()
            
            # Calculs approximatifs des rendements (à affiner selon vos besoins)
            total_invested = investments_df['invested_amount'].sum() if not investments_df.empty else 1
            
            # Rendements mensuels = flux nets / total investi
            monthly_returns = (monthly_flows / total_invested).tolist()
            
            return monthly_returns
            
        except Exception as e:
            print(f"⚠️  Erreur calcul rendements mensuels: {e}")
            return []
    
    def generate_performance_report(self, investments_df: pd.DataFrame, cash_flows_df: pd.DataFrame) -> Dict:
        """Générer un rapport complet de performance"""
        
        print("📊 Génération du rapport de performance avancé...")
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'period_analyzed': 'Depuis inception'
        }
        
        try:
            # 1. TRI Global
            global_metrics = self.calculate_global_irr(investments_df, cash_flows_df)
            report['global_irr'] = global_metrics
            
            # 2. TRI par plateforme
            platform_irrs = {}
            if not investments_df.empty:
                platforms = investments_df['platform'].unique()
                for platform in platforms:
                    platform_irrs[platform] = self.calculate_platform_irr(investments_df, cash_flows_df, platform)
            report['platform_irrs'] = platform_irrs
            
            # 3. Métriques de risque
            monthly_returns = self.calculate_monthly_returns(investments_df, cash_flows_df)
            if monthly_returns:
                report['risk_metrics'] = {
                    'sharpe_ratio': self.calculate_sharpe_ratio(monthly_returns),
                    'var_5pct': self.calculate_var(monthly_returns, 0.05),
                    'var_1pct': self.calculate_var(monthly_returns, 0.01),
                    'volatility': np.std(monthly_returns) * np.sqrt(12) * 100,  # Annualisée
                    'max_drawdown': self.calculate_max_drawdown(monthly_returns)
                }
            
            # 4. Comparaisons benchmark
            if monthly_returns:
                report['benchmark_comparisons'] = self.compare_to_benchmarks(monthly_returns)
            
            # 5. Métriques crowdfunding
            report['crowdfunding_metrics'] = self.calculate_crowdfunding_metrics(investments_df, cash_flows_df)
            
            print("✅ Rapport de performance généré avec succès")
            
        except Exception as e:
            print(f"❌ Erreur génération rapport: {e}")
            import traceback
            traceback.print_exc()
        
        return report

# ===== Test et utilisation =====
def test_metrics_calculator():
    """Fonction de test du calculateur de métriques"""
    
    print("🧪 Test du calculateur de métriques avancées...")
    
    # Créer des données de test
    test_cash_flows = [
        ('2022-01-01', -1000),  # Investissement initial
        ('2022-06-01', 50),     # Intérêts
        ('2022-12-01', 50),     # Intérêts
        ('2023-06-01', 50),     # Intérêts
        ('2023-12-01', 1050),   # Remboursement capital + intérêts
    ]
    
    calculator = AdvancedMetricsCalculator()
    
    # Test TRI
    irr = calculator.calculate_irr(test_cash_flows)
    print(f"TRI calculé: {irr:.2f}%")
    
    # Test Sharpe
    test_returns = [0.02, -0.01, 0.03, 0.01, -0.005, 0.025]
    sharpe = calculator.calculate_sharpe_ratio(test_returns)
    print(f"Ratio de Sharpe: {sharpe:.3f}")
    
    print("✅ Tests terminés")

if __name__ == "__main__":
    test_metrics_calculator()