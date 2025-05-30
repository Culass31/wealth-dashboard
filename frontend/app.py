import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import numpy as np
from datetime import datetime, timedelta
import sys
import os

# Ajouter le backend au path
sys.path.append(os.path.join(os.path.dirname(__file__), '..'))

from backend.models.database import DatabaseManager
from backend.data.data_loader import DataLoader
from backend.analytics.advanced_metrics import AdvancedMetricsCalculator
from backend.analytics.financial_freedom import FinancialFreedomSimulator, FinancialProfile

# Configuration de la page
st.set_page_config(
    page_title="Wealth Dashboard - Suite Complète",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé unifié
st.markdown("""
<style>
    .main-nav {
        background: linear-gradient(90deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
    }
    .nav-button {
        background: rgba(255,255,255,0.2);
        border: none;
        padding: 0.5rem 1rem;
        margin: 0.2rem;
        border-radius: 0.3rem;
        color: white;
        cursor: pointer;
    }
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
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
</style>
""", unsafe_allow_html=True)

# Variables de session pour la navigation
if 'current_page' not in st.session_state:
    st.session_state.current_page = 'dashboard'

if 'user_id' not in st.session_state:
    st.session_state.user_id = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e"

@st.cache_data(ttl=300)
def charger_donnees_utilisateur(user_id: str):
    """Charger les données utilisateur avec mise en cache"""
    db = DatabaseManager()
    investissements_df = db.get_user_investments(user_id)
    flux_tresorerie_df = db.get_user_cash_flows(user_id)
    return investissements_df, flux_tresorerie_df

@st.cache_data(ttl=300)
def charger_donnees_avancees(user_id: str):
    """Charger les données avec métriques avancées"""
    db = DatabaseManager()
    calculator = AdvancedMetricsCalculator()
    
    investissements_df = db.get_user_investments(user_id)
    flux_tresorerie_df = db.get_user_cash_flows(user_id)
    
    if not investissements_df.empty and not flux_tresorerie_df.empty:
        rapport_performance = calculator.generate_performance_report(investissements_df, flux_tresorerie_df)
    else:
        rapport_performance = {}
    
    return investissements_df, flux_tresorerie_df, rapport_performance

def navigation_bar():
    """Barre de navigation principale"""
    st.markdown("""
    <div class="main-nav">
        <h2 style="color: white; margin: 0;">💰 Wealth Dashboard - Suite Complète</h2>
    </div>
    """, unsafe_allow_html=True)
    
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        if st.button("📊 Dashboard Principal", use_container_width=True):
            st.session_state.current_page = 'dashboard'
            st.rerun()
    
    with col2:
        if st.button("📈 Analyses Avancées", use_container_width=True):
            st.session_state.current_page = 'advanced'
            st.rerun()
    
    with col3:
        if st.button("🎯 Simulateur Liberté", use_container_width=True):
            st.session_state.current_page = 'simulator'
            st.rerun()
    
    with col4:
        if st.button("🏦 Gestion PEA", use_container_width=True):
            st.session_state.current_page = 'pea'
            st.rerun()
    
    with col5:
        if st.button("⚙️ Configuration", use_container_width=True):
            st.session_state.current_page = 'config'
            st.rerun()

def sidebar_commun():
    """Sidebar commun à toutes les pages"""
    with st.sidebar:
        st.header("🔧 Configuration Globale")
        
        # User ID
        user_id = st.text_input("ID Utilisateur", value=st.session_state.user_id)
        if user_id != st.session_state.user_id:
            st.session_state.user_id = user_id
            st.cache_data.clear()
        
        st.markdown("---")
        
        # Actions globales
        if st.button("🔄 Actualiser Toutes les Données"):
            st.cache_data.clear()
            st.success("Données actualisées !")
        
        # Upload de fichiers
        st.subheader("📤 Import de Données")
        
        # Upload crowdfunding
        uploaded_file = st.file_uploader(
            "Fichier Crowdfunding (.xlsx)", 
            type=['xlsx'],
            key="cf_upload"
        )
        
        if uploaded_file:
            plateforme = st.selectbox(
                "Plateforme Crowdfunding",
                ["LBP", "PretUp", "BienPreter", "Homunity"]
            )
            
            if st.button("📊 Charger Crowdfunding"):
                charger_fichier_crowdfunding(uploaded_file, plateforme, user_id)
        
        # Upload PEA
        st.subheader("🏦 Import PEA")
        
        col1, col2 = st.columns(2)
        
        with col1:
            releve_pdf = st.file_uploader(
                "Relevé PEA (.pdf)", 
                type=['pdf'],
                key="releve_upload"
            )
        
        with col2:
            evaluation_pdf = st.file_uploader(
                "Évaluation PEA (.pdf)", 
                type=['pdf'],
                key="eval_upload"
            )
        
        if (releve_pdf or evaluation_pdf) and st.button("🏦 Charger PEA"):
            charger_fichiers_pea(releve_pdf, evaluation_pdf, user_id)

def charger_fichier_crowdfunding(uploaded_file, plateforme, user_id):
    """Charger un fichier de crowdfunding"""
    try:
        # Sauvegarder temporairement
        temp_path = f"temp_{uploaded_file.name}"
        with open(temp_path, "wb") as f:
            f.write(uploaded_file.getbuffer())
        
        # Charger via DataLoader
        loader = DataLoader()
        success = loader.load_platform_data(temp_path, plateforme.lower(), user_id)
        
        if success:
            st.success(f"✅ Données {plateforme} chargées avec succès !")
            st.cache_data.clear()
        else:
            st.error(f"❌ Échec du chargement {plateforme}")
        
        # Nettoyage
        os.remove(temp_path)
        
    except Exception as e:
        st.error(f"Erreur chargement : {e}")

def charger_fichiers_pea(releve_pdf, evaluation_pdf, user_id):
    """Charger les fichiers PEA via le parser"""
    try:
        from backend.data.pea_parser import PEAParser
        
        # Sauvegarder temporairement les PDFs
        releve_path = None
        evaluation_path = None
        
        if releve_pdf:
            releve_path = f"temp_releve_{releve_pdf.name}"
            with open(releve_path, "wb") as f:
                f.write(releve_pdf.getbuffer())
        
        if evaluation_pdf:
            evaluation_path = f"temp_evaluation_{evaluation_pdf.name}"
            with open(evaluation_path, "wb") as f:
                f.write(evaluation_pdf.getbuffer())
        
        # Parser
        parser = PEAParser(user_id)
        investissements, flux_tresorerie, positions = parser.parse_pdf_files(
            releve_path, evaluation_path
        )
        
        # Charger en BDD
        db = DatabaseManager()
        success_inv = db.insert_investments(investissements) if investissements else True
        success_cf = db.insert_cash_flows(flux_tresorerie) if flux_tresorerie else True
        
        if success_inv and success_cf:
            st.success(f"✅ PEA chargé : {len(investissements)} investissements, {len(flux_tresorerie)} transactions")
            st.cache_data.clear()
        else:
            st.error("❌ Échec du chargement PEA")
        
        # Nettoyage
        if releve_path and os.path.exists(releve_path):
            os.remove(releve_path)
        if evaluation_path and os.path.exists(evaluation_path):
            os.remove(evaluation_path)
        
    except Exception as e:
        st.error(f"Erreur parser PEA : {e}")
        import traceback
        st.text(traceback.format_exc())

def calculer_metriques_base(investissements_df: pd.DataFrame, flux_tresorerie_df: pd.DataFrame):
    """Calculer les métriques de base pour le dashboard principal"""
    metriques = {}
    
    if not investissements_df.empty:
        metriques['total_investi'] = investissements_df['invested_amount'].sum()
        metriques['repartition_plateforme'] = investissements_df.groupby('platform')['invested_amount'].sum()
        metriques['repartition_statut'] = investissements_df['status'].value_counts()
        metriques['repartition_actifs'] = investissements_df.groupby('asset_class')['invested_amount'].sum()
    
    if not flux_tresorerie_df.empty:
        flux_tresorerie_df['transaction_date'] = pd.to_datetime(flux_tresorerie_df['transaction_date'], errors='coerce')
        
        flux_entrants = flux_tresorerie_df[flux_tresorerie_df['flow_direction'] == 'in']
        flux_sortants = flux_tresorerie_df[flux_tresorerie_df['flow_direction'] == 'out']
        
        total_entrees = flux_entrants['gross_amount'].sum()
        total_sorties = flux_sortants['gross_amount'].sum()
        
        metriques['total_entrees'] = total_entrees
        metriques['total_sorties'] = total_sorties
        metriques['performance_nette'] = total_entrees - total_sorties
        
        # Flux mensuels
        flux_tresorerie_df_clean = flux_tresorerie_df.dropna(subset=['transaction_date'])
        if not flux_tresorerie_df_clean.empty:
            flux_tresorerie_df_clean['annee_mois'] = flux_tresorerie_df_clean['transaction_date'].dt.to_period('M')
            flux_mensuels = flux_tresorerie_df_clean.groupby('annee_mois')['net_amount'].sum()
            metriques['flux_mensuels'] = flux_mensuels
    
    return metriques

# ===== PAGES =====

def page_dashboard_principal():
    """Page dashboard principal (existante mais améliorée)"""
    st.header("📊 Dashboard Principal")
    st.markdown("Vue d'ensemble de votre patrimoine")
    
    try:
        investissements_df, flux_tresorerie_df = charger_donnees_utilisateur(st.session_state.user_id)
        
        if investissements_df.empty and flux_tresorerie_df.empty:
            st.warning("Aucune donnée trouvée. Utilisez la barre latérale pour charger vos fichiers.")
            return
        
        metriques = calculer_metriques_base(investissements_df, flux_tresorerie_df)
        
        # Métriques principales
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_investi = metriques.get('total_investi', 0)
            st.metric("💸 Total Investi", f"{total_investi:,.0f} €")
        
        with col2:
            total_entrees = metriques.get('total_entrees', 0)
            st.metric("💰 Total Retours", f"{total_entrees:,.0f} €")
        
        with col3:
            performance_nette = metriques.get('performance_nette', 0)
            delta_color = "normal" if performance_nette >= 0 else "inverse"
            st.metric(
                "📊 Performance Nette",
                f"{performance_nette:,.0f} €",
                f"{(performance_nette/total_investi)*100:.1f}%" if total_investi > 0 else "0%",
                delta_color=delta_color
            )
        
        with col4:
            projets_actifs = len(investissements_df[investissements_df['status'] == 'active']) if not investissements_df.empty else 0
            st.metric("🏗️ Projets Actifs", projets_actifs)
        
        st.markdown("---")
        
        # Graphiques
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Répartition par Plateforme")
            if 'repartition_plateforme' in metriques and not metriques['repartition_plateforme'].empty:
                fig = px.pie(
                    values=metriques['repartition_plateforme'].values,
                    names=metriques['repartition_plateforme'].index,
                    title="Allocation par Plateforme"
                )
                st.plotly_chart(fig, use_container_width=True)
        
        with col2:
            st.subheader("🎯 Statut des Projets")
            if 'repartition_statut' in metriques and not metriques['repartition_statut'].empty:
                couleurs_statut = {
                    'active': '#2ca02c',
                    'completed': '#1f77b4', 
                    'delayed': '#ff7f0e',
                    'defaulted': '#d62728',
                    'in_procedure': '#9467bd'
                }
                
                fig = px.bar(
                    x=metriques['repartition_statut'].index,
                    y=metriques['repartition_statut'].values,
                    title="Projets par Statut",
                    color=metriques['repartition_statut'].index,
                    color_discrete_map=couleurs_statut
                )
                fig.update_layout(showlegend=False)
                st.plotly_chart(fig, use_container_width=True)
        
        # Flux mensuels
        if 'flux_mensuels' in metriques and not metriques['flux_mensuels'].empty:
            st.subheader("💰 Évolution des Flux de Trésorerie")
            flux_mensuels = metriques['flux_mensuels']
            
            fig = go.Figure()
            fig.add_trace(go.Bar(
                x=[str(periode) for periode in flux_mensuels.index],
                y=flux_mensuels.values,
                marker_color=['green' if x > 0 else 'red' for x in flux_mensuels.values],
                name="Flux Mensuel"
            ))
            
            fig.update_layout(
                title="Flux de Trésorerie Mensuels",
                xaxis_title="Mois",
                yaxis_title="Montant (€)",
                showlegend=False
            )
            st.plotly_chart(fig, use_container_width=True)
        
    except Exception as e:
        st.error(f"Erreur chargement dashboard : {e}")

def page_analyses_avancees():
    """Page analyses avancées (TRI, Sharpe, etc.)"""
    st.header("📈 Analyses Avancées")
    st.markdown("Métriques financières avancées et comparaisons")
    
    try:
        investissements_df, flux_tresorerie_df, rapport_performance = charger_donnees_avancees(st.session_state.user_id)
        
        if investissements_df.empty:
            st.warning("Données insuffisantes pour les analyses avancées")
            return
        
        # TRI Section
        st.subheader("🎯 Analyse TRI (Taux de Rendement Interne)")
        
        global_irr = rapport_performance.get('global_irr', {})
        platform_irrs = rapport_performance.get('platform_irrs', {})
        
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
            st.metric("Marge Bénéficiaire", f"{profit_margin:.1f}%")
        
        with col3:
            total_invested = global_irr.get('total_invested', 0)
            st.metric("Capital Total", f"{total_invested:,.0f} €")
        
        # TRI par plateforme
        if platform_irrs:
            st.subheader("📊 TRI par Plateforme")
            
            platforms = list(platform_irrs.keys())
            irr_values = [platform_irrs[p]['irr'] for p in platforms]
            
            fig = go.Figure()
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
        
        # Métriques de risque
        risk_metrics = rapport_performance.get('risk_metrics', {})
        
        if risk_metrics:
            st.subheader("⚠️ Métriques de Risque")
            
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                sharpe = risk_metrics.get('sharpe_ratio', 0)
                st.metric("Ratio de Sharpe", f"{sharpe:.3f}")
            
            with col2:
                var_5 = risk_metrics.get('var_5pct', 0)
                st.metric("VaR 5%", f"{var_5:.2f}%")
            
            with col3:
                volatility = risk_metrics.get('volatility', 0)
                st.metric("Volatilité", f"{volatility:.1f}%")
            
            with col4:
                max_dd = risk_metrics.get('max_drawdown', 0)
                st.metric("Drawdown Max", f"{max_dd:.1f}%")
        
    except Exception as e:
        st.error(f"Erreur analyses avancées : {e}")

def page_simulateur():
    """Page simulateur liberté financière"""
    st.header("🎯 Simulateur de Liberté Financière")
    st.markdown("Planifiez votre indépendance financière")
    
    # Configuration du profil
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("👤 Votre Profil")
        age = st.slider("Âge actuel", 25, 65, 43)
        target_age = st.slider("Âge cible liberté", age + 5, 70, 55)
        current_patrimoine = st.number_input("Patrimoine actuel (€)", 0, 1000000, 50000, step=5000)
    
    with col2:
        st.subheader("💰 Paramètres Financiers")
        monthly_investment = st.number_input("Investissement mensuel (€)", 0, 10000, 1500, step=100)
        monthly_expenses = st.number_input("Dépenses mensuelles souhaitées (€)", 1000, 20000, 3000, step=100)
        risk_tolerance = st.selectbox("Tolérance au risque", ["conservative", "moderate", "aggressive"], index=1)
    
    # Créer le profil et simulateur
    profile = FinancialProfile(
        age=age,
        target_age=target_age,
        current_patrimoine=current_patrimoine,
        monthly_investment=monthly_investment,
        monthly_expenses=monthly_expenses,
        risk_tolerance=risk_tolerance
    )
    
    simulator = FinancialFreedomSimulator(profile)
    
    # Simulation
    if st.button("🚀 Lancer la Simulation Monte Carlo", type="primary"):
        with st.spinner("Simulation en cours..."):
            results = simulator.run_monte_carlo(1000)
        
        # Résultats
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
            st.metric("Patrimoine Médian", f"{results['median_final_value']:,.0f} €")
        
        with col3:
            required = results['required_patrimoine']
            st.metric("Objectif Requis", f"{required:,.0f} €")
        
        # Graphique trajectoires
        st.subheader("📈 Trajectoires de Patrimoine")
        
        fig = go.Figure()
        
        # Quelques trajectoires
        import random
        sample_paths = random.sample(results['all_paths'], min(50, len(results['all_paths'])))
        years = list(range(len(sample_paths[0])))
        
        for i, path in enumerate(sample_paths):
            fig.add_trace(go.Scatter(
                x=years,
                y=path,
                mode='lines',
                line=dict(width=1, color='lightblue'),
                showlegend=False
            ))
        
        # Ligne médiane
        median_path = np.median(results['all_paths'], axis=0)
        fig.add_trace(go.Scatter(
            x=years,
            y=median_path,
            mode='lines',
            line=dict(width=3, color='blue'),
            name='Médiane'
        ))
        
        # Ligne objectif
        fig.add_hline(y=required, line_dash="dash", line_color="red", annotation_text=f"Objectif: {required:,.0f}€")
        
        fig.update_layout(
            title="Évolution du Patrimoine - Simulation Monte Carlo",
            xaxis_title="Années",
            yaxis_title="Patrimoine (€)"
        )
        
        st.plotly_chart(fig, use_container_width=True)

def page_gestion_pea():
    """Page spécifique à la gestion PEA"""
    st.header("🏦 Gestion PEA")
    st.markdown("Parser et analyser vos données PEA Bourse Direct")
    
    # Instructions
    st.info("""
    **Comment utiliser le parser PEA :**
    1. Téléchargez vos PDF depuis votre espace Bourse Direct
    2. Utilisez la barre latérale pour charger les fichiers
    3. Le système extraira automatiquement vos transactions et positions
    """)
    
    # Afficher les données PEA existantes
    try:
        db = DatabaseManager()
        investissements_df = db.get_user_investments(st.session_state.user_id, platform='PEA')
        flux_tresorerie_df = db.get_user_cash_flows(st.session_state.user_id)
        
        # Filtrer les flux PEA
        flux_pea_df = flux_tresorerie_df[
            flux_tresorerie_df['payment_method'].str.contains('PEA', case=False, na=False)
        ] if not flux_tresorerie_df.empty else pd.DataFrame()
        
        if not investissements_df.empty:
            st.subheader("📊 Positions PEA Actuelles")
            
            # Métriques PEA
            col1, col2, col3 = st.columns(3)
            
            with col1:
                total_pea = investissements_df['invested_amount'].sum()
                st.metric("💰 Valorisation PEA", f"{total_pea:,.0f} €")
            
            with col2:
                nb_positions = len(investissements_df)
                st.metric("📈 Nombre de Positions", nb_positions)
            
            with col3:
                if not flux_pea_df.empty:
                    dividendes = flux_pea_df[flux_pea_df['flow_type'] == 'dividend']['gross_amount'].sum()
                    st.metric("💎 Dividendes Reçus", f"{dividendes:,.0f} €")
            
            # Répartition par classe d'actifs
            if 'asset_class' in investissements_df.columns:
                st.subheader("🎯 Répartition par Type d'Actif")
                
                repartition = investissements_df.groupby('asset_class')['invested_amount'].sum()
                
                fig = px.pie(
                    values=repartition.values,
                    names=repartition.index,
                    title="Allocation PEA par Classe d'Actifs"
                )
                st.plotly_chart(fig, use_container_width=True)
            
            # Tableau des positions
            st.subheader("📋 Détail des Positions")
            
            display_columns = ['project_name', 'invested_amount', 'asset_class', 'status']
            available_columns = [col for col in display_columns if col in investissements_df.columns]
            
            if available_columns:
                display_df = investissements_df[available_columns].copy()
                
                if 'invested_amount' in display_df.columns:
                    display_df['invested_amount'] = display_df['invested_amount'].apply(lambda x: f"{x:,.0f} €")
                
                st.dataframe(display_df, use_container_width=True, hide_index=True)
        
        else:
            st.warning("Aucune donnée PEA trouvée. Utilisez la barre latérale pour charger vos fichiers PDF.")
    
    except Exception as e:
        st.error(f"Erreur affichage PEA : {e}")

def page_configuration():
    """Page de configuration et maintenance"""
    st.header("⚙️ Configuration & Maintenance")
    st.markdown("Paramètres globaux et outils de maintenance")
    
    # Informations système
    st.subheader("ℹ️ Informations Système")
    
    try:
        db = DatabaseManager()
        investissements_df = db.get_user_investments(st.session_state.user_id)
        flux_tresorerie_df = db.get_user_cash_flows(st.session_state.user_id)
        
        col1, col2, col3 = st.columns(3)
        
        with col1:
            st.metric("📊 Total Investissements", len(investissements_df))
        
        with col2:
            st.metric("💰 Total Flux", len(flux_tresorerie_df))
        
        with col3:
            if not investissements_df.empty:
                platforms = investissements_df['platform'].nunique()
                st.metric("🏢 Plateformes", platforms)
        
        # Répartition par plateforme
        if not investissements_df.empty:
            st.subheader("📈 Répartition des Données")
            
            platform_stats = investissements_df.groupby('platform').agg({
                'invested_amount': ['count', 'sum']
            }).round(2)
            
            st.dataframe(platform_stats, use_container_width=True)
    
    except Exception as e:
        st.error(f"Erreur informations système : {e}")
    
    # Outils de maintenance
    st.subheader("🔧 Outils de Maintenance")
    
    col1, col2 = st.columns(2)
    
    with col1:
        if st.button("🗑️ Vider Cache", type="secondary"):
            st.cache_data.clear()
            st.success("Cache vidé !")
    
    with col2:
        if st.button("⚠️ Supprimer Toutes Données", type="secondary"):
            if st.checkbox("Je confirme la suppression"):
                try:
                    db = DatabaseManager()
                    db.clear_user_data(st.session_state.user_id)
                    st.success("Données supprimées !")
                    st.cache_data.clear()
                except Exception as e:
                    st.error(f"Erreur suppression : {e}")

# ===== MAIN APPLICATION =====

def main():
    """Application principale avec navigation"""
    
    # Navigation
    navigation_bar()
    
    # Sidebar commun
    sidebar_commun()
    
    # Router vers la bonne page
    if st.session_state.current_page == 'dashboard':
        page_dashboard_principal()
    elif st.session_state.current_page == 'advanced':
        page_analyses_avancees()
    elif st.session_state.current_page == 'simulator':
        page_simulateur()
    elif st.session_state.current_page == 'pea':
        page_gestion_pea()
    elif st.session_state.current_page == 'config':
        page_configuration()

if __name__ == "__main__":
    main()