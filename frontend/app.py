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

# Configuration de la page
st.set_page_config(
    page_title="Tableau de Bord Patrimoine",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# CSS personnalisé
st.markdown("""
<style>
    .metric-container {
        background-color: #f0f2f6;
        padding: 1rem;
        border-radius: 0.5rem;
        margin: 0.5rem 0;
    }
    .big-number {
        font-size: 2rem;
        font-weight: bold;
        color: #1f77b4;
    }
    .positive {
        color: #2ca02c;
    }
    .negative {
        color: #d62728;
    }
</style>
""", unsafe_allow_html=True)

@st.cache_data
def charger_donnees_utilisateur(user_id: str):
    """Charger les données utilisateur avec mise en cache"""
    db = DatabaseManager()
    investissements_df = db.get_user_investments(user_id)
    flux_tresorerie_df = db.get_user_cash_flows(user_id)
    return investissements_df, flux_tresorerie_df

def calculer_metriques(investissements_df: pd.DataFrame, flux_tresorerie_df: pd.DataFrame):
    """Calculer les métriques clés avec logique corrigée"""
    metriques = {}
    
    if not investissements_df.empty:
        # Total investi (montant réel investi)
        metriques['total_investi'] = investissements_df['invested_amount'].sum()
        
        # Répartition par plateforme
        repartition_plateforme = investissements_df.groupby('platform')['invested_amount'].sum()
        metriques['repartition_plateforme'] = repartition_plateforme
        
        # Répartition par statut
        repartition_statut = investissements_df['status'].value_counts()
        metriques['repartition_statut'] = repartition_statut
        
        # Répartition par classe d'actifs
        repartition_actifs = investissements_df.groupby('asset_class')['invested_amount'].sum()
        metriques['repartition_actifs'] = repartition_actifs
    
    if not flux_tresorerie_df.empty:
        # Convertir les dates
        flux_tresorerie_df['transaction_date'] = pd.to_datetime(flux_tresorerie_df['transaction_date'], errors='coerce')
        
        # Séparer les flux entrants et sortants
        flux_entrants = flux_tresorerie_df[flux_tresorerie_df['flow_direction'] == 'in']
        flux_sortants = flux_tresorerie_df[flux_tresorerie_df['flow_direction'] == 'out']
        
        # Calculer les totaux
        total_entrees = flux_entrants['gross_amount'].sum()
        total_sorties = flux_sortants['gross_amount'].sum()
        
        # Séparer les différents types de flux
        interets_bruts = flux_entrants[flux_entrants['flow_type'] == 'interest']['gross_amount'].sum()
        remboursements_capital = flux_entrants[flux_entrants['flow_type'] == 'repayment']['capital_amount'].sum()
        frais_fiscaux = flux_sortants[flux_sortants['flow_type'] == 'fee']['gross_amount'].sum()
        
        # Calculs corrigés
        metriques['total_entrees'] = total_entrees
        metriques['total_sorties'] = total_sorties
        metriques['interets_bruts'] = interets_bruts
        metriques['frais_fiscaux'] = frais_fiscaux
        metriques['remboursements_capital'] = remboursements_capital
        metriques['performance_nette'] = total_entrees - total_sorties
        
        # Taux de réinvestissement (nouveau calcul)
        if metriques.get('total_investi', 0) > 0:
            # Capital récupéré qui a été réinvesti
            capital_reinvesti = max(0, metriques['total_investi'] - 
                                  (total_entrees - interets_bruts))  # Approximation
            metriques['taux_reinvestissement'] = (capital_reinvesti / metriques['total_investi']) * 100
        else:
            metriques['taux_reinvestissement'] = 0
        
        # Flux mensuels
        flux_tresorerie_df_clean = flux_tresorerie_df.dropna(subset=['transaction_date'])
        if not flux_tresorerie_df_clean.empty:
            flux_tresorerie_df_clean['annee_mois'] = flux_tresorerie_df_clean['transaction_date'].dt.to_period('M')
            flux_mensuels = flux_tresorerie_df_clean.groupby('annee_mois')['net_amount'].sum()
            metriques['flux_mensuels'] = flux_mensuels
    
    return metriques

def main():
    st.title("💰 Tableau de Bord Patrimoine")
    st.markdown("---")
    
    # Barre latérale
    with st.sidebar:
        st.header("Navigation")
        
        # Pour le développement - simuler un utilisateur
        user_id = st.text_input("ID Utilisateur (développement)", value="demo-user-123")
        
        # Section de gestion des données
        st.subheader("Gestion des Données")
        
        if st.button("🔄 Actualiser les Données"):
            st.cache_data.clear()
            st.success("Données actualisées !")
        
        fichier_upload = st.file_uploader(
            "Télécharger un Fichier de Plateforme", 
            type=['xlsx'],
            help="Télécharger un fichier Excel de plateforme de crowdfunding"
        )
        
        plateforme = st.selectbox(
            "Sélectionner la Plateforme",
            ["LBP", "PretUp", "BienPreter", "Homunity"]
        )
        
        if fichier_upload and st.button("Charger les Données"):
            try:
                # Sauvegarder le fichier temporairement
                with open(f"temp_{fichier_upload.name}", "wb") as f:
                    f.write(fichier_upload.getbuffer())
                
                # Charger les données
                loader = DataLoader()
                succes = loader.load_platform_data(
                    f"temp_{fichier_upload.name}", 
                    plateforme.lower(), 
                    user_id
                )
                
                if succes:
                    st.success(f"✅ Données chargées depuis {plateforme} !")
                    st.cache_data.clear()  # Vider le cache pour recharger les données
                    os.remove(f"temp_{fichier_upload.name}")  # Nettoyage
                else:
                    st.error("❌ Échec du chargement des données")
                    
            except Exception as e:
                st.error(f"Erreur : {e}")
    
    # Contenu principal
    try:
        # Charger les données
        investissements_df, flux_tresorerie_df = charger_donnees_utilisateur(user_id)
        
        if investissements_df.empty and flux_tresorerie_df.empty:
            st.warning("Aucune donnée trouvée. Veuillez télécharger des fichiers via la barre latérale.")
            st.info("""
            **Pour commencer :**
            1. Sélectionnez une plateforme (LBP, PretUp, BienPreter, Homunity)
            2. Téléchargez votre fichier Excel de cette plateforme
            3. Cliquez sur 'Charger les Données'
            """)
            return
        
        # Calculer les métriques
        metriques = calculer_metriques(investissements_df, flux_tresorerie_df)
        
        # Ligne des métriques clés
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            total_investi = metriques.get('total_investi', 0)
            st.metric(
                "💸 Total Investi",
                f"{total_investi:,.0f} €",
                help="Montant total investi sur toutes les plateformes"
            )
        
        with col2:
            total_entrees = metriques.get('total_entrees', 0)
            st.metric(
                "💰 Total des Retours",
                f"{total_entrees:,.0f} €",
                help="Total des retours reçus (capital + intérêts)"
            )
        
        with col3:
            performance_nette = metriques.get('performance_nette', 0)
            couleur_delta = "normal" if performance_nette >= 0 else "inverse"
            st.metric(
                "📊 Performance Nette",
                f"{performance_nette:,.0f} €",
                f"{(performance_nette/total_investi)*100:.1f}%" if total_investi > 0 else "0%",
                delta_color=couleur_delta
            )
        
        with col4:
            taux_reinvestissement = metriques.get('taux_reinvestissement', 0)
            st.metric(
                "🔄 Taux Réinvestissement",
                f"{taux_reinvestissement:.1f}%",
                help="Pourcentage du capital récupéré qui a été réinvesti"
            )
        
        # Nouvelle ligne de métriques détaillées
        col1, col2, col3, col4 = st.columns(4)
        
        with col1:
            projets_actifs = len(investissements_df[investissements_df['status'] == 'active']) if not investissements_df.empty else 0
            st.metric(
                "🏗️ Projets Actifs",
                projets_actifs
            )
        
        with col2:
            interets_bruts = metriques.get('interets_bruts', 0)
            st.metric(
                "🎯 Intérêts Bruts",
                f"{interets_bruts:,.0f} €"
            )
        
        with col3:
            frais_fiscaux = metriques.get('frais_fiscaux', 0)
            st.metric(
                "🏛️ Frais Fiscaux",
                f"{frais_fiscaux:,.0f} €"
            )
        
        with col4:
            remboursements_capital = metriques.get('remboursements_capital', 0)
            st.metric(
                "💵 Capital Remboursé",
                f"{remboursements_capital:,.0f} €"
            )
        
        st.markdown("---")
        
        # Ligne des graphiques 1
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("📊 Investissements par Plateforme")
            if 'repartition_plateforme' in metriques and not metriques['repartition_plateforme'].empty:
                fig = px.pie(
                    values=metriques['repartition_plateforme'].values,
                    names=metriques['repartition_plateforme'].index,
                    title="Répartition par Plateforme"
                )
                fig.update_traces(textposition='inside', textinfo='percent+label')
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée d'investissement disponible")
        
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
            else:
                st.info("Aucune donnée de statut disponible")
        
        # Ligne des graphiques 2
        col1, col2 = st.columns(2)
        
        with col1:
            st.subheader("💰 Flux de Trésorerie Mensuels")
            if 'flux_mensuels' in metriques and not metriques['flux_mensuels'].empty:
                flux_mensuels = metriques['flux_mensuels']
                
                fig = go.Figure()
                fig.add_trace(go.Bar(
                    x=[str(periode) for periode in flux_mensuels.index],
                    y=flux_mensuels.values,
                    marker_color=['green' if x > 0 else 'red' for x in flux_mensuels.values],
                    name="Flux Mensuel"
                ))
                
                fig.update_layout(
                    title="Évolution des Flux de Trésorerie",
                    xaxis_title="Mois",
                    yaxis_title="Montant (€)",
                    showlegend=False
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée de flux de trésorerie disponible")
        
        with col2:
            st.subheader("🏠 Répartition par Classe d'Actifs")
            if 'repartition_actifs' in metriques and not metriques['repartition_actifs'].empty:
                # Utiliser px.pie au lieu de px.donut qui n'existe pas
                fig = px.pie(
                    values=metriques['repartition_actifs'].values,
                    names=metriques['repartition_actifs'].index,
                    title="Allocation par Classe d'Actifs",
                    hole=0.4  # Ceci crée l'effet "donut"
                )
                st.plotly_chart(fig, use_container_width=True)
            else:
                st.info("Aucune donnée de classe d'actifs disponible")
        
        # Tableaux de données
        st.markdown("---")
        
        tab1, tab2 = st.tabs(["📈 Investissements", "💸 Flux de Trésorerie"])
        
        with tab1:
            st.subheader("Portefeuille d'Investissements")
            if not investissements_df.empty:
                # Formater le dataframe pour l'affichage
                colonnes_affichage = ['platform', 'project_name', 'invested_amount', 
                                    'annual_rate', 'investment_date', 'status']
                
                # Vérifier que les colonnes existent
                colonnes_existantes = [col for col in colonnes_affichage if col in investissements_df.columns]
                
                if colonnes_existantes:
                    affichage_df = investissements_df[colonnes_existantes].copy()
                    
                    # Formater les colonnes si elles existent
                    if 'invested_amount' in affichage_df.columns:
                        affichage_df['invested_amount'] = affichage_df['invested_amount'].apply(lambda x: f"{x:,.0f} €" if pd.notna(x) else "N/A")
                    if 'annual_rate' in affichage_df.columns:
                        affichage_df['annual_rate'] = affichage_df['annual_rate'].apply(lambda x: f"{x:.1f}%" if pd.notna(x) else "N/A")
                    
                    # Renommer les colonnes en français
                    noms_colonnes = {
                        'platform': 'Plateforme',
                        'project_name': 'Nom du Projet',
                        'invested_amount': 'Montant Investi',
                        'annual_rate': 'Taux Annuel',
                        'investment_date': 'Date d\'Investissement',
                        'status': 'Statut'
                    }
                    
                    affichage_df = affichage_df.rename(columns=noms_colonnes)
                    
                    st.dataframe(
                        affichage_df,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.warning("Colonnes d'affichage non trouvées dans les données")
            else:
                st.info("Aucune donnée d'investissement à afficher")
        
        with tab2:
            st.subheader("Flux de Trésorerie Récents")
            if not flux_tresorerie_df.empty:
                # Montrer les transactions récentes
                flux_recents = flux_tresorerie_df.sort_values('created_at', ascending=False).head(20)
                
                colonnes_flux = ['transaction_date', 'flow_type', 'gross_amount', 
                               'flow_direction', 'description']
                
                colonnes_existantes = [col for col in colonnes_flux if col in flux_recents.columns]
                
                if colonnes_existantes:
                    affichage_flux = flux_recents[colonnes_existantes].copy()
                    
                    if 'gross_amount' in affichage_flux.columns:
                        affichage_flux['gross_amount'] = affichage_flux['gross_amount'].apply(lambda x: f"{x:,.2f} €" if pd.notna(x) else "N/A")
                    
                    # Renommer les colonnes en français
                    noms_colonnes_flux = {
                        'transaction_date': 'Date Transaction',
                        'flow_type': 'Type de Flux',
                        'gross_amount': 'Montant Brut',
                        'flow_direction': 'Direction',
                        'description': 'Description'
                    }
                    
                    affichage_flux = affichage_flux.rename(columns=noms_colonnes_flux)
                    
                    st.dataframe(
                        affichage_flux,
                        use_container_width=True,
                        hide_index=True
                    )
                else:
                    st.warning("Colonnes de flux non trouvées dans les données")
            else:
                st.info("Aucune donnée de flux de trésorerie à afficher")
        
    except Exception as e:
        st.error(f"Erreur lors du chargement du tableau de bord : {e}")
        st.info("Veuillez vérifier votre connexion à la base de données et vos données.")
        # Afficher plus de détails de l'erreur pour le débogage
        import traceback
        st.text(traceback.format_exc())

if __name__ == "__main__":
    main()