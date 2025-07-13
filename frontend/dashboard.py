# ===== frontend/dashboard.py - NOUVEAU DASHBOARD DE PILOTAGE PATRIMOINE (v1.9.3 - DEBUG TRI & BENCHMARK APPROFONDI) =====
import streamlit as st
import pandas as pd
import plotly.graph_objects as go
import plotly.express as px
import sys
import os
import logging
from pathlib import Path
from typing import Dict, Any
from dotenv import load_dotenv

# --- Configuration du chemin et des imports ---
project_root = Path(__file__).resolve().parent.parent
if str(project_root) not in sys.path:
    sys.path.append(str(project_root))

from backend.analytics.patrimoine_calculator import PatrimoineCalculator
from backend.data.data_loader import DataLoader
from backend.models.database import ExpertDatabaseManager

# --- Configuration de la page Streamlit ---
st.set_page_config(page_title="Wealth Dashboard", page_icon="✨", layout="wide")

# --- CSS Personnalisé pour un design dynamique ---
st.markdown("""<style>
:root {
    --primary-color: #1E88E5; --secondary-color: #00ACC1; --background-color: #F5F7FA;
    --card-background-color: #FFFFFF; --text-color: #263238; --subtle-text-color: #546E7A;
    --border-color: #E0E0E0; --green: #34A853; --red: #EA4335;
}
.stApp { background-color: var(--background-color); color: var(--text-color); }
.kpi-card { 
    background-color: var(--card-background-color); 
    border-radius: 12px; 
    padding: 20px; 
    border: 1px solid var(--border-color); 
    box-shadow: 0 2px 8px rgba(0,0,0,0.04);
    transition: transform 0.2s ease-in-out, box-shadow 0.2s ease-in-out;
}
.kpi-card:hover { transform: translateY(-4px); box-shadow: 0 6px 12px rgba(0,0,0,0.08); }
.kpi-title { font-size: 1rem; color: var(--subtle-text-color); margin-bottom: 8px; }
.kpi-value { font-size: 2.2rem; font-weight: 600; }
.kpi-delta { font-size: 1.1rem; font-weight: 500; }
.section-header { font-size: 1.8rem; font-weight: 700; color: var(--text-color); margin-top: 2rem; margin-bottom: 1rem; padding-bottom: 0.5rem; border-bottom: 3px solid var(--primary-color);}
</style>""", unsafe_allow_html=True)

# --- Fonctions de chargement et de gestion ---
@st.cache_resource(ttl=900)
def load_calculator(user_id: str) -> PatrimoineCalculator:
    with st.spinner("🔍 Connexion et analyse de votre patrimoine..."):
        return PatrimoineCalculator(user_id)

def handle_file_upload(files, platform_code, user_id):
    loader = DataLoader()
    with st.spinner(f"Traitement pour {platform_code}..."):
        if platform_code == 'pea' and isinstance(files, list):
            temp_dir = Path("./temp_pea_uploads")
            temp_dir.mkdir(exist_ok=True)
            for p in temp_dir.glob("*"): p.unlink()
            for f in files:
                with open(temp_dir / f.name, "wb") as out_file: out_file.write(f.getbuffer())
            success = loader.load_all_pea_files(user_id, str(temp_dir))
        else:
            file = files[0] if isinstance(files, list) else files
            temp_path = f"./temp_{file.name}"
            with open(temp_path, "wb") as f: f.write(file.getbuffer())
            success = loader.load_platform_data(temp_path, platform_code, user_id)
            os.remove(temp_path)

    if success:
        st.success("Chargement réussi ! Les données sont en cours d'actualisation.")
        st.cache_resource.clear()
        st.rerun()
    else:
        st.error("Le chargement a échoué. Vérifiez les logs ou le format du fichier.")

