import numpy as np
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
from plotly.subplots import make_subplots
import streamlit as st
from typing import Dict, List, Tuple
from dataclasses import dataclass
from datetime import datetime, timedelta
import random

@dataclass
class FinancialProfile:
    """Profil financier de l'utilisateur"""
    age: int = 43
    target_age: int = 55  # Objectif de liberté financière
    current_patrimoine: float = 50000  # Patrimoine actuel
    monthly_investment: float = 1500   # Investissement mensuel
    target_patrimoine: float = 500000  # Objectif patrimoine
    monthly_expenses: float = 3000     # Dépenses mensuelles souhaitées
    risk_tolerance: str = "moderate"   # conservative, moderate, aggressive

class FinancialFreedomSimulator:
    """Simulateur de liberté financière avec projections Monte Carlo"""
    
    def __init__(self, profile: FinancialProfile):
        self.profile = profile
        self.scenarios = {
            'conservative': {
                'mean_return': 0.04,    # 4% par an
                'volatility': 0.08,     # 8% volatilité
                'crowdfunding_rate': 0.06,  # 6% crowdfunding
                'stock_rate': 0.07,     # 7% actions
                'av_rate': 0.03         # 3% AV fonds euro
            },
            'moderate': {
                'mean_return': 0.07,    # 7% par an
                'volatility': 0.12,     # 12% volatilité
                'crowdfunding_rate': 0.09,  # 9% crowdfunding
                'stock_rate': 0.10,     # 10% actions
                'av_rate': 0.04         # 4% AV
            },
            'aggressive': {
                'mean_return': 0.10,    # 10% par an
                'volatility': 0.18,     # 18% volatilité
                'crowdfunding_rate': 0.12,  # 12% crowdfunding
                'stock_rate': 0.12,     # 12% actions
                'av_rate': 0.05         # 5% AV
            }
        }
    
    def calculate_required_patrimoine(self) -> float:
        """Calculer le patrimoine requis pour la liberté financière (règle des 4%)"""
        annual_expenses = self.profile.monthly_expenses * 12
        required_patrimoine = annual_expenses / 0.04  # Règle des 4%
        return required_patrimoine
    
    def simulate_single_path(self, num_years: int, scenario: str) -> List[float]:
        """Simuler un chemin de croissance du patrimoine"""
        
        scenario_params = self.scenarios[scenario]
        patrimoine_values = [self.profile.current_patrimoine]
        
        for year in range(num_years):
            current_patrimoine = patrimoine_values[-1]
            
            # Ajout des investissements mensuels
            annual_investment = self.profile.monthly_investment * 12
            
            # Rendement aléatoire selon la distribution normale
            annual_return = np.random.normal(
                scenario_params['mean_return'], 
                scenario_params['volatility']
            )
            
            # Application du rendement
            new_patrimoine = (current_patrimoine + annual_investment) * (1 + annual_return)
            
            # S'assurer que le patrimoine ne devienne pas négatif
            new_patrimoine = max(new_patrimoine, current_patrimoine * 0.5)
            
            patrimoine_values.append(new_patrimoine)
        
        return patrimoine_values
    
    def run_monte_carlo(self, num_simulations: int = 1000, num_years: int = None) -> Dict:
        """Exécuter une simulation Monte Carlo"""
        
        if num_years is None:
            num_years = self.profile.target_age - self.profile.age
        
        scenario = self.profile.risk_tolerance
        required_patrimoine = self.calculate_required_patrimoine()
        
        print(f"🎲 Simulation Monte Carlo: {num_simulations} scénarios sur {num_years} ans")
        print(f"🎯 Objectif: {required_patrimoine:,.0f}€")
        
        # Exécuter les simulations
        all_paths = []
        success_count = 0
        
        for i in range(num_simulations):
            path = self.simulate_single_path(num_years, scenario)
            all_paths.append(path)
            
            # Vérifier si l'objectif est atteint
            if path[-1] >= required_patrimoine:
                success_count += 1
        
        # Analyser les résultats
        final_values = [path[-1] for path in all_paths]
        
        results = {
            'success_probability': success_count / num_simulations * 100,
            'median_final_value': np.median(final_values),
            'percentile_10': np.percentile(final_values, 10),
            'percentile_90': np.percentile(final_values, 90),
            'required_patrimoine': required_patrimoine,
            'all_paths': all_paths,
            'years_to_target': num_years,
            'current_age': self.profile.age,
            'target_age': self.profile.target_age
        }
        
        return results
    
    def analyze_allocation_impact(self) -> Dict:
        """Analyser l'impact de différentes allocations d'actifs"""
        
        allocations = {
            'Conservateur (20% Actions, 30% CF, 50% AV)': {
                'stocks': 0.20,
                'crowdfunding': 0.30,
                'av': 0.50
            },
            'Modéré (40% Actions, 40% CF, 20% AV)': {
                'stocks': 0.40,
                'crowdfunding': 0.40,
                'av': 0.20
            },
            'Agressif (60% Actions, 30% CF, 10% AV)': {
                'stocks': 0.60,
                'crowdfunding': 0.30,
                'av': 0.10
            },
            'Full Crowdfunding (0% Actions, 100% CF, 0% AV)': {
                'stocks': 0.00,
                'crowdfunding': 1.00,
                'av': 0.00
            }
        }
        
        scenario_params = self.scenarios[self.profile.risk_tolerance]
        num_years = self.profile.target_age - self.profile.age
        
        allocation_results = {}
        
        for allocation_name, weights in allocations.items():
            # Calculer le rendement espéré pondéré
            expected_return = (
                weights['stocks'] * scenario_params['stock_rate'] +
                weights['crowdfunding'] * scenario_params['crowdfunding_rate'] +
                weights['av'] * scenario_params['av_rate']
            )
            
            # Simulation simple avec rendement constant
            patrimoine = self.profile.current_patrimoine
            annual_investment = self.profile.monthly_investment * 12
            
            patrimoine_evolution = [patrimoine]
            
            for year in range(num_years):
                patrimoine = (patrimoine + annual_investment) * (1 + expected_return)
                patrimoine_evolution.append(patrimoine)
            
            allocation_results[allocation_name] = {
                'expected_return': expected_return * 100,
                'final_patrimoine': patrimoine,
                'evolution': patrimoine_evolution
            }
        
        return allocation_results
    
    def calculate_sensitivity_analysis(self) -> Dict:
        """Analyse de sensibilité aux paramètres clés"""
        
        base_case = self.run_monte_carlo(num_simulations=500)
        base_probability = base_case['success_probability']
        
        # Test différents paramètres
        sensitivity_results = {}
        
        # 1. Impact de l'investissement mensuel
        monthly_investments = [1000, 1250, 1500, 1750, 2000]
        investment_impact = []
        
        for monthly_inv in monthly_investments:
            original_monthly = self.profile.monthly_investment
            self.profile.monthly_investment = monthly_inv
            
            result = self.run_monte_carlo(num_simulations=200)
            investment_impact.append({
                'monthly_investment': monthly_inv,
                'success_probability': result['success_probability']
            })
            
            self.profile.monthly_investment = original_monthly
        
        sensitivity_results['monthly_investment'] = investment_impact
        
        # 2. Impact de l'âge cible
        target_ages = [50, 52, 55, 57, 60]
        age_impact = []
        
        for target_age in target_ages:
            original_age = self.profile.target_age
            self.profile.target_age = target_age
            
            result = self.run_monte_carlo(num_simulations=200)
            age_impact.append({
                'target_age': target_age,
                'success_probability': result['success_probability'],
                'years_to_target': target_age - self.profile.age
            })
            
            self.profile.target_age = original_age
        
        sensitivity_results['target_age'] = age_impact
        
        return sensitivity_results

