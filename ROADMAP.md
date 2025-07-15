# Feuille de Route : Amélioration du Dashboard d'Analyse Patrimoniale

Cette feuille de route détaille les fonctionnalités futures envisagées pour enrichir le dashboard d'analyse patrimoniale, en se basant sur les écarts identifiés entre la documentation initiale et l'implémentation actuelle. Ces améliorations visent à fournir une analyse plus approfondie et des outils plus sophistiqués pour la gestion de patrimoine.

---

### 1. Amélioration de l'Analyse de Risque

**Objectif :** Fournir des outils plus sophistiqués pour évaluer et visualiser les risques du portefeuille.

*   **1.1. Calcul de l'Indice de Herfindahl pour la Concentration par Émetteur** - **TERMINÉ**
    *   **Valeur Ajoutée :** L'Indice de Herfindahl est une mesure standard de la concentration du marché. Son calcul permettrait une évaluation plus formelle et quantitative du risque de concentration par émetteur, au-delà d'un simple pourcentage.
    *   **Considérations Techniques :**
        *   **Backend (`PatrimoineCalculator`) :** Implémenté une méthode pour calculer l'indice à partir des données de `investments_df` (en utilisant `company_name` et `invested_amount`).
        *   **Base de Données :** La vue `v_concentration_analysis` fournit déjà les données nécessaires (`share_percentage`), il s'agit d'une agrégation supplémentaire côté application.
        *   **Frontend (`dashboard.py`) :** Afficher l'indice et son interprétation (par exemple, seuils de faible/moyenne/forte concentration).

*   **1.2. Analyse de la Diversification (Géographique et Sectorielle)** - **EN PAUSE (Données source non disponibles)**
    *   **Valeur Ajoutée :** La diversification est clé pour la gestion des risques. Permettre aux utilisateurs de visualiser leur exposition par région ou secteur (si ces données sont disponibles ou peuvent être inférées) offrirait une perspective cruciale.
    *   **Considérations Techniques :**
        *   **Data Ingestion (`UnifiedPortfolioParser`) :** Nécessiterait l'ajout de champs `geographical_location` et `sector` aux modèles `Investment` et leur extraction lors du parsing (potentiellement complexe si non présents dans les fichiers sources).
        *   **Backend (`PatrimoineCalculator`) :** Développer des méthodes pour agréger et analyser les investissements par ces nouvelles dimensions.
        *   **Base de Données :** Ajouter les colonnes `geographical_location` et `sector` à la table `investments`.
        *   **Frontend (`dashboard.py`) :** Créer des graphiques de répartition (camemberts, barres) pour la diversification géographique et sectorielle.

*   **1.3. Calcul du Ratio de Sharpe (adapté au Crowdfunding)** - **EN PAUSE (Méthodologie de volatilité incertaine)**
    *   **Valeur Ajoutée :** Le Ratio de Sharpe mesure le rendement ajusté au risque. L'adapter au crowdfunding (en utilisant un taux sans risque approprié et une volatilité calculée ou estimée pour ce type d'actif) fournirait une métrique de performance plus pertinente.
    *   **Considérations Techniques :**
        *   **Backend (`PatrimoineCalculator`) :** Implémenter le calcul du Ratio de Sharpe. Cela nécessiterait de définir un "taux sans risque" et de calculer la volatilité des rendements du crowdfunding (ce qui pourrait être complexe sans une série historique de rendements agrégés).
        *   **Data :** Potentiellement, collecter ou estimer des données de volatilité pour les plateformes de crowdfunding.

*   **1.4. Stress testing multi-scénarios** - **TERMINÉ (via simulation Monte Carlo dans `financial_freedom.py`)**
    *   **Valeur Ajoutée :** Permet d'évaluer la résilience du portefeuille face à différents scénarios de marché.
    *   **Considérations Techniques :**
        *   **Backend (`financial_freedom.py`) :** Implémenté des simulations Monte Carlo pour projeter l'évolution du patrimoine sous différentes conditions.

*   **1.5. Analyse de retards et projets en difficulté** - **TERMINÉ**
    *   **Valeur Ajoutée :** Identification rapide des investissements à risque pour une gestion proactive.
    *   **Considérations Techniques :**
        *   **Base de Données :** La colonne `is_delayed` dans la table `investments` permet de marquer les projets en retard.
        *   **Frontend (`dashboard.py`) :** Afficher les projets en retard et leur impact potentiel sur le portefeuille.

### 2. Approfondissement de l'Analyse de Liquidité et de Rendement

**Objectif :** Offrir une vision plus granulaire de la liquidité du portefeuille et des flux de capital.

*   **2.1. Taux de Remboursement et Rotation du Capital** - **TERMINÉ (par plateforme)**
    *   **Valeur Ajoutée :** Ces métriques indiquent la vitesse à laquelle le capital investi est récupéré et réutilisé, essentielle pour la gestion de trésorerie et la compréhension du cycle d'investissement.
    *   **Considérations Techniques :**
        *   **Backend (`PatrimoineCalculator`) :** Calculé ces ratios à partir de `investments_df` (`invested_amount`, `capital_repaid`) et `cash_flows_df`.
        *   **Frontend (`dashboard.py`) :** Afficher ces KPIs dans la synthèse globale ou par plateforme.