# --- Composants UI Personnalisés ---
def display_custom_kpi(title: str, value: float, unit: str = "€", delta: float = None, delta_label: str = ""):
    value_color = "var(--primary-color)"
    delta_color = "var(--subtle-text-color)"
    if title == "Plus-Value Nette":
        if value > 0:
            value_color = "var(--green)"
        elif value < 0:
            value_color = "var(--red)"

    if delta is not None:
        if delta > 0:
            delta_color = "var(--green)"
        elif delta < 0:
            delta_color = "var(--red)"

    delta_str = f"<span class='kpi-delta' style='color:{delta_color};'>{delta:,.2f}% {delta_label}</span>" if delta is not None else ""

    # Correction: Encapsuler le delta dans une div pour stabiliser le rendu HTML.
    st.markdown(f'''
    <div class="kpi-card">
        <div class="kpi-title">{title}</div>
        <div class="kpi-value" style="color:{value_color};">{value:,.0f} {unit}</div>
        <div>{delta_str}</div>
    </div>
    ''', unsafe_allow_html=True)

# --- Sections du Dashboard ---
def display_global_kpis(kpis: Dict[str, Any]):
    st.markdown("<div class='section-header'>Synthèse Globale</div>", unsafe_allow_html=True)
    c1, c2, c3, c4 = st.columns(4)
    with c1: display_custom_kpi("Patrimoine Total", kpis.get('patrimoine_total', 0))
    with c2: display_custom_kpi("Plus-Value Nette", kpis.get('plus_value_nette', 0))
    with c3: display_custom_kpi("Total des Apports", kpis.get('total_apports', 0))
    with c4: display_custom_kpi("TRI Global Annuel", kpis.get('tri_global_brut', 0), unit="%", delta=kpis.get('tri_global_net', 0), delta_label="(Net)")

