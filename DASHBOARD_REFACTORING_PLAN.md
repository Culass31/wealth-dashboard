# Plan de Refonte du Dashboard "Expert Patrimoine"

**Objectif Général :** Transformer le dashboard actuel en un outil d'analyse patrimoniale de pointe, visuellement moderne et ergonomique, offrant des insights approfondis sur la performance, les projections et les risques, en tirant parti de l'expertise de votre backend.

---

#### **1. Structure et Design du Dashboard (Modernisation & Ergonomie)**

Pour une expérience utilisateur optimale et pour accueillir la richesse des nouvelles métriques, je propose une réorganisation en **sections claires et potentiellement en onglets/pages dédiées** si la complexité l'exige.

*   **Layout Général :**
    *   **Page d'Accueil / Synthèse Globale :** Restera la vue principale, mais sera enrichie.
    *   **Navigation Latérale (Sidebar) :** Mieux structurée pour les actions (chargement, actualisation) et la navigation entre les sections/pages principales (ex: "Performance", "Projections", "Risques", "Détail par Plateforme").
    *   **Design Épuré :** Continuer sur la lancée du CSS personnalisé, en affinant les couleurs, les typographies et les espacements pour une lisibilité maximale. Utilisation de cartes (cards) pour regrouper les informations.

*   **Composants UI/UX :**
    *   **KPIs Améliorés :** Intégrer des "sparklines" (mini-graphiques de tendance) ou des indicateurs de variation sur les cartes KPI pour une vision rapide de l'évolution.
    *   **Filtres Avancés :** Ajouter des filtres globaux (période, type d'investissement, plateforme) qui affectent l'ensemble du dashboard, pour une analyse dynamique.
    *   **Tableaux Interactifs :** Utiliser des bibliothèques Streamlit plus avancées pour les tableaux (ex: `st.dataframe` avec options de tri, filtrage, recherche, et mise en forme conditionnelle) pour les détails de projets.
    *   **Visualisations Sophistiquées :** Exploiter pleinement Plotly pour des graphiques plus complexes et interactifs (ex: treemaps pour la concentration, graphiques en cascade pour l'attribution de performance).

---

#### **2. Nouveaux Indicateurs Pertinents (Priorisés)**

Je m'appuierai sur les capacités existantes de `PatrimoineCalculator` et proposerai des extensions si nécessaire.

**A. Performance du Patrimoine (Priorité Haute)**

*   **Attribution de Performance Détaillée :**
    *   **Par Plateforme :** Afficher la contribution de chaque plateforme au TRI global (déjà partiellement calculé, mais à mieux visualiser).
    *   **Par Classe d'Actifs :** Décomposer la performance par classe (Crowdfunding, Bourse, Liquidités, etc.).
    *   **Visualisation :** Graphique en cascade (waterfall chart) ou à barres empilées pour montrer la contribution de chaque segment.
*   **Performance vs. Benchmarks Multiples :**
    *   **Intégration des Benchmarks du `README.md` :** Afficher la performance du portefeuille par rapport à l'OAT 10Y et un indice immobilier (si données disponibles via `yfinance` ou autre source).
    *   **Graphique Comparatif :** Permettre de sélectionner plusieurs benchmarks à comparer sur le graphique d'évolution.
*   **Performance Glissante (Rolling Returns) :**
    *   **Calcul :** Ajouter des calculs de TRI sur des périodes glissantes (ex: 1 an, 3 ans, 5 ans) pour lisser les effets de point de départ/fin.
    *   **Visualisation :** Graphiques linéaires montrant l'évolution de ces TRI glissants.
*   **Contribution aux Flux :**
    *   **Répartition des Revenus :** Graphique montrant la part des intérêts, dividendes, plus-values réalisées dans les revenus totaux.
    *   **Répartition des Dépenses :** Graphique montrant la part des frais, taxes, retraits.

**B. Projections (Priorité Haute)**

*   **Projections de Liquidité Détaillées :**
    *   **Timeline des Remboursements :** Visualiser les remboursements attendus (capital + intérêts) sur les 12-24 prochains mois, agrégés par mois et par plateforme.
    *   **Graphique :** Barres empilées ou graphique linéaire montrant les flux entrants projetés.
*   **Suivi des Objectifs Financiers :**
    *   **Intégration de `financial_goals` :** Afficher la progression vers les objectifs définis (montant actuel vs. cible, pourcentage atteint, temps restant).
    *   **Visualisation :** Barres de progression, graphiques en jauge.
    *   **Simulation Simple :** Permettre à l'utilisateur de modifier des paramètres (investissement mensuel, rendement espéré) pour voir l'impact sur l'atteinte des objectifs.
*   **Scénarios de Croissance du Patrimoine :**
    *   **Extension de `FinancialFreedomSimulator` :** Présenter des scénarios "optimiste", "réaliste", "pessimiste" pour l'évolution du patrimoine, basés sur des rendements différents.
    *   **Visualisation :** Graphiques en entonnoir ou courbes multiples.

**C. Analyse des Risques (Priorité Importante)**

*   **Volatilité et Drawdown :**
    *   **Calcul :** Introduire des métriques de volatilité (écart-type des rendements) et de drawdown (perte maximale depuis un pic) pour le portefeuille global et par classe d'actifs.
    *   **Visualisation :** Graphiques de l'historique des drawdowns.
*   **Concentration Avancée :**
    *   **Visualisation :** Utiliser un "treemap" pour représenter la concentration par émetteur (`company_name`) ou par projet, la taille des blocs étant proportionnelle au montant investi.
    *   **Indice de Herfindahl :** Afficher l'HHI avec une interprétation claire (faible, modérée, forte concentration).
*   **Analyse des Retards et Défauts :**
    *   **KPIs :** Nombre et pourcentage de projets en retard/défaut, capital total affecté.
    *   **Tableau :** Liste des projets en difficulté avec leur statut et le capital restant dû.

---

#### **3. Stratégie de Mise en Œuvre**

*   **Développement Itératif :** Commencer par les indicateurs de performance, puis les projections, et enfin l'analyse des risques.
*   **Réutilisation du Backend :** Maximiser la réutilisation des méthodes existantes dans `PatrimoineCalculator`. Pour les nouvelles métriques, ajouter des méthodes dédiées dans cette classe.
*   **Refactoring du Frontend :**
    *   Créer des fonctions Streamlit dédiées pour chaque nouvelle section/graphique.
    *   Utiliser `st.container`, `st.expander`, `st.tabs` pour organiser le contenu.
    *   Mettre à jour le CSS pour les nouveaux composants et pour maintenir une cohérence visuelle.
*   **Tests :** S'assurer que chaque nouvelle métrique et visualisation est correctement testée.

---

**Prochaine Étape :**

Commencer par la section **Performance du Patrimoine**.