*   **2.2. Projections de Liquidité à Court/Moyen Terme** - **TERMINÉ (par plateforme)**
    *   **Valeur Ajoutée :** Permettre aux utilisateurs de prévoir les rentrées de capital (remboursements, intérêts) sur les prochains mois/années est fondamental pour la planification financière et les décisions de réinvestissement.
    *   **Considérations Techniques :**
        *   **Backend (`PatrimoineCalculator`) :** Développé une logique de projection basée sur `expected_end_date` et les échéanciers (si disponibles) des investissements.
        *   **Frontend (`dashboard.py`) :** Visualiser ces projections sous forme de graphique (par exemple, histogramme mensuel des flux attendus).

*   **2.3. Duration Moyenne Pondérée et Répartition par Échéance** - **TERMINÉ (par plateforme)**
    *   **Valeur Ajoutée :** La duration est une mesure de la sensibilité d'un investissement aux variations de taux d'intérêt et de la durée moyenne de récupération du capital. La répartition par échéance est cruciale pour l'analyse de liquidité.
    *   **Considérations Techniques :**
        *   **Backend (`PatrimoineCalculator`) :** Calculé la duration moyenne pondérée pour les investissements à revenu fixe (crowdfunding, obligations) et agréger la répartition par tranches d'échéance (<6m, 6-12m, >12m).
        *   **Base de Données :** S'assurer que `duration_months` et `expected_end_date` sont fiables.
        *   **Frontend (`dashboard.py`) :** Afficher ces métriques et des graphiques de répartition.

### 3. Optimisation Fiscale Avancée

**Objectif :** Aider les utilisateurs à optimiser leur fiscalité et à comprendre l'impact des décisions d'investissement.

*   **3.1. Optimisation des Plus-Values PEA**
    *   **Valeur Ajoutée :** Proposer des stratégies pour minimiser l'impôt sur les plus-values dans le cadre du PEA (par exemple, en suggérant des arbitrages ou des ventes après la période d'exonération).
    *   **Considérations Techniques :**
        *   **Backend (`PatrimoineCalculator`) :** Nécessiterait une logique complexe de suivi des prix de revient, des dates d'acquisition/cession, et des règles fiscales spécifiques au PEA.
        *   **Data :** Assurer la disponibilité des prix d'achat et des dates d'acquisition pour les positions PEA.

*   **3.2. Optimisation Fiscale des Flux Entrants** - **TERMINÉ**
    *   **Valeur Ajoutée :** Analyser comment les dépôts et les réinvestissements peuvent être structurés pour optimiser la fiscalité globale (par exemple, utilisation des enveloppes fiscales).
    *   **Considérations Techniques :**
        *   **Backend (`PatrimoineCalculator`) :** Développé des règles et des simulations basées sur les types de flux et les plateformes.

### 4. Indicateurs de Performance et de Maturité

**Objectif :** Fournir des métriques supplémentaires pour évaluer la performance et la maturité du portefeuille.

*   **4.1. Taux de Réinvestissement** - **TERMINÉ (par plateforme)**
    *   **Valeur Ajoutée :** Mesure la part des flux de capital (remboursements, intérêts) qui est réinvestie dans de nouveaux projets, illustrant l'effet boule de neige et la croissance du capital par réinvestissement.
    *   **Considérations Techniques :**
        *   **Backend (`PatrimoineCalculator`) :** Calculé ce ratio en comparant les flux de remboursement/intérêts aux nouveaux investissements.

*   **4.2. Indicateur de Maturité du Portefeuille** - **TERMINÉ (par plateforme)**
    *   **Valeur Ajoutée :** Un indicateur composite qui évalue la proportion d'investissements arrivant à terme, la liquidité disponible et la capacité de réinvestissement, donnant une idée de la "vieillesse" ou de la "jeunesse" du portefeuille.
    *   **Considérations Techniques :**
        *   **Backend (`PatrimoineCalculator`) :** Développé une métrique composite basée sur la duration, les projections de liquidité et le taux de réinvestissement.

### 5. Fonctionnalités Temporairement Désactivées

### 6. Refonte Complète du Dashboard

**Objectif :** Refondre entièrement le dashboard pour intégrer de nouveaux indicateurs de performance, de projection et d'analyse des risques, avec un design moderne et ergonomique.

*   **Plan Détaillé :** Se référer à [DASHBOARD_REFACTORING_PLAN.md](DASHBOARD_REFACTORING_PLAN.md) pour le plan d'action complet.

---

### 5. Fonctionnalités Temporairement Désactivées

**Objectif :** Suivre les fonctionnalités qui ont été temporairement désactivées et qui nécessitent une réimplémentation ou une correction.

*   **5.1. Évolution du Patrimoine vs. Benchmark (ETF World)** - **EN PAUSE**
    *   **Valeur Ajoutée :** Permet de comparer la performance du portefeuille de l'utilisateur à un indice de référence (ETF World) pour évaluer l'outperformance ou la sous-performance.
    *   **Considérations Techniques :**
        *   **Problème Identifié :** Erreur `Only valid with DatetimeIndex, TimedeltaIndex or PeriodIndex, but got an instance of 'Index'` lors de l'affichage dans le frontend. La section graphique s'affiche désormais après simplification temporaire de la fonction `get_charts_data()`.
        *   **Action :** La logique de calcul originale a été restaurée dans `backend/analytics/patrimoine_calculator.py`. L'analyse approfondie de cette section est mise en pause pour le moment et sera reprise ultérieurement.