def display_global_charts(charts_data: Dict[str, Any]):
    st.markdown("<div class='section-header'>Visualisations Globales</div>", unsafe_allow_html=True)
    c1, c2 = st.columns([1, 2])
    with c1:
        st.subheader("Répartition du Patrimoine")
        repartition = charts_data.get('repartition_data', {})
        if sum(repartition.values()) > 0:
            fig = go.Figure(data=[go.Pie(labels=list(repartition.keys()), values=list(repartition.values()), hole=.5, marker_colors=['#1E88E5', '#00ACC1', '#D1D9E1'])])
            fig.update_traces(textinfo='percent+label', textfont_size=14)
            fig.update_layout(showlegend=False, margin=dict(t=0, b=0, l=0, r=0))
            st.plotly_chart(fig, use_container_width=True)
    with c2:
        st.subheader("Évolution du Patrimoine vs. Benchmark")
        evolution_data = charts_data.get('evolution_data', {})
        patrimoine_total_evolution = evolution_data.get('patrimoine_total_evolution')
        benchmark = evolution_data.get('benchmark')

        if not patrimoine_total_evolution.empty:
            fig = go.Figure()
            fig.add_trace(go.Scatter(x=patrimoine_total_evolution.index, y=patrimoine_total_evolution.values, mode='lines', name='Mon Patrimoine', line=dict(color='#1E88E5')))
            if not benchmark.empty:
                fig.add_trace(go.Scatter(x=benchmark.index, y=benchmark.values, mode='lines', name='Benchmark (ETF World)', line=dict(color='#00ACC1', dash='dash')))
            
            fig.update_layout(
                title_text='Évolution du Patrimoine et Benchmark',
                xaxis_title='Date',
                yaxis_title='Valeur (Indexée)',
                hovermode="x unified",
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.warning("Pas de données d'évolution du patrimoine disponibles pour le graphique.")

def display_periodic_performance(calculator: PatrimoineCalculator):
    st.markdown("<div class='section-header'>Performance Périodique</div>", unsafe_allow_html=True)
    perf_data = calculator.get_periodic_performance()
    view = st.radio("Choisir la vue", ["Mensuelle", "Annuelle"], horizontal=True, label_visibility="collapsed")
    df = perf_data['annual'] if view == "Annuelle" else perf_data['monthly']
    if not df.empty:
        fig = px.bar(df, x='Period', y='net_gain', title=f"Performance Nette {view.lower()}", color='net_gain', color_continuous_scale=px.colors.diverging.RdYlGn, labels={'net_gain': 'Gain/Perte Net (€)'})
        st.plotly_chart(fig, use_container_width=True)

def display_platform_analysis(calculator: PatrimoineCalculator):
    st.markdown("<div class='section-header'>Analyse Détaillée par Plateforme</div>", unsafe_allow_html=True)
    platform_details = calculator.get_platform_details()
    if not platform_details: st.warning("Aucune donnée de plateforme à analyser."); return
    platforms = list(platform_details.keys())
    selected_platform = st.selectbox("Sélectionnez une plateforme", options=platforms)
    if selected_platform:
        details = platform_details[selected_platform]
        st.subheader(f"Fiche d'Identité : {selected_platform}")
        c1, c2, c3 = st.columns(3)
        cap_inv, cap_enc = details.get('capital_investi_encours', (0,0))
        c1.metric("Capital Investi / Encours", f"{cap_inv:,.0f}€", f"{cap_enc:,.0f}€ en cours")
        c2.metric("Plus-Value Réalisée (Nette)", f"{details.get('plus_value_realisee_nette', 0):,.0f}€")
        c3.metric("TRI Plateforme", f"{details.get('tri_brut', 0):.2f}%", f"{details.get('tri_net', 0):.2f}% (Net)")
        st.markdown("#### Tableau de Bord Détaillé")
        st.table(pd.DataFrame({"Métrique": ["Intérêts Bruts Reçus", "Impôts et Frais", "Nombre de projets/lignes"], "Valeur": [f"{details.get('interets_bruts_recus', 0):,.2f} €", f"{details.get('impots_et_frais', 0):,.2f} €", str(details.get('nombre_projets', 0))]})) # <-- CORRECTION ICI
        project_details = calculator.get_crowdfunding_project_details()
        if selected_platform in project_details:
            st.markdown("#### Détail des Projets")
            st.dataframe(project_details[selected_platform].style.format({'Montant Investi': "{:.2f}€", 'Capital Restant Dû': "{:.2f}€", 'Intérêts Reçus (Nets)': "{:.2f}€", 'TRI du Projet (%)': "{:.2f}%"}))

# --- Application Principale ---
def main():
    load_dotenv()  # Charger les variables d'environnement depuis .env
    st.title("✨ Wealth Dashboard")
    user_id = os.getenv("DEFAULT_USER_ID")
    if not user_id:
        st.error("DEFAULT_USER_ID n'est pas défini dans le fichier .env. Veuillez le configurer.")
        return
    with st.sidebar:
        st.header("⚙️ Actions")
        if st.button("🔄 Actualiser les Données"):
            st.cache_resource.clear()
            st.rerun()
        
        with st.expander("📤 Chargement de Données", expanded=False):
            platform_options = {"La Première Brique": "lpb", "PretUp": "pretup", "BienPrêter": "bienpreter", "Homunity": "homunity", "Assurance Vie (Linxea)": "assurance_vie"}
            uploaded_excel = st.file_uploader("Fichier Excel (Crowdfunding, AV)", type=['xlsx'])
            if uploaded_excel:
                platform_name = st.selectbox("Plateforme Excel", options=list(platform_options.keys()))
                if st.button(f"Charger {platform_name}"):
                    handle_file_upload(uploaded_excel, platform_options[platform_name], user_id)

            uploaded_pdfs = st.file_uploader("Fichiers PDF (PEA)", type=['pdf'], accept_multiple_files=True)
            if uploaded_pdfs:
                if st.button("Charger Fichiers PEA"):
                    handle_file_upload(uploaded_pdfs, 'pea', user_id)

        with st.expander("🗑️ Vider mes Données", expanded=False):
            if st.checkbox("Je confirme vouloir supprimer toutes mes données."):
                if st.button("Supprimer Définitivement", type="primary"):
                    db = ExpertDatabaseManager()
                    db.clear_user_data(user_id)
                    st.cache_resource.clear()
                    st.success("Toutes vos données ont été supprimées.")
                    st.rerun()

    try:
        calculator = load_calculator(user_id)
        display_global_kpis(calculator.get_global_kpis())
        display_global_charts(calculator.get_charts_data())
        display_periodic_performance(calculator)
        display_platform_analysis(calculator)
    except Exception as e:
        st.error(f"Une erreur est survenue: {e}")
        st.warning("Veuillez vérifier que des données ont été chargées ou actualiser.")

if __name__ == "__main__":
    main()
