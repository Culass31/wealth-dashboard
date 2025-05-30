# ===== frontend/expert_dashboard.py - DASHBOARD EXPERT PATRIMOINE =====
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
from backend.data.data_loader import CorrectedDataLoader
from backend.analytics.expert_metrics import ExpertPatrimoineCalculator

# Configuration de la page
st.set_page_config(
    page_title="Expert Patrimoine Dashboard",
    page_icon="💎",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé expert
st.markdown("""
<style>
    .expert-header {
        background: linear-gradient(90deg, #2C3E50 0%, #34495E 100%);
        color: white;
        padding: 2rem;
        border-radius: 0.5rem;
        margin-bottom: 2rem;
        text-align: center;
    }
    .metric-expert {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        color: white;
        padding: 1.5rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
        text-align: center;
    }
    .tri-excellent {
        background: linear-gradient(135deg, #11998e 0%, #38ef7d 100%);
    }
    .tri-warning {
        background: linear-gradient(135deg, #ff7f0e 0%, #ffbb33 100%);
    }
    .tri-danger {
        background: linear-gradient(135deg, #fc4a1a 0%, #f7b733 100%);
    }
    .concentration-low {
        border-left: 4px solid #28a745;
        padding-left: 1rem;
    }
    .concentration-high {
        border-left: 4px solid #dc3545;
        padding-left: 1rem;
    }
    .performance-card {
        border: 1px solid #e9ecef;
        border-radius: 0.5rem;
        padding: 1rem;
        margin: 0.5rem 0;
        background: #f8f9fa;
    }
    .recommendation {
        background: #d4edda;
        border: 1px solid #c3e6cb;
        border-radius: 0.25rem;
        padding: 0.75rem;
        margin: 0.5rem 0;
    }
    .warning-rec {
        background: #fff3cd;
        border: 1px solid #ffeaa7;
    }
    .danger-rec {
        background: #f8d7da;
        border: 1px solid #f5c6cb;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data(ttl=300)
def charger_donnees_expert(user_id: str):
    """Charger les données avec calculs expert complets"""
    db = DatabaseManager()
    calculator = ExpertPatrimoineCalculator()
    
    # Données de base
    investissements_df = db.get_user_investments(user_id)
    flux_tresorerie_df = db.get_user_cash_flows(user_id)
    
    # Rapport expert complet
    if not investissements_df.empty:
        rapport_expert = calculator.generate_expert_report(investissements_df, flux_tresorerie_df)
    else:
        rapport_expert = {}
    
    return investissements_df, flux_tresorerie_df, rapport_expert

def afficher_header_expert():
    """Header principal du dashboard expert"""
    st.markdown("""
    <div class="expert-header">
        <h1>💎 Dashboard Expert Gestion de Patrimoine</h1>
        <p>Analyse approfondie avec métriques avancées • TRI • Duration • Concentration • Stress Test</p>
    </div>
    """, unsafe_allow_html=True)

def afficher_kpi_globaux(rapport_expert: dict):
    """Afficher les KPI globaux en haut de page"""
    
    st.subheader("📊 KPI Globaux du Portefeuille")
    
    # Extraire les données clés
    capital_data = rapport_expert.get('capital_en_cours', {})
    tri_data = rapport_expert.get('tri_expert', {})
    reinvest_data = rapport_expert.get('taux_reinvestissement', {})
    
    # Calculs globaux
    total_capital_en_cours = sum(data.get('capital_en_cours', 0) for data in capital_data.values())
    total_capital_investi = sum(data.get('capital_investi', 0) for data in capital_data.values())
    
    # TRI moyen pondéré
    tri_moyenne = 0
    if tri_data:
        total_depose = sum(data.get('total_depose', 0) for data in tri_data.values())
        if total_depose > 0:
            tri_pondere = sum(data.get('tri_annuel', 0) * data.get('total_depose', 0) for data in tri_data.values())
            tri_moyenne = tri_pondere / total_depose
    
    # Taux de réinvestissement global
    total_argent_frais = sum(data.get('argent_frais_depose', 0) for data in reinvest_data.values())
    total_investi_projets = sum(data.get('total_investi', 0) for data in reinvest_data.values())
    taux_reinvest_global = (1 - (total_argent_frais / total_investi_projets)) * 100 if total_investi_projets > 0 else 0
    
    # Affichage en colonnes
    col1, col2, col3, col4, col5 = st.columns(5)
    
    with col1:
        st.metric(
            "💰 Capital en Cours", 
            f"{total_capital_en_cours:,.0f} €",
            delta=f"{((total_capital_en_cours/total_capital_investi)-1)*100:.1f}%" if total_capital_investi > 0 else None
        )
    
    with col2:
        tri_color = "normal"
        if tri_moyenne > 8:
            tri_color = "normal"
        elif tri_moyenne < 4:
            tri_color = "inverse"
        
        st.metric(
            "📈 TRI Moyen Pondéré", 
            f"{tri_moyenne:.1f}%",
            delta=f"{tri_moyenne - 3.5:.1f}% vs OAT 10Y",
            delta_color=tri_color
        )
    
    with col3:
        st.metric(
            "🔄 Taux Réinvestissement", 
            f"{taux_reinvest_global:.1f}%",
            help="Pourcentage de réinvestissement des remboursements"
        )
    
    with col4:
        nb_plateformes = len(capital_data)
        st.metric(
            "🏢 Plateformes Actives", 
            nb_plateformes,
            help="Nombre de plateformes avec du capital en cours"
        )
    
    with col5:
        # Performance vs benchmark
        outperformance = tri_moyenne - 3.5  # vs OAT 10Y
        st.metric(
            "🎯 Outperformance", 
            f"{outperformance:+.1f}%",
            delta_color="normal" if outperformance > 0 else "inverse"
        )

def afficher_capital_en_cours(rapport_expert: dict):
    """Afficher l'analyse du capital en cours"""
    
    st.subheader("💰 Analyse du Capital en Cours")
    
    capital_data = rapport_expert.get('capital_en_cours', {})
    
    if not capital_data:
        st.warning("Données de capital en cours non disponibles")
        return
    
    # Graphique en barres empilées
    platforms = list(capital_data.keys())
    capital_investi = [data['capital_investi'] for data in capital_data.values()]
    capital_rembourse = [data['capital_rembourse'] for data in capital_data.values()]
    capital_en_cours = [data['capital_en_cours'] for data in capital_data.values()]
    
    fig = go.Figure()
    
    fig.add_trace(go.Bar(
        name='Capital Remboursé',
        x=platforms,
        y=capital_rembourse,
        marker_color='lightgreen',
        text=[f"{val:,.0f}€" for val in capital_rembourse],
        textposition='auto'
    ))
    
    fig.add_trace(go.Bar(
        name='Capital en Cours',
        x=platforms,
        y=capital_en_cours,
        marker_color='lightblue',
        text=[f"{val:,.0f}€" for val in capital_en_cours],
        textposition='auto'
    ))
    
    fig.update_layout(
        title="Capital Investi vs Remboursé vs En Cours",
        xaxis_title="Plateforme",
        yaxis_title="Montant (€)",
        barmode='stack'
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tableau détaillé
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📋 Détail par Plateforme")
        
        detail_data = []
        for platform, data in capital_data.items():
            detail_data.append({
                'Plateforme': platform,
                'Capital Investi': f"{data['capital_investi']:,.0f} €",
                'Capital Remboursé': f"{data['capital_rembourse']:,.0f} €",
                'Capital en Cours': f"{data['capital_en_cours']:,.0f} €",
                'Taux Remboursement': f"{data['taux_remboursement']:.1f}%"
            })
        
        df_detail = pd.DataFrame(detail_data)
        st.dataframe(df_detail, use_container_width=True, hide_index=True)
    
    with col2:
        # Graphique circulaire capital en cours
        st.subheader("🥧 Répartition Capital en Cours")
        
        if any(val > 0 for val in capital_en_cours):
            fig_pie = px.pie(
                values=capital_en_cours,
                names=platforms,
                title="Répartition du Capital en Cours"
            )
            st.plotly_chart(fig_pie, use_container_width=True)

def afficher_tri_expert(rapport_expert: dict):
    """Afficher l'analyse TRI expert avec dates réelles"""
    
    st.subheader("🎯 Analyse TRI Expert (Dates Réelles)")
    
    tri_data = rapport_expert.get('tri_expert', {})
    
    if not tri_data:
        st.warning("Données TRI expert non disponibles")
        return
    
    # Métriques TRI par plateforme
    platforms = list(tri_data.keys())
    tri_values = [data['tri_annuel'] for data in tri_data.values()]
    
    # Graphique TRI avec seuils de couleur
    fig = go.Figure()
    
    colors = []
    for tri in tri_values:
        if tri > 8:
            colors.append('#28a745')  # Vert excellent
        elif tri > 5:
            colors.append('#17a2b8')  # Bleu bon
        elif tri > 2:
            colors.append('#ffc107')  # Jaune moyen
        else:
            colors.append('#dc3545')  # Rouge faible
    
    fig.add_trace(go.Bar(
        x=platforms,
        y=tri_values,
        marker_color=colors,
        text=[f"{tri:.1f}%" for tri in tri_values],
        textposition='auto'
    ))
    
    # Ligne benchmark OAT 10Y
    fig.add_hline(y=3.5, line_dash="dash", line_color="red", 
                  annotation_text="OAT 10Y (3.5%)")
    
    # Ligne benchmark immobilier
    fig.add_hline(y=5.5, line_dash="dash", line_color="orange", 
                  annotation_text="Benchmark Immobilier (5.5%)")
    
    fig.update_layout(
        title="TRI Annuel par Plateforme vs Benchmarks",
        xaxis_title="Plateforme",
        yaxis_title="TRI (%)",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tableau détaillé TRI
    st.subheader("📊 Métriques TRI Détaillées")
    
    tri_detail = []
    for platform, data in tri_data.items():
        tri_detail.append({
            'Plateforme': platform,
            'TRI Annuel': f"{data['tri_annuel']:.2f}%",
            'Total Déposé': f"{data['total_depose']:,.0f} €",
            'Total Retourné': f"{data['total_retourne']:,.0f} €",
            'Multiple': f"{data['multiple']:.2f}x",
            'Profit Net': f"{data['profit_net']:,.0f} €",
            'Outperformance vs OAT': f"{data['outperformance_vs_oat']:+.1f}%",
            'Période (jours)': data['periode_jours']
        })
    
    df_tri = pd.DataFrame(tri_detail)
    st.dataframe(df_tri, use_container_width=True, hide_index=True)

def afficher_taux_reinvestissement(rapport_expert: dict):
    """Afficher l'analyse des taux de réinvestissement"""
    
    st.subheader("🔄 Analyse Taux de Réinvestissement")
    
    reinvest_data = rapport_expert.get('taux_reinvestissement', {})
    
    if not reinvest_data:
        st.warning("Données de réinvestissement non disponibles")
        return
    
    # Graphique effet boule de neige
    platforms = list(reinvest_data.keys())
    taux_reinvest = [data['taux_reinvestissement_pct'] for data in reinvest_data.values()]
    effet_boule_neige = [data['effet_boule_neige'] for data in reinvest_data.values()]
    
    fig = make_subplots(
        rows=1, cols=2,
        subplot_titles=('Taux de Réinvestissement (%)', 'Effet Boule de Neige (Multiple)'),
        specs=[[{"secondary_y": False}, {"secondary_y": False}]]
    )
    
    # Graphique 1 : Taux de réinvestissement
    colors_reinvest = ['green' if taux > 70 else 'orange' if taux > 40 else 'red' for taux in taux_reinvest]
    
    fig.add_trace(
        go.Bar(x=platforms, y=taux_reinvest, marker_color=colors_reinvest, name='Taux Réinvest.'),
        row=1, col=1
    )
    
    # Graphique 2 : Effet boule de neige
    fig.add_trace(
        go.Bar(x=platforms, y=effet_boule_neige, marker_color='lightblue', name='Effet Boule de Neige'),
        row=1, col=2
    )
    
    fig.update_layout(
        title_text="Analyse du Réinvestissement et Effet Boule de Neige",
        showlegend=False
    )
    
    st.plotly_chart(fig, use_container_width=True)
    
    # Tableau détaillé
    col1, col2 = st.columns(2)
    
    with col1:
        st.subheader("📈 Détail Réinvestissement")
        
        reinvest_detail = []
        for platform, data in reinvest_data.items():
            reinvest_detail.append({
                'Plateforme': platform,
                'Argent Frais': f"{data['argent_frais_depose']:,.0f} €",
                'Total Investi': f"{data['total_investi']:,.0f} €",
                'Capital Réinvesti': f"{data['capital_reinvesti']:,.0f} €",
                'Taux Réinvest.': f"{data['taux_reinvestissement_pct']:.1f}%",
                'Effet Boule Neige': f"{data['effet_boule_neige']:.2f}x"
            })
        
        df_reinvest = pd.DataFrame(reinvest_detail)
        st.dataframe(df_reinvest, use_container_width=True, hide_index=True)
    
    with col2:
        st.subheader("💡 Analyse")
        
        for platform, data in reinvest_data.items():
            taux = data['taux_reinvestissement_pct']
            effet = data['effet_boule_neige']
            
            if taux > 70:
                st.success(f"✅ **{platform}**: Excellent réinvestissement ({taux:.0f}%)")
            elif taux > 40:
                st.warning(f"⚠️ **{platform}**: Réinvestissement moyen ({taux:.0f}%)")
            else:
                st.error(f"❌ **{platform}**: Faible réinvestissement ({taux:.0f}%)")
            
            if effet > 2:
                st.info(f"🚀 Effet multiplicateur x{effet:.1f}")

def afficher_duration_immobilisation(rapport_expert: dict):
    """Afficher l'analyse de duration et immobilisation"""
    
    st.subheader("⏱️ Analyse Duration et Immobilisation")
    
    duration_data = rapport_expert.get('duration_analysis', {})
    
    if not duration_data:
        st.warning("Données de duration non disponibles")
        return
    
    # Métriques duration
    col1, col2, col3 = st.columns(3)
    
    platforms = list(duration_data.keys())
    
    for i, (platform, data) in enumerate(duration_data.items()):
        col = [col1, col2, col3][i % 3]
        
        with col:
            duration_moy = data['duration_moyenne_mois']
            
            st.markdown(f"""
            <div class="metric-expert">
                <h4>{platform}</h4>
                <h2>{duration_moy:.1f} mois</h2>
                <p>Duration moyenne</p>
            </div>
            """, unsafe_allow_html=True)
            
            # Indicateur retard
            taux_retard = data['taux_retard_pct']
            if taux_retard > 10:
                st.error(f"⚠️ Retards: {taux_retard:.1f}%")
            elif taux_retard > 5:
                st.warning(f"⚠️ Retards: {taux_retard:.1f}%")
            else:
                st.success(f"✅ Retards: {taux_retard:.1f}%")
    
    # Graphique répartition échéances
    st.subheader("📊 Répartition par Échéance")
    
    fig = go.Figure()
    
    for platform, data in duration_data.items():
        repartition = data['repartition_echeances']
        
        fig.add_trace(go.Bar(
            name=platform,
            x=['< 6 mois', '6-12 mois', '> 12 mois'],
            y=[repartition['court_terme_6m'], repartition['moyen_terme_6_12m'], repartition['long_terme_12m_plus']],
            text=[repartition['court_terme_6m'], repartition['moyen_terme_6_12m'], repartition['long_terme_12m_plus']],
            textposition='auto'
        ))
    
    fig.update_layout(
        title="Nombre de Projets par Échéance",
        xaxis_title="Période",
        yaxis_title="Nombre de Projets",
        barmode='group'
    )
    
    st.plotly_chart(fig, use_container_width=True)

def afficher_concentration_risk(rapport_expert: dict):
    """Afficher l'analyse de concentration"""
    
    st.subheader("🎯 Analyse Risque de Concentration")
    
    concentration_data = rapport_expert.get('concentration_risk', {})
    
    if not concentration_data:
        st.warning("Données de concentration non disponibles")
        return
    
    # Métriques concentration par plateforme
    for platform, data in concentration_data.items():
        herfindahl = data['herfindahl_index']
        level = data['concentration_level']
        top_1_share = data['top_1_share_pct']
        nb_emetteurs = data['nombre_emetteurs_total']
        
        # Couleur selon niveau
        if level == "Faible":
            css_class = "concentration-low"
            color = "success"
        elif level in ["Élevée", "Très élevée"]:
            css_class = "concentration-high"
            color = "error"
        else:
            css_class = "concentration-low"
            color = "warning"
        
        st.markdown(f"""
        <div class="{css_class}">
            <h4>{platform} - Concentration {level}</h4>
            <ul>
                <li><strong>Indice Herfindahl:</strong> {herfindahl:.3f}</li>
                <li><strong>Part du top émetteur:</strong> {top_1_share:.1f}%</li>
                <li><strong>Nombre d'émetteurs:</strong> {nb_emetteurs}</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)
        
        # Top émetteurs
        if 'top_emetteurs' in data:
            with st.expander(f"🔍 Top Émetteurs {platform}"):
                top_data = []
                for emetteur, info in data['top_emetteurs'].items():
                    top_data.append({
                        'Émetteur': emetteur,
                        'Montant': f"{info['montant']:,.0f} €",
                        'Part': f"{info['part_pct']:.1f}%"
                    })
                
                df_top = pd.DataFrame(top_data)
                st.dataframe(df_top, use_container_width=True, hide_index=True)

def afficher_stress_test(rapport_expert: dict):
    """Afficher les résultats du stress test"""
    
    st.subheader("⚠️ Stress Test du Portefeuille")
    
    stress_data = rapport_expert.get('stress_test', {})
    
    if not stress_data:
        st.warning("Données de stress test non disponibles")
        return
    
    # Affichage par plateforme et scénario
    for platform, scenarios in stress_data.items():
        st.subheader(f"📊 {platform}")
        
        cols = st.columns(len(scenarios))
        
        for i, (scenario_name, scenario_data) in enumerate(scenarios.items()):
            with cols[i]:
                scenario_title = {
                    'defaut_plus_gros_emetteur': '💥 Défaut Plus Gros Émetteur',
                    'retard_50_pct_projets': '⏱️ Retard 50% Projets',
                    'baisse_valorisation_20pct': '📉 Baisse Valorisation -20%'
                }.get(scenario_name, scenario_name)
                
                st.markdown(f"**{scenario_title}**")
                
                if 'perte_absolue' in scenario_data:
                    perte = scenario_data['perte_absolue']
                    perte_pct = scenario_data.get('perte_pct_platform', 0)
                    st.error(f"Perte: {perte:,.0f} € ({perte_pct:.1f}%)")
                
                if 'capital_immobilise_supplementaire' in scenario_data:
                    capital_immo = scenario_data['capital_immobilise_supplementaire']
                    impact_liquidite = scenario_data.get('impact_liquidite_pct', 0)
                    st.warning(f"Capital bloqué: {capital_immo:,.0f} € ({impact_liquidite:.1f}%)")
                
                if 'nouvelle_valorisation' in scenario_data:
                    nouvelle_val = scenario_data['nouvelle_valorisation']
                    st.info(f"Nouvelle valorisation: {nouvelle_val:,.0f} €")

def afficher_recommandations_expert(rapport_expert: dict):
    """Afficher les recommandations automatiques"""
    
    st.subheader("💡 Recommandations Expert")
    
    recommandations = rapport_expert.get('recommandations', [])
    
    if not recommandations:
        st.info("Aucune recommandation générée")
        return
    
    for rec in recommandations:
        # Classification des recommandations
        if rec.startswith('✅'):
            st.markdown(f'<div class="recommendation">{rec}</div>', unsafe_allow_html=True)
        elif rec.startswith('⚠️'):
            st.markdown(f'<div class="recommendation warning-rec">{rec}</div>', unsafe_allow_html=True)
        elif rec.startswith('❌'):
            st.markdown(f'<div class="recommendation danger-rec">{rec}</div>', unsafe_allow_html=True)
        else:
            st.markdown(f'<div class="recommendation">{rec}</div>', unsafe_allow_html=True)

def sidebar_expert():
    """Sidebar avec contrôles expert"""
    
    with st.sidebar:
        st.header("🔧 Configuration Expert")
        
        # User ID
        user_id = st.text_input("ID Utilisateur", value="29dec51d-0772-4e3a-8e8f-1fece8fefe0e")
        
        # Actions
        col1, col2 = st.columns(2)
        with col1:
            if st.button("🔄 Actualiser"):
                st.cache_data.clear()
                st.success("Actualisé!")
        
        with col2:
            if st.button("📥 Charger Données"):
                with st.spinner("Chargement..."):
                    from backend.data.data_loader import load_user_data_auto
                    success = load_user_data_auto(user_id)
                    if success:
                        st.success("Données chargées!")
                        st.cache_data.clear()
                    else:
                        st.error("Échec chargement")
        
        st.markdown("---")
        
        # Options d'affichage
        st.subheader("📊 Sections à Afficher")
        show_kpi = st.checkbox("KPI Globaux", value=True)
        show_capital = st.checkbox("Capital en Cours", value=True)
        show_tri = st.checkbox("TRI Expert", value=True)
        show_reinvest = st.checkbox("Réinvestissement", value=True)
        show_duration = st.checkbox("Duration", value=True)
        show_concentration = st.checkbox("Concentration", value=True)
        show_stress = st.checkbox("Stress Test", value=True)
        show_reco = st.checkbox("Recommandations", value=True)
        
        # Paramètres avancés
        st.subheader("⚙️ Paramètres")
        benchmark_oat = st.slider("Benchmark OAT 10Y (%)", 2.0, 5.0, 3.5, 0.1)
        benchmark_immo = st.slider("Benchmark Immobilier (%)", 4.0, 8.0, 5.5, 0.1)
        
        return user_id, {
            'show_kpi': show_kpi,
            'show_capital': show_capital,
            'show_tri': show_tri,
            'show_reinvest': show_reinvest,
            'show_duration': show_duration,
            'show_concentration': show_concentration,
            'show_stress': show_stress,
            'show_reco': show_reco,
            'benchmark_oat': benchmark_oat,
            'benchmark_immo': benchmark_immo
        }

def main_expert_dashboard():
    """Application principale dashboard expert"""
    
    # Header
    afficher_header_expert()
    
    # Sidebar
    user_id, options = sidebar_expert()
    
    # Chargement des données
    try:
        with st.spinner("Chargement des analyses expertes..."):
            investissements_df, flux_tresorerie_df, rapport_expert = charger_donnees_expert(user_id)
        
        if investissements_df.empty:
            st.error("❌ Aucune donnée trouvée pour cet utilisateur")
            st.info("💡 Utilisez le bouton 'Charger Données' dans la barre latérale")
            return
        
        # Affichage conditionnel des sections
        if options['show_kpi']:
            afficher_kpi_globaux(rapport_expert)
            st.markdown("---")
        
        if options['show_capital']:
            afficher_capital_en_cours(rapport_expert)
            st.markdown("---")
        
        if options['show_tri']:
            afficher_tri_expert(rapport_expert)
            st.markdown("---")
        
        if options['show_reinvest']:
            afficher_taux_reinvestissement(rapport_expert)
            st.markdown("---")
        
        if options['show_duration']:
            afficher_duration_immobilisation(rapport_expert)
            st.markdown("---")
        
        if options['show_concentration']:
            afficher_concentration_risk(rapport_expert)
            st.markdown("---")
        
        if options['show_stress']:
            afficher_stress_test(rapport_expert)
            st.markdown("---")
        
        if options['show_reco']:
            afficher_recommandations_expert(rapport_expert)
        
        # Footer avec résumé
        st.markdown("---")
        st.markdown("""
        <div style="text-align: center; color: #6c757d; padding: 1rem;">
            💎 Dashboard Expert Patrimoine • Analyse complète avec métriques avancées
            <br>TRI calculé avec dates réelles • Duration • Concentration • Stress Testing
        </div>
        """, unsafe_allow_html=True)
    
    except Exception as e:
        st.error(f"❌ Erreur lors du chargement: {e}")
        st.info("Vérifiez que vos données sont correctement chargées")
        import traceback
        with st.expander("🔍 Détails de l'erreur"):
            st.text(traceback.format_exc())

if __name__ == "__main__":
    main_expert_dashboard()