def create_simulation_dashboard():
    """Interface Streamlit pour le simulateur"""
    
    st.title("🎯 Simulateur de Liberté Financière")
    st.markdown("---")
    
    # Configuration du profil utilisateur
    st.sidebar.header("👤 Votre Profil")
    
    age = st.sidebar.slider("Âge actuel", 25, 65, 43)
    target_age = st.sidebar.slider("Âge cible liberté financière", age + 5, 70, 55)
    current_patrimoine = st.sidebar.number_input("Patrimoine actuel (€)", 0, 1000000, 50000, step=5000)
    monthly_investment = st.sidebar.number_input("Investissement mensuel (€)", 0, 10000, 1500, step=100)
    monthly_expenses = st.sidebar.number_input("Dépenses mensuelles souhaitées (€)", 1000, 20000, 3000, step=100)
    
    risk_tolerance = st.sidebar.selectbox(
        "Tolérance au risque",
        ["conservative", "moderate", "aggressive"],
        index=1
    )
    
    # Créer le profil
    profile = FinancialProfile(
        age=age,
        target_age=target_age,
        current_patrimoine=current_patrimoine,
        monthly_investment=monthly_investment,
        monthly_expenses=monthly_expenses,
        risk_tolerance=risk_tolerance
    )
    
    # Créer le simulateur
    simulator = FinancialFreedomSimulator(profile)
    
    # Onglets de navigation
    tab1, tab2, tab3, tab4 = st.tabs(["🎲 Simulation", "📊 Allocations", "🔍 Sensibilité", "📋 Recommandations"])
    
    with tab1:
        st.subheader("Simulation Monte Carlo")
        
        col1, col2 = st.columns(2)
        
        with col1:
            num_simulations = st.slider("Nombre de simulations", 100, 2000, 1000, step=100)
        
        with col2:
            custom_years = st.checkbox("Période personnalisée")
            if custom_years:
                num_years = st.slider("Nombre d'années", 5, 30, target_age - age)
            else:
                num_years = target_age - age
        
        if st.button("🚀 Lancer la Simulation"):
            with st.spinner("Simulation en cours..."):
                results = simulator.run_monte_carlo(num_simulations, num_years)
            
            # Affichage des résultats
            col1, col2, col3 = st.columns(3)
            
            with col1:
                success_prob = results['success_probability']
                color = "green" if success_prob > 70 else "orange" if success_prob > 50 else "red"
                
                st.markdown(f"""
                <div style="border: 2px solid {color}; padding: 1rem; border-radius: 0.5rem; text-align: center;">
                    <h3>Probabilité de Succès</h3>
                    <h1 style="color: {color};">{success_prob:.1f}%</h1>
                </div>
                """, unsafe_allow_html=True)
            
            with col2:
                st.metric(
                    "Patrimoine Médian",
                    f"{results['median_final_value']:,.0f} €"
                )
            
            with col3:
                required = results['required_patrimoine']
                st.metric(
                    "Objectif Requis",
                    f"{required:,.0f} €"
                )
            
            # Graphique des trajectoires
            st.subheader("📈 Trajectoires de Patrimoine")
            
            fig = go.Figure()
            
            # Afficher quelques trajectoires
            sample_paths = random.sample(results['all_paths'], min(50, len(results['all_paths'])))
            years = list(range(num_years + 1))
            
            for i, path in enumerate(sample_paths):
                fig.add_trace(go.Scatter(
                    x=years,
                    y=path,
                    mode='lines',
                    line=dict(width=1, color='lightblue'),
                    showlegend=False,
                    hovertemplate='Année %{x}<br>Patrimoine: %{y:,.0f}€'
                ))
            
            # Ligne médiane
            median_path = np.median(results['all_paths'], axis=0)
            fig.add_trace(go.Scatter(
                x=years,
                y=median_path,
                mode='lines',
                line=dict(width=3, color='blue'),
                name='Médiane',
                hovertemplate='Année %{x}<br>Patrimoine: %{y:,.0f}€'
            ))
            
            # Ligne objectif
            fig.add_hline(
                y=required,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Objectif: {required:,.0f}€"
            )
            
            fig.update_layout(
                title="Évolution du Patrimoine - Simulation Monte Carlo",
                xaxis_title="Années",
                yaxis_title="Patrimoine (€)",
                hovermode='x'
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Histogramme des résultats finaux
            st.subheader("📊 Distribution des Résultats")
            
            final_values = [path[-1] for path in results['all_paths']]
            
            fig_hist = go.Figure()
            fig_hist.add_trace(go.Histogram(
                x=final_values,
                nbinsx=50,
                name='Distribution',
                marker_color='lightgreen'
            ))
            
            fig_hist.add_vline(
                x=required,
                line_dash="dash",
                line_color="red",
                annotation_text="Objectif"
            )
            
            fig_hist.update_layout(
                title="Distribution du Patrimoine Final",
                xaxis_title="Patrimoine Final (€)",
                yaxis_title="Fréquence"
            )
            
            st.plotly_chart(fig_hist, use_container_width=True)
    
    with tab2:
        st.subheader("Impact de l'Allocation d'Actifs")
        
        if st.button("📊 Analyser les Allocations"):
            with st.spinner("Analyse en cours..."):
                allocation_results = simulator.analyze_allocation_impact()
            
            # Graphique comparatif
            fig = go.Figure()
            
            for allocation_name, data in allocation_results.items():
                years = list(range(len(data['evolution'])))
                fig.add_trace(go.Scatter(
                    x=years,
                    y=data['evolution'],
                    mode='lines',
                    name=allocation_name,
                    hovertemplate=f'{allocation_name}<br>Année %{{x}}<br>Patrimoine: %{{y:,.0f}}€'
                ))
            
            # Ligne objectif
            required = simulator.calculate_required_patrimoine()
            fig.add_hline(
                y=required,
                line_dash="dash",
                line_color="red",
                annotation_text=f"Objectif: {required:,.0f}€"
            )
            
            fig.update_layout(
                title="Comparaison des Allocations d'Actifs",
                xaxis_title="Années",
                yaxis_title="Patrimoine (€)"
            )
            
            st.plotly_chart(fig, use_container_width=True)
            
            # Tableau comparatif
            comparison_data = []
            for allocation_name, data in allocation_results.items():
                comparison_data.append({
                    'Allocation': allocation_name,
                    'Rendement Espéré (%)': f"{data['expected_return']:.1f}",
                    'Patrimoine Final (€)': f"{data['final_patrimoine']:,.0f}",
                    'Objectif Atteint': "✅" if data['final_patrimoine'] >= required else "❌"
                })
            
            df_comparison = pd.DataFrame(comparison_data)
            st.dataframe(df_comparison, use_container_width=True, hide_index=True)
    
    with tab3:
        st.subheader("Analyse de Sensibilité")
        
        if st.button("🔍 Analyser la Sensibilité"):
            with st.spinner("Analyse de sensibilité en cours..."):
                sensitivity = simulator.calculate_sensitivity_analysis()
            
            # Impact investissement mensuel
            if 'monthly_investment' in sensitivity:
                st.subheader("💰 Impact de l'Investissement Mensuel")
                
                monthly_data = sensitivity['monthly_investment']
                investments = [d['monthly_investment'] for d in monthly_data]
                probabilities = [d['success_probability'] for d in monthly_data]
                
                fig_inv = go.Figure()
                fig_inv.add_trace(go.Scatter(
                    x=investments,
                    y=probabilities,
                    mode='lines+markers',
                    name='Probabilité de Succès',
                    line=dict(width=3, color='blue')
                ))
                
                fig_inv.update_layout(
                    title="Sensibilité à l'Investissement Mensuel",
                    xaxis_title="Investissement Mensuel (€)",
                    yaxis_title="Probabilité de Succès (%)"
                )
                
                st.plotly_chart(fig_inv, use_container_width=True)
            
            # Impact âge cible
            if 'target_age' in sensitivity:
                st.subheader("🎯 Impact de l'Âge Cible")
                
                age_data = sensitivity['target_age']
                ages = [d['target_age'] for d in age_data]
                probabilities = [d['success_probability'] for d in age_data]
                
                fig_age = go.Figure()
                fig_age.add_trace(go.Scatter(
                    x=ages,
                    y=probabilities,
                    mode='lines+markers',
                    name='Probabilité de Succès',
                    line=dict(width=3, color='green')
                ))
                
                fig_age.update_layout(
                    title="Sensibilité à l'Âge Cible",
                    xaxis_title="Âge Cible",
                    yaxis_title="Probabilité de Succès (%)"
                )
                
                st.plotly_chart(fig_age, use_container_width=True)
    
    with tab4:
        st.subheader("📋 Recommandations Personnalisées")
        
        # Calculer quelques métriques pour les recommandations
        required_patrimoine = simulator.calculate_required_patrimoine()
        years_available = target_age - age
        annual_investment = monthly_investment * 12
        
        st.info(f"""
        **Votre Situation :**
        - Patrimoine actuel : {current_patrimoine:,.0f} €
        - Objectif patrimoine : {required_patrimoine:,.0f} €
        - Écart à combler : {required_patrimoine - current_patrimoine:,.0f} €
        - Temps disponible : {years_available} ans
        - Investissement annuel : {annual_investment:,.0f} €
        """)
        
        # Recommandations basées sur la situation
        recommendations = []
        
        if required_patrimoine - current_patrimoine > annual_investment * years_available * 1.5:
            recommendations.append("⚠️ **Objectif ambitieux** : Considérez augmenter votre investissement mensuel ou repousser l'âge cible")
        
        if monthly_investment / (current_patrimoine / 100) < 3:
            recommendations.append("💡 **Potentiel d'épargne** : Vous pourriez possiblement augmenter votre investissement mensuel")
        
        if risk_tolerance == "conservative" and years_available > 10:
            recommendations.append("📈 **Profil de risque** : Avec votre horizon long terme, vous pourriez envisager un profil plus agressif")
        
        recommendations.extend([
            "🏠 **Diversification** : Maintenez un bon équilibre entre crowdfunding, actions et assurance vie",
            "📊 **Suivi régulier** : Réévaluez votre stratégie chaque année",
            "🎯 **Flexibilité** : Adaptez vos objectifs selon l'évolution de votre situation"
        ])
        
        for rec in recommendations:
            st.write(rec)

if __name__ == "__main__":
    create_simulation_dashboard()