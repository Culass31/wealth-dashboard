import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import sys
import os
from typing import Dict

# Ajouter le backend au path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.models.database import DatabaseManager
from backend.data.data_loader import DataLoader
from backend.analytics.advanced_metrics import AdvancedMetricsCalculator

# Configuration de la page
st.set_page_config(
    page_title="Tableau de Bord Patrimoine Avancé",
    page_icon="📈",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé pour métriques avancées
st.markdown("""
<style>
    .advanced-metric {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .irr-positive {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    .irr-negative {
        background: linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%);
    }
    .benchmark-comparison {
        border-left: 4px solid #1f77b4;
        padding-left: 1rem;
        margin: 1rem 0;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)  # Cache pendant 5 minutes
def charger_donnees_avancees(user_id: str):
    """Charger les données avec métriques avancées"""
    db = DatabaseManager()
    calculator = AdvancedMetricsCalculator()
    
    # Données de base
    investissements_df = db.get_user_investments(user_id)
    flux_tresorerie_df = db.get_user_cash_flows(user_id)
    
    # Rapport de performance avancé
    rapport_performance = calculator.generate_performance_report(investissements_df, flux_tresorerie_df)
    
    return investissements_df, flux_tresorerie_df, rapport_performance

def afficher_metriques_irr(rapport_performance: Dict):
    """Afficher les métriques TRI"""
    st.subheader("🎯 Analyse TRI (Taux de Rendement Interne)")
    
    global_irr = rapport_performance.get('global_irr', {})
    platform_irrs = rapport_performance.get('platform_irrs', {})
    
    # TRI Global
    col1, col2, col3 = st.columns(3)
    
    with col1:
        irr_global = global_irr.get('global_irr', 0)
        color_class = 'irr-positive' if irr_global > 0 else 'irr-negative'
        
        st.markdown(f"""
        <div class="advanced-metric {color_class}">
            <h3>TRI Global</h3>
            <h2>{irr_global:.2f}%</h2>
            <p>Rendement annualisé</p>
        </div>
        """, unsafe_allow_html=True)
    
    with col2:
        profit_margin = global_irr.get('profit_margin', 0)
        st.metric(
            "Marge Bénéficiaire",
            f"{profit_margin:.1f}%",
            help="Profit net / Capital investi"
        )
    
    with col3:
        total_invested = global_irr.get('total_invested', 0)
        st.metric(
            "Capital Total",
            f"{total_invested:,.0f} €",
            help="Montant total investi"
        )
    
    # TRI par plateforme
    if platform_irrs:
        st.subheader("📊 TRI par Plateforme")
        
        # Créer le graphique en barres
        platforms = list(platform_irrs.keys())
        irr_values = [platform_irrs[p]['irr'] for p in platforms]
        investments = [platform_irrs[p]['total_invested'] for p in platforms]
        
        fig = go.Figure()
        
        # Barres TRI avec couleurs conditionnelles
        colors = ['green' if irr > 0 else 'red' for irr in irr_values]
        
        fig.add_trace(go.Bar(
            x=platforms,
            y=irr_values,
            name='TRI (%)',
            marker_color=colors,
            text=[f"{irr:.1f}%" for irr in irr_values],
            textposition='auto'
        ))
        
        fig.update_layout(
            title="TRI par Plateforme",
            xaxis_title="Plateforme",
            yaxis_title="TRI (%)",
            showlegend=False
        )
        
        st.plotly_chart(fig, use_container_width=True)
        
        # Tableau détaillé
        st.subheader("📋 Détail par Plateforme")
        
        platform_details = []
        for platform, data in platform_irrs.items():
            platform_details.append({
                'Plateforme': platform,
                'TRI (%)': f"{data['irr']:.2f}",
                'Investi (€)': f"{data['total_invested']:,.0f}",
                'Retourné (€)': f"{data['total_returned']:,.0f}",
                'Multiple': f"{data['multiple']:.2f}x",
                'Nb Projets': data['nb_projects']
            })
        
        df_details = pd.DataFrame(platform_details)
        st.dataframe(df_details, use_container_width=True, hide_index=True)

def afficher_metriques_risque(rapport_performance: Dict):
    """Afficher les métriques de risque"""
    st.subheader("⚠️ Analyse des Risques")
    
    risk_metrics = rapport_performance.get('risk_metrics', {})
    
    if not risk_metrics:
        st.info("Données insuffisantes pour le calcul des métriques de risque")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        sharpe = risk_metrics.get('sharpe_ratio', 0)
        st.metric(
            "Ratio de Sharpe",
            f"{sharpe:.3f}",
            help="Rendement excédentaire / Volatilité (>1 = bon, >2 = excellent)"
        )
    
    with col2:
        var_5 = risk_metrics.get('var_5pct', 0)
        st.metric(
            "VaR 5%",
            f"{var_5:.2f}%",
            help="Perte maximum avec 95% de confiance"
        )
    
    with col3:
        volatility = risk_metrics.get('volatility', 0)
        st.metric(
            "Volatilité",
            f"{volatility:.1f}%",
            help="Écart-type des rendements annualisé"
        )
    
    with col4:
        max_dd = risk_metrics.get('max_drawdown', 0)
        st.metric(
            "Drawdown Max",
            f"{max_dd:.1f}%",
            help="Baisse maximum depuis un pic"
        )
    
    # Graphique de distribution des risques
    st.subheader("📈 Profil Risque-Rendement")
    
    # Simuler une distribution pour l'affichage (à améliorer avec vraies données)
    returns_simulation = np.random.normal(
        risk_metrics.get('sharpe_ratio', 0) * 0.1, 
        risk_metrics.get('volatility', 10) / 100, 
        1000
    )
    
    fig = go.Figure()
    fig.add_trace(go.Histogram(
        x=returns_simulation * 100,
        nbinsx=50,
        name='Distribution des Rendements',
        marker_color='lightblue'
    ))
    
    # VaR lines
    fig.add_vline(x=var_5, line_dash="dash", line_color="red", 
                  annotation_text=f"VaR 5%: {var_5:.1f}%")
    
    fig.update_layout(
        title="Distribution des Rendements Simulés",
        xaxis_title="Rendement (%)",
        yaxis_title="Fréquence"
    )
    
    st.plotly_chart(fig, use_container_width=True)

def afficher_comparaisons_benchmark(rapport_performance: Dict):
    """Afficher les comparaisons avec les benchmarks"""
    st.subheader("🏆 Comparaison avec les Benchmarks")
    
    benchmarks = rapport_performance.get('benchmark_comparisons', {})
    
    if not benchmarks:
        st.info("Données de benchmark en cours de chargement...")
        return
    
    # Créer le graphique de comparaison
    benchmark_names = list(benchmarks.keys())
    portfolio_returns = [benchmarks[name].get('alpha', 0) for name in benchmark_names]
    benchmark_returns = [benchmarks[name].get('benchmark_return', 0) for name in benchmark_names]
    
    fig = go.Figure()
    
    # Barres groupées
    fig.add_trace(go.Bar(
        name='Votre Portefeuille (Alpha)',
        x=benchmark_names,
        y=portfolio_returns,
        marker_color='lightgreen'
    ))
    
    fig.add_trace(go.Bar(
        name='Benchmark',
        x=benchmark_names,
        y=benchmark_returns,
        marker_color='lightcoral'
    ))
    
    fig.update_layout(
        title="Performance vs Benchmarks (Rendement Annuel %)",
        xaxis_title="Indice",
        yaxis_title="Rendement (%)",
        barmode='group'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tableau détaillé avec Alpha et Beta
    st.subheader("📊 Métriques Comparatives")
    
    comparison_data = []
    for name, data in benchmarks.items():
        comparison_data.append({
            'Benchmark': name,
            'Rendement Benchmark (%)': f"{data.get('benchmark_return', 0):.2f}",
            'Alpha (%)': f"{data.get('alpha', 0):.2f}",
            'Beta': f"{data.get('beta', 1):.3f}",
            'Corrélation': f"{data.get('correlation', 0):.3f}"
        })
    
    if comparison_data:
        df_comparison = pd.DataFrame(comparison_data)
        st.dataframe(df_comparison, use_container_width=True, hide_index=True)
        
        # Explications
        st.info("""
        **Interprétation :**
        - **Alpha** : Performance excédentaire vs benchmark (+ = surperformance)
        - **Beta** : Sensibilité aux mouvements du marché (>1 = plus volatil)
        - **Corrélation** : Degré de synchronisation avec le marché (0-1)
        """)

def afficher_metriques_crowdfunding(rapport_performance: Dict):
    """Afficher les métriques spécifiques au crowdfunding"""
    st.subheader("🏠 Analyse Crowdfunding Immobilier")
    
    cf_metrics = rapport_performance.get('crowdfunding_metrics', {})
    
    if not cf_metrics:
        st.info("Données crowdfunding insuffisantes")
        return
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        default_rate = cf_metrics.get('default_rate', 0)
        color = "inverse" if default_rate > 5 else "normal"
        st.metric(
            "Taux de Défaut",
            f"{default_rate:.1f}%",
            delta_color=color,
            help="Pourcentage de projets en défaut"
        )
    
    with col2:
        delay_rate = cf_metrics.get('delay_rate', 0)
        color = "inverse" if delay_rate > 10 else "normal"
        st.metric(
            "Taux de Retard",
            f"{delay_rate:.1f}%",
            delta_color=color,
            help="Pourcentage de projets en retard"
        )
    
    with col3:
        avg_duration = cf_metrics.get('avg_duration_years', 0)
        st.metric(
            "Durée Moyenne",
            f"{avg_duration:.1f} ans",
            help="Durée moyenne des projets"
        )
    
    with col4:
        weighted_rate = cf_metrics.get('weighted_avg_rate', 0)
        st.metric(
            "Taux Moyen Pondéré",
            f"{weighted_rate:.1f}%",
            help="Taux d'intérêt moyen pondéré par montant"
        )
    
    # Analyse de concentration
    if 'concentration_index' in cf_metrics:
        st.subheader("🎯 Analyse de Diversification")
        
        col1, col2 = st.columns(2)
        
        with col1:
            concentration = cf_metrics.get('concentration_index', 0)
            
            # Interprétation de l'indice de Herfindahl
            if concentration < 0.15:
                diversification = "Excellent"
                color = "green"
            elif concentration < 0.25:
                diversification = "Bon"
                color = "orange"
            else:
                diversification = "Risqué"
                color = "red"
            
            st.markdown(f"""
            <div style="border-left: 4px solid {color}; padding-left: 1rem;">
                <h4>Indice de Concentration</h4>
                <h2 style="color: {color};">{concentration:.3f}</h2>
                <p><strong>Niveau :</strong> {diversification}</p>
            </div>
            """, unsafe_allow_html=True)
        
        with col2:
            top_share = cf_metrics.get('top_promoter_share', 0)
            st.metric(
                "Part du Top Promoteur",
                f"{top_share:.1f}%",
                help="Concentration chez le promoteur principal"
            )

def page_analyse_avancee():
    """Page principale d'analyse avancée"""
    st.title("📈 Analyse de Performance Avancée")
    st.markdown("---")
    
    # Sidebar avec contrôles
    with st.sidebar:
        st.header("🔧 Paramètres d'Analyse")
        
        user_id = st.text_input("ID Utilisateur", value="29dec51d-0772-4e3a-8e8f-1fece8fefe0e")
        
        if st.button("🔄 Actualiser Analyses"):
            st.cache_data.clear()
            st.success("Analyses actualisées!")
        
        # Options d'analyse
        st.subheader("Options")
        show_irr = st.checkbox("Analyse TRI", value=True)
        show_risk = st.checkbox("Métriques de Risque", value=True)
        show_benchmarks = st.checkbox("Comparaisons Benchmark", value=True)
        show_crowdfunding = st.checkbox("Analyse Crowdfunding", value=True)
    
    # Chargement des données
    try:
        with st.spinner("Chargement des analyses avancées..."):
            investissements_df, flux_tresorerie_df, rapport_performance = charger_donnees_avancees(user_id)
        
        if investissements_df.empty:
            st.warning("Aucune donnée trouvée pour cet utilisateur")
            return
        
        # Affichage des métriques selon les options
        if show_irr:
            afficher_metriques_irr(rapport_performance)
            st.markdown("---")
        
        if show_risk:
            afficher_metriques_risque(rapport_performance)
            st.markdown("---")
        
        if show_benchmarks:
            afficher_comparaisons_benchmark(rapport_performance)
            st.markdown("---")
        
        if show_crowdfunding:
            afficher_metriques_crowdfunding(rapport_performance)
            st.markdown("---")
        
        # Résumé exécutif
        st.subheader("📋 Résumé Exécutif")
        
        global_irr = rapport_performance.get('global_irr', {}).get('global_irr', 0)
        risk_metrics = rapport_performance.get('risk_metrics', {})
        sharpe = risk_metrics.get('sharpe_ratio', 0)
        
        # Génération de recommandations automatiques
        recommendations = []
        
        if global_irr > 10:
            recommendations.append("✅ Excellente performance globale avec un TRI supérieur à 10%")
        elif global_irr > 5:
            recommendations.append("✅ Performance satisfaisante")
        else:
            recommendations.append("⚠️ Performance en dessous des attentes, considérer une révision de stratégie")
        
        if sharpe > 1:
            recommendations.append("✅ Bon rapport risque/rendement (Sharpe > 1)")
        elif sharpe > 0.5:
            recommendations.append("⚠️ Rapport risque/rendement acceptable")
        else:
            recommendations.append("❌ Rapport risque/rendement à améliorer")
        
        for rec in recommendations:
            st.write(rec)
        
        # Export du rapport
        if st.button("📄 Générer Rapport PDF"):
            st.info("Fonctionnalité d'export PDF à implémenter")
    
    except Exception as e:
        st.error(f"Erreur lors du chargement de l'analyse : {e}")
        import traceback
        st.text(traceback.format_exc())

if __name__ == "__main__":
    page_analyse_avancee()