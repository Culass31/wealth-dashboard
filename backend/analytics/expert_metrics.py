# ===== backend/analytics/expert_metrics.py - MÉTRIQUES EXPERT PATRIMOINE =====
import pandas as pd
import numpy as np
from typing import Dict, List, Tuple, Optional
from datetime import datetime, timedelta
from scipy.optimize import fsolve
import warnings
warnings.filterwarnings('ignore')

class ExpertPatrimoineCalculator:
    """Calculateur expert pour métriques avancées de gestion de patrimoine"""
    
    def __init__(self):
        self.oat_10y_rate = 0.035  # OAT 10 ans France ~3.5% (benchmark sans risque)
        self.real_estate_benchmark = 0.055  # Benchmark immobilier ~5.5%
    
    def calculate_capital_en_cours(self, investments_df: pd.DataFrame, cash_flows_df: pd.DataFrame) -> Dict:
        """
        Calculer le capital en cours par plateforme
        Capital en cours = Capital investi - Capital remboursé + Valorisation actuelle
        """
        print("💰 Calcul du capital en cours par plateforme...")
        
        capital_by_platform = {}
        
        if investments_df.empty:
            return capital_by_platform
        
        platforms = investments_df['platform'].unique()
        
        for platform in platforms:
            # Investissements de la plateforme
            platform_investments = investments_df[investments_df['platform'] == platform]
            
            # Flux de la plateforme
            platform_flows = cash_flows_df[cash_flows_df['platform'] == platform] if 'platform' in cash_flows_df.columns else pd.DataFrame()
            
            # Capital investi total
            capital_investi = platform_investments['invested_amount'].sum()
            
            # Capital remboursé (remboursements + ventes)
            capital_rembourse = 0.0
            if not platform_flows.empty:
                repayments = platform_flows[
                    (platform_flows['flow_type'].isin(['repayment', 'sale'])) & 
                    (platform_flows['flow_direction'] == 'in')
                ]['net_amount'].sum()
                capital_rembourse = repayments
            
            # Valorisation actuelle (pour PEA principalement)
            valorisation_actuelle = 0.0
            if 'current_value' in platform_investments.columns:
                valorisation_actuelle = platform_investments['current_value'].fillna(0).sum()
            
            # Capital en cours = Investi - Remboursé (pour crowdfunding) ou Valorisation actuelle (pour PEA)
            if platform in ['PEA']:
                capital_en_cours = valorisation_actuelle
            else:
                capital_en_cours = capital_investi - capital_rembourse
            
            capital_by_platform[platform] = {
                'capital_investi': capital_investi,
                'capital_rembourse': capital_rembourse,
                'valorisation_actuelle': valorisation_actuelle,
                'capital_en_cours': capital_en_cours,
                'taux_remboursement': (capital_rembourse / capital_investi * 100) if capital_investi > 0 else 0
            }
        
        return capital_by_platform
    
    def calculate_taux_reinvestissement(self, cash_flows_df: pd.DataFrame) -> Dict:
        """
        Calculer les taux de réinvestissement par plateforme
        Taux réinvestissement = 1 - (Argent déposé / Total investi)
        Taux capital remboursé = Argent frais / Capital remboursé
        """
        print("🔄 Calcul des taux de réinvestissement...")
        
        reinvestment_by_platform = {}
        
        if cash_flows_df.empty or 'platform' not in cash_flows_df.columns:
            return reinvestment_by_platform
        
        platforms = cash_flows_df['platform'].unique()
        
        for platform in platforms:
            platform_flows = cash_flows_df[cash_flows_df['platform'] == platform]
            
            # Argent frais déposé
            depots = platform_flows[
                (platform_flows['flow_type'] == 'deposit') & 
                (platform_flows['flow_direction'] == 'out')
            ]['gross_amount'].sum()
            
            # Total investi dans les projets
            investissements = platform_flows[
                (platform_flows['flow_type'] == 'investment') & 
                (platform_flows['flow_direction'] == 'out')
            ]['gross_amount'].sum()
            
            # Capital remboursé
            remboursements = platform_flows[
                (platform_flows['flow_type'].isin(['repayment', 'sale'])) & 
                (platform_flows['flow_direction'] == 'in')
            ]['net_amount'].sum()
            
            # Calculs des taux
            if investissements > 0:
                taux_reinvestissement = 1 - (depots / investissements)
                taux_reinvestissement_pct = taux_reinvestissement * 100
            else:
                taux_reinvestissement_pct = 0
            
            if remboursements > 0:
                taux_capital_rembourse = (depots / remboursements) * 100
            else:
                taux_capital_rembourse = 0
            
            # Effet boule de neige
            capital_reinvesti = max(0, investissements - depots)
            
            reinvestment_by_platform[platform] = {
                'argent_frais_depose': depots,
                'total_investi': investissements,
                'capital_rembourse': remboursements,
                'capital_reinvesti': capital_reinvesti,
                'taux_reinvestissement_pct': taux_reinvestissement_pct,
                'taux_capital_rembourse_pct': taux_capital_rembourse,
                'effet_boule_neige': capital_reinvesti / depots if depots > 0 else 0
            }
        
        return reinvestment_by_platform
    
    def calculate_performance_mensuelle(self, investments_df: pd.DataFrame, cash_flows_df: pd.DataFrame) -> Dict:
        """
        Calculer les performances mensuelles par plateforme
        Particulièrement important pour le PEA avec valorisation
        """
        print("📊 Calcul des performances mensuelles...")
        
        performance_by_platform = {}
        
        if cash_flows_df.empty:
            return performance_by_platform
        
        # Préparation données temporelles
        cash_flows_df['transaction_date'] = pd.to_datetime(cash_flows_df['transaction_date'], errors='coerce')
        cash_flows_df['year_month'] = cash_flows_df['transaction_date'].dt.to_period('M')
        
        platforms = cash_flows_df['platform'].unique()
        
        for platform in platforms:
            platform_flows = cash_flows_df[cash_flows_df['platform'] == platform]
            
            # Flux mensuels nets
            monthly_flows = platform_flows.groupby('year_month')['net_amount'].sum()
            
            # Pour PEA : utiliser valorisation si disponible
            if platform == 'PEA':
                # Performance basée sur la valorisation mensuelle
                monthly_performance = self._calculate_pea_monthly_performance(platform_flows, investments_df)
            else:
                # Pour crowdfunding : performance basée sur les flux
                monthly_performance = self._calculate_cf_monthly_performance(monthly_flows, investments_df, platform)
            
            performance_by_platform[platform] = {
                'monthly_flows': monthly_flows.to_dict(),
                'monthly_performance': monthly_performance,
                'annual_performance': self._annualize_performance(monthly_performance),
                'volatility': np.std(list(monthly_performance.values())) * np.sqrt(12) if monthly_performance else 0
            }
        
        return performance_by_platform
    
    def _calculate_pea_monthly_performance(self, platform_flows: pd.DataFrame, investments_df: pd.DataFrame) -> Dict:
        """Calculer performance mensuelle PEA basée sur valorisation"""
        
        # Simplification : performance basée sur les flux entrants/sortants
        # À améliorer avec vraies données de valorisation mensuelle
        
        monthly_performance = {}
        platform_investments = investments_df[investments_df['platform'] == 'PEA']
        
        if platform_investments.empty:
            return monthly_performance
        
        # Capital total PEA
        total_capital = platform_investments['invested_amount'].sum()
        current_value = platform_investments['current_value'].sum() if 'current_value' in platform_investments.columns else total_capital
        
        # Performance globale à répartir mensuellement (approximation)
        if total_capital > 0:
            total_performance = (current_value - total_capital) / total_capital
            
            # Répartition mensuelle approximative
            monthly_flows = platform_flows.groupby('year_month')['net_amount'].sum()
            
            for period in monthly_flows.index:
                # Performance mensuelle approximative
                monthly_perf = total_performance / len(monthly_flows) if len(monthly_flows) > 0 else 0
                monthly_performance[str(period)] = monthly_perf * 100
        
        return monthly_performance
    
    def _calculate_cf_monthly_performance(self, monthly_flows: pd.Series, investments_df: pd.DataFrame, platform: str) -> Dict:
        """Calculer performance mensuelle crowdfunding"""
        
        monthly_performance = {}
        platform_investments = investments_df[investments_df['platform'] == platform]
        
        if platform_investments.empty:
            return monthly_performance
        
        total_invested = platform_investments['invested_amount'].sum()
        
        for period, flow in monthly_flows.items():
            if total_invested > 0:
                monthly_perf = (flow / total_invested) * 100
                monthly_performance[str(period)] = monthly_perf
        
        return monthly_performance
    
    def _annualize_performance(self, monthly_performance: Dict) -> float:
        """Annualiser la performance mensuelle"""
        if not monthly_performance:
            return 0.0
        
        monthly_returns = [perf / 100 for perf in monthly_performance.values()]
        
        if len(monthly_returns) == 0:
            return 0.0
        
        # Performance annualisée composée
        cumulative_return = 1
        for ret in monthly_returns:
            cumulative_return *= (1 + ret)
        
        annual_performance = (cumulative_return ** (12 / len(monthly_returns))) - 1
        return annual_performance * 100
    
    def calculate_tri_expert(self, investments_df: pd.DataFrame, cash_flows_df: pd.DataFrame) -> Dict:
        """
        Calculer TRI expert avec dates réelles d'investissement
        Utilise les vraies dates d'investment_date (pas signature_date)
        """
        print("🎯 Calcul TRI expert avec dates réelles...")
        
        tri_by_platform = {}
        
        if investments_df.empty or cash_flows_df.empty:
            return tri_by_platform
        
        platforms = investments_df['platform'].unique()
        
        for platform in platforms:
            print(f"  📊 TRI {platform}...")
            
            platform_investments = investments_df[investments_df['platform'] == platform]
            platform_flows = cash_flows_df[cash_flows_df['platform'] == platform] if 'platform' in cash_flows_df.columns else pd.DataFrame()
            
            # Construire les flux de trésorerie pour TRI
            cash_flows_list = []
            
            # 1. Sorties : Argent frais déposé (dates réelles)
            if not platform_flows.empty:
                deposits = platform_flows[
                    (platform_flows['flow_type'] == 'deposit') & 
                    (platform_flows['flow_direction'] == 'out')
                ]
                
                for _, deposit in deposits.iterrows():
                    if pd.notna(deposit['transaction_date']):
                        cash_flows_list.append((deposit['transaction_date'], -deposit['gross_amount']))
            
            # 2. Entrées : Remboursements nets (capital + intérêts - taxes)
            if not platform_flows.empty:
                repayments = platform_flows[
                    (platform_flows['flow_type'].isin(['repayment', 'interest', 'dividend'])) & 
                    (platform_flows['flow_direction'] == 'in')
                ]
                
                for _, repayment in repayments.iterrows():
                    if pd.notna(repayment['transaction_date']):
                        cash_flows_list.append((repayment['transaction_date'], repayment['net_amount']))
            
            # 3. Valorisation actuelle pour positions ouvertes (PEA)
            if platform == 'PEA':
                current_value = platform_investments['current_value'].sum() if 'current_value' in platform_investments.columns else 0
                if current_value > 0:
                    cash_flows_list.append((datetime.now().strftime('%Y-%m-%d'), current_value))
            
            # Calculer TRI
            if len(cash_flows_list) >= 2:
                tri = self._calculate_irr_xirr(cash_flows_list)
                
                # Métriques complémentaires
                total_deposited = sum(-flow[1] for flow in cash_flows_list if flow[1] < 0)
                total_returned = sum(flow[1] for flow in cash_flows_list if flow[1] > 0)
                
                tri_by_platform[platform] = {
                    'tri_annuel': tri,
                    'total_depose': total_deposited,
                    'total_retourne': total_returned,
                    'multiple': total_returned / total_deposited if total_deposited > 0 else 0,
                    'profit_net': total_returned - total_deposited,
                    'nb_flux': len(cash_flows_list),
                    'periode_jours': self._calculate_period_days(cash_flows_list),
                    'benchmark_oat_10y': self.oat_10y_rate * 100,
                    'outperformance_vs_oat': tri - (self.oat_10y_rate * 100)
                }
            else:
                tri_by_platform[platform] = {
                    'tri_annuel': 0,
                    'total_depose': 0,
                    'total_retourne': 0,
                    'multiple': 0,
                    'profit_net': 0,
                    'nb_flux': 0,
                    'periode_jours': 0,
                    'benchmark_oat_10y': self.oat_10y_rate * 100,
                    'outperformance_vs_oat': 0
                }
        
        return tri_by_platform
    
    def _calculate_irr_xirr(self, cash_flows: List[Tuple[str, float]]) -> float:
        """
        Calculer TRI avec méthode XIRR (dates exactes)
        Plus précis que IRR classique pour des flux irréguliers
        """
        if len(cash_flows) < 2:
            return 0.0
        
        try:
            # Convertir en DataFrame
            df = pd.DataFrame(cash_flows, columns=['date', 'amount'])
            df['date'] = pd.to_datetime(df['date'])
            df = df.sort_values('date')
            
            # Date de référence (premier flux)
            base_date = df['date'].iloc[0]
            df['days'] = (df['date'] - base_date).dt.days
            
            # Fonction VAN pour résolution TRI
            def npv_function(rate):
                npv = 0
                for _, row in df.iterrows():
                    years = row['days'] / 365.25
                    npv += row['amount'] / ((1 + rate) ** years)
                return npv
            
            # Résolution Newton-Raphson
            try:
                irr = fsolve(npv_function, 0.1)[0]  # Estimation initiale 10%
                
                # Validation : TRI entre -95% et +500%
                if -0.95 <= irr <= 5.0:
                    return irr * 100  # Convertir en pourcentage
                else:
                    return 0.0
            except:
                # Fallback : méthode approximative
                return self._calculate_irr_approximate(cash_flows)
                
        except Exception as e:
            print(f"⚠️  Erreur calcul TRI: {e}")
            return 0.0
    
    def _calculate_irr_approximate(self, cash_flows: List[Tuple[str, float]]) -> float:
        """Méthode approximative pour TRI en cas d'échec XIRR"""
        try:
            total_invested = sum(-flow[1] for flow in cash_flows if flow[1] < 0)
            total_returned = sum(flow[1] for flow in cash_flows if flow[1] > 0)
            
            if total_invested <= 0:
                return 0.0
            
            # Période en années
            dates = [datetime.strptime(flow[0], '%Y-%m-%d') for flow in cash_flows]
            period_years = (max(dates) - min(dates)).days / 365.25
            
            if period_years <= 0:
                return 0.0
            
            # TRI approximatif : ((Total retourné / Total investi) ^ (1/années)) - 1
            irr_approx = ((total_returned / total_invested) ** (1 / period_years)) - 1
            return irr_approx * 100
            
        except:
            return 0.0
    
    def _calculate_period_days(self, cash_flows: List[Tuple[str, float]]) -> int:
        """Calculer période en jours entre premier et dernier flux"""
        try:
            dates = [datetime.strptime(flow[0], '%Y-%m-%d') for flow in cash_flows]
            return (max(dates) - min(dates)).days
        except:
            return 0
    
    def calculate_duration_immobilisation(self, investments_df: pd.DataFrame) -> Dict:
        """
        Analyser la duration et l'immobilisation des capitaux
        Métriques clés pour optimiser la liquidité
        """
        print("⏱️  Calcul duration et immobilisation...")
        
        duration_analysis = {}
        
        if investments_df.empty:
            return duration_analysis
        
        # Convertir les dates
        investments_df = investments_df.copy()
        investments_df['investment_date'] = pd.to_datetime(investments_df['investment_date'], errors='coerce')
        investments_df['expected_end_date'] = pd.to_datetime(investments_df['expected_end_date'], errors='coerce')
        investments_df['actual_end_date'] = pd.to_datetime(investments_df['actual_end_date'], errors='coerce')
        
        platforms = investments_df['platform'].unique()
        
        for platform in platforms:
            platform_investments = investments_df[investments_df['platform'] == platform]
            
            # Duration moyenne pondérée
            duration_months = []
            weights = []
            
            for _, investment in platform_investments.iterrows():
                if pd.notna(investment['investment_date']) and pd.notna(investment['expected_end_date']):
                    duration = (investment['expected_end_date'] - investment['investment_date']).days / 30.44
                    duration_months.append(duration)
                    weights.append(investment['invested_amount'])
            
            if duration_months:
                # Duration moyenne pondérée par montant
                weighted_duration = np.average(duration_months, weights=weights)
                
                # Répartition par échéance
                short_term = sum(1 for d in duration_months if d < 6)
                medium_term = sum(1 for d in duration_months if 6 <= d <= 12)
                long_term = sum(1 for d in duration_months if d > 12)
                
                # Projets en retard
                retards = len(platform_investments[platform_investments['status'] == 'delayed'])
                
                # Capital immobilisé court terme
                short_term_investments = platform_investments[
                    platform_investments.apply(
                        lambda x: pd.notna(x['investment_date']) and pd.notna(x['expected_end_date']) and
                        (x['expected_end_date'] - x['investment_date']).days < 180,
                        axis=1
                    )
                ]
                capital_court_terme = short_term_investments['invested_amount'].sum()
                
                duration_analysis[platform] = {
                    'duration_moyenne_mois': weighted_duration,
                    'duration_mediane_mois': np.median(duration_months),
                    'repartition_echeances': {
                        'court_terme_6m': short_term,
                        'moyen_terme_6_12m': medium_term,
                        'long_terme_12m_plus': long_term
                    },
                    'projets_en_retard': retards,
                    'taux_retard_pct': (retards / len(platform_investments)) * 100,
                    'capital_court_terme': capital_court_terme,
                    'pct_capital_court_terme': (capital_court_terme / platform_investments['invested_amount'].sum()) * 100
                }
        
        return duration_analysis
    
    def calculate_concentration_risk(self, investments_df: pd.DataFrame) -> Dict:
        """
        Analyser le risque de concentration par promoteur/émetteur
        Indice de Herfindahl et métriques de diversification
        """
        print("🎯 Analyse risque de concentration...")
        
        concentration_analysis = {}
        
        if investments_df.empty:
            return concentration_analysis
        
        platforms = investments_df['platform'].unique()
        
        for platform in platforms:
            platform_investments = investments_df[investments_df['platform'] == platform]
            
            if 'company_name' not in platform_investments.columns:
                continue
            
            # Concentration par promoteur/émetteur
            company_allocation = platform_investments.groupby('company_name')['invested_amount'].sum()
            total_platform = platform_investments['invested_amount'].sum()
            
            if total_platform > 0:
                # Parts relatives
                company_shares = company_allocation / total_platform
                
                # Indice de Herfindahl (concentration)
                herfindahl_index = (company_shares ** 2).sum()
                
                # Top 3 émetteurs
                top_3 = company_shares.nlargest(3)
                
                # Nombre d'émetteurs effectifs (inverse Herfindahl)
                effective_number = 1 / herfindahl_index if herfindahl_index > 0 else 1
                
                # Classification concentration
                if herfindahl_index < 0.15:
                    concentration_level = "Faible"
                elif herfindahl_index < 0.25:
                    concentration_level = "Modérée"
                elif herfindahl_index < 0.40:
                    concentration_level = "Élevée"
                else:
                    concentration_level = "Très élevée"
                
                concentration_analysis[platform] = {
                    'herfindahl_index': herfindahl_index,
                    'concentration_level': concentration_level,
                    'nombre_emetteurs_effectifs': effective_number,
                    'top_1_share_pct': top_3.iloc[0] * 100 if len(top_3) > 0 else 0,
                    'top_3_cumul_pct': top_3.sum() * 100,
                    'nombre_emetteurs_total': len(company_allocation),
                    'top_emetteurs': {
                        name: {
                            'montant': company_allocation[name],
                            'part_pct': company_shares[name] * 100
                        } for name in top_3.index
                    }
                }
        
        return concentration_analysis
    
    def calculate_stress_test(self, investments_df: pd.DataFrame, cash_flows_df: pd.DataFrame) -> Dict:
        """
        Stress test : impact de scénarios adverses
        - Défaut du plus gros émetteur
        - Retard de 50% des projets
        - Baisse 20% valorisation PEA
        """
        print("⚠️  Stress test portefeuille...")
        
        stress_results = {}
        
        if investments_df.empty:
            return stress_results
        
        # Capital total
        total_portfolio = investments_df['invested_amount'].sum()
        
        platforms = investments_df['platform'].unique()
        
        for platform in platforms:
            platform_investments = investments_df[investments_df['platform'] == platform]
            platform_capital = platform_investments['invested_amount'].sum()
            
            scenarios = {}
            
            # Scénario 1 : Défaut plus gros émetteur
            if 'company_name' in platform_investments.columns:
                company_allocation = platform_investments.groupby('company_name')['invested_amount'].sum()
                if not company_allocation.empty:
                    biggest_exposure = company_allocation.max()
                    scenarios['defaut_plus_gros_emetteur'] = {
                        'perte_absolue': biggest_exposure,
                        'perte_pct_platform': (biggest_exposure / platform_capital) * 100,
                        'perte_pct_portfolio': (biggest_exposure / total_portfolio) * 100
                    }
            
            # Scénario 2 : Retard 50% des projets (impact liquidité)
            projets_actifs = platform_investments[platform_investments['status'] == 'active']
            if not projets_actifs.empty:
                capital_retarde = projets_actifs['invested_amount'].sum() * 0.5
                scenarios['retard_50_pct_projets'] = {
                    'capital_immobilise_supplementaire': capital_retarde,
                    'impact_liquidite_pct': (capital_retarde / platform_capital) * 100
                }
            
            # Scénario 3 : Baisse valorisation (PEA/AV)
            if platform in ['PEA', 'Assurance_Vie']:
                current_value = platform_investments['current_value'].sum() if 'current_value' in platform_investments.columns else platform_capital
                baisse_20_pct = current_value * 0.2
                scenarios['baisse_valorisation_20pct'] = {
                    'perte_absolue': baisse_20_pct,
                    'perte_pct_platform': 20.0,
                    'nouvelle_valorisation': current_value - baisse_20_pct
                }
            
            stress_results[platform] = scenarios
        
        return stress_results
    
    def generate_expert_report(self, investments_df: pd.DataFrame, cash_flows_df: pd.DataFrame) -> Dict:
        """
        Générer le rapport expert complet avec toutes les métriques avancées
        """
        print("📋 Génération rapport expert patrimoine...")
        
        report = {
            'generated_at': datetime.now().isoformat(),
            'report_type': 'Expert Patrimoine Analysis',
            'analyst': 'AI Expert Gestion Patrimoine'
        }
        
        try:
            # 1. Capital en cours
            report['capital_en_cours'] = self.calculate_capital_en_cours(investments_df, cash_flows_df)
            
            # 2. Taux de réinvestissement
            report['taux_reinvestissement'] = self.calculate_taux_reinvestissement(cash_flows_df)
            
            # 3. Performance mensuelle
            report['performance_mensuelle'] = self.calculate_performance_mensuelle(investments_df, cash_flows_df)
            
            # 4. TRI expert
            report['tri_expert'] = self.calculate_tri_expert(investments_df, cash_flows_df)
            
            # 5. Duration et immobilisation
            report['duration_analysis'] = self.calculate_duration_immobilisation(investments_df)
            
            # 6. Concentration
            report['concentration_risk'] = self.calculate_concentration_risk(investments_df)
            
            # 7. Stress test
            report['stress_test'] = self.calculate_stress_test(investments_df, cash_flows_df)
            
            # 8. Recommandations automatiques
            report['recommandations'] = self._generate_auto_recommendations(report)
            
            print("✅ Rapport expert généré avec succès")
            
        except Exception as e:
            print(f"❌ Erreur génération rapport expert: {e}")
            import traceback
            traceback.print_exc()
        
        return report
    
    def _generate_auto_recommendations(self, report: Dict) -> List[str]:
        """Générer des recommandations automatiques basées sur l'analyse"""
        
        recommendations = []
        
        # Analyse TRI
        tri_data = report.get('tri_expert', {})
        for platform, tri_info in tri_data.items():
            tri_value = tri_info.get('tri_annuel', 0)
            if tri_value > 8:
                recommendations.append(f"✅ {platform}: TRI excellent à {tri_value:.1f}% (vs OAT 10Y à 3.5%)")
            elif tri_value > 5:
                recommendations.append(f"✅ {platform}: TRI satisfaisant à {tri_value:.1f}%")
            elif tri_value < 3:
                recommendations.append(f"⚠️ {platform}: TRI faible à {tri_value:.1f}%, réviser la stratégie")
        
        # Analyse concentration
        concentration_data = report.get('concentration_risk', {})
        for platform, conc_info in concentration_data.items():
            level = conc_info.get('concentration_level', '')
            if level in ['Élevée', 'Très élevée']:
                top_share = conc_info.get('top_1_share_pct', 0)
                recommendations.append(f"⚠️ {platform}: Concentration élevée ({top_share:.1f}% sur un émetteur)")
        
        # Analyse réinvestissement
        reinvest_data = report.get('taux_reinvestissement', {})
        for platform, reinvest_info in reinvest_data.items():
            taux = reinvest_info.get('taux_reinvestissement_pct', 0)
            if taux > 80:
                recommendations.append(f"✅ {platform}: Excellent effet boule de neige ({taux:.0f}% de réinvestissement)")
            elif taux < 30:
                recommendations.append(f"⚠️ {platform}: Faible réinvestissement ({taux:.0f}%), optimiser les flux")
        
        # Analyse duration
        duration_data = report.get('duration_analysis', {})
        for platform, dur_info in duration_data.items():
            retard_pct = dur_info.get('taux_retard_pct', 0)
            if retard_pct > 10:
                recommendations.append(f"⚠️ {platform}: Taux de retard élevé ({retard_pct:.1f}%)")
            
            court_terme_pct = dur_info.get('pct_capital_court_terme', 0)
            if court_terme_pct < 20:
                recommendations.append(f"ℹ️ {platform}: Peu de liquidité court terme ({court_terme_pct:.1f}%)")
        
        if not recommendations:
            recommendations.append("✅ Portefeuille équilibré sans point d'attention majeur")
        
        return recommendations