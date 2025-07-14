# 💎 Expert Patrimoine - Dashboard Avancé

> **Analyse experte de portefeuille multi-plateformes avec métriques financières avancées**

Une solution complète d'analyse patrimoniale développée par un agent expert en gestion de patrimoine avec plus de 30 ans d'expérience, spécialisé dans les produits PEA, CTO, Assurance vie et Crowdfunding immobilier.

## 🎯 Fonctionnalités Expert

### 📊 **Métriques Financières Avancées**
- **TRI (Taux de Rendement Interne)** avec dates réelles d'investissement
- **Capital en cours** vs capital remboursé par plateforme
- **Taux de remboursement** et rotation du capital par plateforme
- **Projections de liquidité** à court/moyen terme par plateforme
- **Duration moyenne pondérée** et répartition par échéance par plateforme
- **Taux de réinvestissement** et effet boule de neige par plateforme
- **Performance mensuelle** et annualisée
- **Outperformance vs benchmarks** (OAT 10Y, Immobilier, ETF World via `yfinance`)

### 🎯 **Analyse de Risque**
- **Concentration par émetteur** (Indice de Herfindahl)
- **Stress testing** multi-scénarios (Simulation Monte Carlo via `financial_freedom.py`)
- **Analyse de retards** et projets en difficulté
- **Diversification géographique** et sectorielle
- **Ratio de Sharpe** adapté au crowdfunding

### 🔄 **Gestion Fiscale Intelligente**
- **Calcul automatique des taxes** (Flat tax 30%, CSG/CRDS)
- **Suivi de la fiscalité** par type d'investissement
- **Optimisation Fiscale des Flux Entrants** : Analyse des dépôts et réinvestissements pour des stratégies d'optimisation fiscale (ex: utilisation d'enveloppes fiscales, via `analyze_tax_optimization_of_flows`).

### 🏢 **Support Multi-Plateformes**
- **LPB (La Première Brique)** - Crowdfunding immobilier
- **PretUp** - Crédit immobilier participatif  
- **BienPrêter** - Financement de promoteurs
- **Homunity** - Investissement immobilier digital
- **PEA Bourse Direct** - Actions et ETF
- **Assurance Vie Linxea** - Fonds et UC

## 🚀 Installation Rapide

### 1. **Prérequis**
```bash
# Python 3.8+ requis
python --version

# Installer les dépendances
pip install -r requirements.txt
```

### 2. **Configuration Base de Données**
Créez un fichier `.env` à la racine de votre projet avec les informations suivantes :
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
DEFAULT_USER_ID=your_user_id # Votre ID utilisateur par défaut
```

### 3. **Structure des Fichiers**
Organisez vos fichiers comme suit :
```
data/raw/
├── Portefeuille LPB 20250529.xlsx
├── Portefeuille PretUp 20250529.xlsx
├── Portefeuille BienPreter 20250529.xlsx
├── Portefeuille Homunity 20250529.xlsx
├── Portefeuille AV Linxea.xlsx
└── pea/
    ├── releve_pea_avril_2025.pdf
    └── evaluation_pea_avril_2025.pdf
```

### 4. **Lancement**
```bash
# Lancement du dashboard Streamlit
streamlit run frontend/dashboard.py

# Chargement des données (optionnel, si vous n'avez pas encore chargé vos données)
# Utilisez --user_id si votre ID utilisateur est différent de celui par défaut dans .env
python scripts/load_sample_data.py load [--user_id your_user_id] [--platforms platform1 platform2 ...]
```

## 📂 Structure du Projet

Une vue d'ensemble de l'organisation des fichiers et répertoires du projet.

### Répertoires Principaux

*   `.git/`: Répertoire de contrôle de version Git.
*   `backend/`: Contient la logique métier, les API, les modèles de données et les outils d'analyse.
*   `data/`: Stocke les données brutes et traitées, organisées par type (ex: pea).
*   `docs/`: Documentation du projet.
*   `exports/`: Pour les fichiers exportés ou les rapports générés.
*   `frontend/`: Contient l'interface utilisateur (dashboard).
*   `logs/`: Pour les fichiers de logs de l'application.
*   `scripts/`: Contient divers scripts pour des tâches spécifiques (chargement de données, débogage, etc.).
*   `temp_pea_uploads/`: Répertoire temporaire pour les fichiers PDF de PEA avant traitement.
*   `venv/`: L'environnement virtuel Python, contenant les dépendances du projet.

### Analyse Détaillée des Répertoires Clés

#### `backend/`
Le cœur de l'application, regroupant la logique métier et les services.
*   `analytics/`: Logique d'analyse financière.
    *   `patrimoine_calculator.py`: Moteur de calcul centralisé pour le dashboard, gérant les KPIs globaux, les métriques par plateforme, les détails des projets de crowdfunding, et la performance périodique. Utilise `scipy.optimize.fsolve` pour le calcul du TRI (XIRR) et `yfinance` pour les données de benchmark.
    *   `financial_freedom.py`: Module de simulation de liberté financière, incluant des projections Monte Carlo, une analyse d'impact des allocations d'actifs et une analyse de sensibilité. Utilise `numpy`, `pandas`, `plotly` et `streamlit`.
*   `data/`: Gère le chargement et le parsing des données.
    *   `data_loader.py`: Module responsable du chargement des données brutes (Excel et PDF) dans la base de données. Il orchestre l'utilisation de `UnifiedPortfolioParser` pour le parsing et `ExpertDatabaseManager` pour l'insertion. Inclut des méthodes pour le chargement par plateforme, le chargement complet du PEA, et la validation des fichiers. **Améliorations**: Les fonctions de chargement et de validation utilisent désormais un mapping interne (`PLATFORM_MAPPING`) pour assurer la cohérence des noms de plateformes entre les fichiers sources et la base de données.
    *   `parser_constants.py`: Centralise toutes les constantes (noms de feuilles Excel, noms de plateformes, patterns de classification des flux de trésorerie, expressions régulières) utilisées par le `UnifiedPortfolioParser`, assurant flexibilité et maintenabilité. **Améliorations**: Inclut désormais un `PLATFORM_MAPPING` pour faciliter la correspondance entre les noms abrégés et complets des plateformes.
    *   `unified_parser.py`: Pour unifier et parser les différents formats de données (notamment les PDF de PEA).
*   `models/`: Définit la structure de la base de données et les modèles de données.
    *   `database.py`: Le gestionnaire principal de la base de données. Il utilise Supabase pour les opérations CRUD sur toutes les tables (investments, cash_flows, portfolio_positions, liquidity_balances, expert_metrics_cache, financial_goals, user_preferences). Il intègre la validation des données via les modèles Pydantic, utilise les vues PostgreSQL pour des requêtes optimisées, gère le caching des métriques, permet l'analyse de la qualité des données et l'exportation des données utilisateur. **Améliorations**: La fonction `clear_platform_data` utilise désormais le `PLATFORM_MAPPING` pour s'assurer que le nom complet de la plateforme est utilisé lors de la suppression des données, évitant ainsi les problèmes de doublons.
    *   `models.py`: Définit les schémas de données (modèles Pydantic) pour toutes les entités de la base de données : `Investment`, `CashFlow`, `PortfolioPosition`, `ExpertMetricCache`, `FinancialGoal`, `UserPreference`, et `LiquidityBalance`. Ces modèles assurent la validation des données, la définition des types de champs, et l'application de contraintes (par exemple, `Field(gt=0)` pour les montants positifs, `Literal` pour les valeurs énumérées).
    *   `schema_bd.sql`: Contient le schéma SQL complet de la base de données PostgreSQL. Cela inclut les définitions de tables (`investments`, `cash_flows`, `portfolio_positions`, `expert_metrics_cache`, `financial_goals`, `user_preferences`, `liquidity_balances`), les index pour l'optimisation des performances, les contraintes `CHECK` pour l'intégrité des données, les fonctions et triggers pour la gestion automatique des `updated_at`, les vues pour les analyses rapides, un script de migration pour l'évolution du schéma, et des données de test pour le développement.
*   `utils/`: Fonctions utilitaires générales.
    *   `file_helpers.py`: Fournit des fonctions utilitaires génériques pour la manipulation et le nettoyage des données. Cela inclut la standardisation des formats de date (`standardize_date`) et la conversion robuste des chaînes de caractères en montants numériques (`clean_amount`), gérant divers formats régionaux et symboles monétaires.

#### `data/`
Gestion des données brutes et traitées.
*   `processed/pea/`: Données PEA après traitement et normalisation.
*   `raw/pea/`: Données PEA brutes, principalement des fichiers PDF (BD, evaluation, portefeuille, positions, releve).

#### `frontend/`
Interface utilisateur.
*   `dashboard.py`: Le frontend est construit avec [Streamlit](https://streamlit.io/), offrant un dashboard interactif pour visualiser les analyses financières. Il interagit principalement avec `backend.analytics.patrimoine_calculator.PatrimoineCalculator` pour récupérer et afficher les données.

#### `scripts/`
Scripts pour diverses tâches.
*   `check_constraint.py`: Outil de diagnostic pour vérifier les contraintes de la base de données, notamment les types de flux (`flow_type`) et les champs numériques (`duration_months`). Il fournit des recommandations pour la correction des données ou l'ajustement du schéma.
*   `clear_database.py`: Script interactif en ligne de commande pour la gestion des données de la base de données. Il permet de visualiser les statistiques, de supprimer toutes les données, de supprimer les données d'un utilisateur spécifique, ou de vider une table particulière.
*   `config.py`: Centralise les configurations du projet, telles que les clés d'API Supabase, les chemins des répertoires de données, et les mappings pour les plateformes et les types d'investissement. Ce fichier assure une gestion centralisée et facile des paramètres globaux de l'application.
*   `debug_bienpreter_parser.py`, `debug_homunity_parser.py`, `debug_lpb_parser.py`, `debug_pea_parser.py`, `debug_pea_structure.py`: Scripts de débogage spécifiques au parsing des données.
*   `load_sample_data.py`: Script multifonctionnel pour la gestion des données. Il permet le chargement automatique des données brutes, le nettoyage et le rechargement complet des données utilisateur, et la vérification du statut actuel de la base de données.
    *   **Utilisation**: `python scripts/load_sample_data.py [command] [--user_id <id>] [--platforms <platform1> <platform2> ...]`
    *   **Commandes**:
        *   `load` (Défaut): Charge les données brutes depuis `data/raw` vers la base de données.
        *   `clean`: Supprime les données existantes pour un utilisateur (ou des plateformes spécifiques) puis recharge les données.
        *   `check`: Vérifie le statut actuel de la base de données pour un utilisateur, affichant des statistiques sur les investissements, les flux et les positions.
    *   **Arguments Optionnels**:
        *   `--user_id`: Spécifie l'ID de l'utilisateur pour lequel opérer. Défaut: `29dec51d-0772-4e3a-8e8f-1fece8fefe0e`.
        *   `--platforms`: Liste des plateformes spécifiques à traiter (ex: `lpb pretup`). Si omis, toutes les plateformes sont traitées.


### Fichiers Importants à la Racine

*   `requirements.txt`: Liste toutes les dépendances Python du projet.
*   `README.md`: Description du projet, instructions d'installation et d'utilisation.
*   `.gitignore`: Spécifie les fichiers et répertoires à ignorer par Git.

## 🗄️ Base de Données

Le projet utilise une base de données PostgreSQL pour stocker les informations financières. Voici les tables principales et leur rôle.

### Tables Principales

1.  **`investments`**
    *   **Rôle**: Stocke les informations détaillées sur chaque investissement réalisé par un utilisateur.
    *   **Clé Primaire**: `id` (UUID, généré automatiquement).
    *   **Clés Étrangères**: `user_id` (UUID, non nulle).
    *   **Colonnes Clés**:
        *   `platform`: Plateforme d'investissement (LPB, PretUp, BienPreter, Homunity, PEA, Assurance_Vie).
        *   `investment_type`: Type d'investissement (crowdfunding, stocks, bonds, funds).
        *   `asset_class`: Classe d'actifs (real_estate, equity, fixed_income, mixed).
        *   `project_name`, `company_name`, `isin`: Détails spécifiques à l'investissement.
        *   `invested_amount`, `annual_rate`, `duration_months`: Données financières.
        *   `capital_repaid`, `remaining_capital`, `monthly_payment`: Suivi du capital et des flux.
        *   `investment_date`, `signature_date`, `expected_end_date`, `actual_end_date`: Dates importantes pour le calcul du TRI (Taux de Rentabilité Interne).
        *   `status`: Statut de l'investissement (active, completed, delayed, defaulted, in_procedure).
        *   `is_delayed`, `is_short_term`: Indicateurs pour l'analyse.
    *   **Commentaires**: Très complet pour le suivi des investissements multi-plateformes, avec des champs spécifiques pour le calcul du TRI et l'analyse de liquidité.

2.  **`cash_flows`**
    *   **Rôle**: Enregistre tous les flux de trésorerie (dépôts, investissements, remboursements, intérêts, dividendes, frais, ventes, etc.) liés aux investissements ou au compte utilisateur.
    *   **Clé Primaire**: `id` (UUID, généré automatiquement).
    *   **Clés Étrangères**: `investment_id` (UUID, référence `investments.id`, peut être NULL pour les flux non liés à un investissement spécifique), `user_id` (UUID, non nulle).
    *   **Colonnes Clés**:
        *   `platform`: CRUCIAL pour la traçabilité et les calculs de TRI par plateforme.
        *   `flow_type`: Type de flux (deposit, investment, repayment, interest, dividend, fee, sale, other).
        *   `flow_direction`: Direction du flux (in, out).
        *   `gross_amount`, `net_amount`, `tax_amount`: Montants détaillés pour la gestion fiscale.
        *   `capital_amount`, `interest_amount`: Détail pour les analyses de TRI.
        *   `transaction_date`: Date du flux.
    *   **Commentaires**: La colonne `platform` ajoutée est une excellente initiative pour des analyses granulaires. La distinction entre `gross_amount`, `net_amount`, et `tax_amount` est essentielle pour une gestion fiscale précise.

3.  **`portfolio_positions`**
    *   **Rôle**: Suivi des positions actuelles pour les portefeuilles de type PEA et Assurance Vie.
    *   **Clé Primaire**: `id` (UUID, généré automatiquement).
    *   **Clés Étrangères**: `user_id` (UUID, non nulle).
    *   **Colonnes Clés**:
        *   `platform`: PEA, Assurance_Vie.
        *   `isin`: Code ISIN de l'actif.
        *   `asset_name`, `asset_class`: Nom et classe de l'actif.
        *   `quantity`, `current_price`, `market_value`, `portfolio_percentage`: Détails de la position.
        *   `valuation_date`: Date de valorisation.
    *   **Commentaires**: Permet une vue instantanée de la composition et de la valeur des portefeuilles gérés.

4.  **`expert_metrics_cache`**
    *   **Rôle**: Cache les métriques calculées (TRI, capital en cours, concentration, etc.) pour optimiser les performances et éviter des recalculs coûteux.
    *   **Clé Primaire**: `id` (UUID, généré automatiquement).
    *   **Clés Étrangères**: `user_id` (UUID, non nulle).
    *   **Colonnes Clés**:
        *   `platform`: Peut être NULL pour les métriques globales.
        *   `metric_type`: Type de métrique.
        *   `metric_value`, `metric_percentage`, `metric_json`: Valeurs des métriques (JSONB pour les données complexes).
        *   `calculation_date`, `calculation_period_start`, `calculation_period_end`: Métadonnées du calcul.
    *   **Contrainte Unique**: `UNIQUE(user_id, platform, metric_type)` assure l'unicité des entrées de cache.
    *   **Commentaires**: Très bonne pratique pour une application orientée performance, surtout avec des calculs financiers complexes.

5.  **`financial_goals`**
    *   **Rôle**: Gère les objectifs financiers des utilisateurs.
    *   **Clé Primaire**: `id` (UUID, généré automatiquement).
    *   **Clés Étrangères**: `user_id` (UUID, référence `auth.users.id` avec `ON DELETE CASCADE`).
    *   **Colonnes Clés**: `goal_name`, `goal_type`, `target_amount`, `target_date`, `monthly_contribution`, `expected_return_rate`.
    *   **Commentaires**: Permet de suivre la progression vers des objectifs comme l'indépendance financière ou l'achat immobilier.

6.  **`user_preferences`**
    *   **Rôle**: Stocke les préférences et le profil d'investisseur de chaque utilisateur.
    *   **Clé Primaire**: `user_id` (UUID, référence `auth.users.id` avec `ON DELETE CASCADE`).
    *   **Colonnes Clés**: `age`, `risk_tolerance`, `investment_horizon_years`, `default_currency`, `preferred_allocation` (JSONB), `notification_settings` (JSONB).
    *   **Commentaires**: Essentiel pour personnaliser l'expérience utilisateur et adapter les analyses.

7.  **`liquidity_balances`**
    *   **Rôle**: Suivi des soldes de liquidités par plateforme et par date.
    *   **Clé Primaire**: `id` (UUID, généré automatiquement).
    *   **Clés Étrangères**: `user_id` (UUID, non nulle).
    *   **Colonnes Clés**: `platform`, `balance_date`, `amount`.
    *   **Contrainte Unique**: `UNIQUE(user_id, platform, balance_date)` assure une seule entrée par jour et par plateforme.
    *   **Commentaires**: Très utile pour l'analyse de la liquidité disponible sur chaque plateforme.

### Optimisations de la Base de Données

*   **Index pour les Performances**: Des index sont créés sur les colonnes fréquemment utilisées dans les requêtes (`user_id`, `platform`, `status`, `transaction_date`, `isin`, `metric_type`, `balance_date`).
*   **Contraintes de Vérification (`CHECK`)**: Des contraintes `CHECK` sont définies pour `cash_flows` (`flow_direction`, `flow_type`) et `investments` (`status`, `platform`) pour assurer l'intégrité des données.
*   **Fonctions et Triggers**: 
    *   `update_updated_at_column()`: Une fonction PL/pgSQL qui met à jour automatiquement la colonne `updated_at` avec l'horodatage actuel lors d'une mise à jour de ligne.
    *   Triggers `update_investments_updated_at` et `update_positions_updated_at`: Ces triggers appellent la fonction `update_updated_at_column()` avant chaque mise à jour sur les tables `investments` et `portfolio_positions`. C'est une pratique courante et recommandée pour le suivi des modifications.
*   **Vues pour Analyses Rapides**: 
    Trois vues sont définies pour faciliter les analyses courantes :
    *   `v_platform_summary`: Résumé des investissements par utilisateur et par plateforme (nombre d'investissements, montants investis, statuts, durée moyenne, etc.).
    *   `v_monthly_flows`: Agrégation des flux de trésorerie par mois, utilisateur, plateforme et direction du flux.
    *   `v_concentration_analysis`: Analyse de la concentration des investissements par émetteur (company_name), calculant la part en pourcentage de chaque émetteur dans le portefeuille.
*   **Script de Schéma (`schema_bd.sql`)**: Le fichier `backend/models/schema_bd.sql` contient le schéma complet de la base de données. Il est conçu pour créer ou mettre à jour les tables sans supprimer le schéma `public` existant, préservant ainsi les configurations comme les politiques RLS.
*   **Politiques RLS (Row Level Security)**: Des politiques RLS sont mises en place pour assurer l'isolation des données par utilisateur. Elles doivent être configurées manuellement dans votre tableau de bord Supabase pour chaque table (`investments`, `cash_flows`, `portfolio_positions`, etc.) afin de permettre aux utilisateurs de lire et écrire uniquement leurs propres données.
*   **Données de Test (`generate_test_data`)**: Une fonction `generate_test_data` est fournie pour insérer des données d'exemple. C'est extrêmement utile pour le développement, les tests et la démonstration de l'application.

## ⚙️ Composants Clés

### `backend/data/unified_parser.py` - Le Cœur de l'Extraction de Données

Le fichier `backend/data/unified_parser.py` contient la classe `UnifiedPortfolioParser`, qui est le cœur du système pour l'extraction et la normalisation des données financières provenant de diverses plateformes.

#### Objectif Général

Le `UnifiedPortfolioParser` vise à transformer des données brutes (principalement des fichiers Excel et PDF) issues de différentes plateformes d'investissement en un format structuré et unifié, prêt à être inséré dans la base de données (`investments`, `cash_flows`, `portfolio_positions`, `liquidity_balances`).

#### Architecture Modulaire

*   `platform_methods`: La classe utilise un dictionnaire `platform_methods` pour mapper chaque plateforme (LPB, PretUp, BienPrêter, Homunity, Assurance Vie, PEA) à une méthode de parsing spécifique (`_parse_lpb`, `_parse_pretup`, etc.). Cela rend le code modulaire et facile à étendre.
*   Point d'entrée `parse_platform`: Cette méthode est le point d'entrée principal, prenant le chemin du fichier et le nom de la plateforme, puis déléguant le travail à la méthode appropriée.

#### Traitement des Fichiers Excel

Pour ces plateformes, le parser s'appuie fortement sur la bibliothèque `pandas` pour lire les fichiers Excel.

*   **LPB (La Première Brique)**:
    *   **Parsing des Projets (`_parse_lpb_projects`)**: Utilise l'onglet 'Projets' comme source de vérité pour le capital investi et remboursé. Le statut initial est défini ici.
    *   **Parsing des Échéanciers (`_parse_lpb_schedules`)**: Lit les onglets d'échéancier pour chaque projet. Détecte automatiquement les projets en 'prolongation' et les marque comme 'delayed'.
    *   **Parsing du Relevé de Compte (`_parse_lpb_account`)**: Utilise le relevé de compte pour les dates de transaction réelles. Pour les remboursements, il se base sur les échéanciers pour une ventilation précise du capital, des intérêts et des taxes. Les flux de taxes (CSG/CRDS, IR) ne sont plus créés comme des entrées séparées, car ils sont inclus dans la ventilation des remboursements.
    *   **Post-traitement (`_update_investments_from_cashflows`)**: Met à jour la date de fin réelle des projets terminés en se basant sur la date du dernier remboursement effectif.
*   **BienPrêter**:
    *   **Parsing des Projets (`_parse_bienpreter_projects`)**: Extrait les projets et une table de correspondance. Le statut est mappé via `_map_bienpreter_status`.
    *   **Parsing du Relevé de Compte (`_parse_bienpreter_account`)**: Effectue une liaison fiable par numéro de contrat et une classification robuste des opérations (`_classify_bienpreter_transaction`).
    *   **Post-traitement**: Utilise `_update_investments_from_cashflows` pour mettre à jour les investissements avec les données des flux.
*   **Homunity**:
    *   **Liaison Fiable**: Utilise `_normalize_homunity_key` pour une liaison fiable basée sur le couple (promoteur, projet).
    *   **Parsing des Projets (`_parse_homunity_projects`)**: Gère les lignes de remboursement multiples pour un même projet et calcule le capital remboursé total. Le statut est mappé via `_map_homunity_status`.
    *   **Parsing du Relevé de Compte (`_parse_homunity_account`)**: Lie les flux à l'échéancier par (Promoteur, Projet, Date) et effectue des calculs précis, y compris la mise à jour de la date d'investissement.
*   **PretUp**:
    *   **Logique Fiabilisée (V3)**: Le parser a été entièrement réécrit pour une robustesse maximale, en se basant sur les règles métier que nous avons définies.
    *   **Liaison par Clé Normalisée**: La liaison entre le relevé de compte, les projets et les échéanciers ne se base plus sur des correspondances fragiles. Elle utilise maintenant une **clé de liaison unique et normalisée**, construite à partir du couple (`Nom de l'entreprise`, `Nom du Projet`), après avoir supprimé les accents et standardisé la casse. C'est le cœur de la fiabilisation.
    *   **Classification Stricte**: La classification des flux (`repayment`, `investment`, etc.) se base **uniquement** sur la colonne `Type` du relevé, conformément à vos instructions, ce qui élimine toute ambiguïté.
    *   **Extraction par Regex**: Les montants de capital et d'intérêts sont extraits de manière fiable depuis le libellé des transactions de remboursement grâce à des expressions régulières (regex) précises.
    *   **Gestion des Dates**: La date de fin réelle (`actual_end_date`) est automatiquement calculée en se basant sur la date du dernier remboursement de capital, assurant une mise à jour correcte du statut des projets terminés.
*   **Assurance Vie**:
    *   **Ultra-Robuste**: Le parser (`_parse_assurance_vie`) est conçu pour être ultra-robuste contre les erreurs de type, notamment pour la colonne d'opération. Il tente de lire le premier onglet si l'onglet 'Relevé compte' n'est pas trouvé.
    *   **Classification des Flux**: Gère la classification des flux (dividende, frais, versement, etc.) avec une gestion robuste des cas numériques et des lignes vides/headers.

#### Améliorations Générales du Parser

*   **Reconnaissance des Plateformes**: La méthode `parse_platform` utilise désormais un mapping interne (`PLATFORM_MAPPING`) pour convertir les noms complets des plateformes en clés abrégées, assurant une meilleure robustesse et flexibilité dans la reconnaissance des plateformes.

#### Traitement des Fichiers PDF (PEA)

Le parsing des PDF est la partie la plus complexe et la plus robuste du parser, utilisant `pdfplumber` pour l'extraction.

*   **Approche Multi-fichiers**: La méthode `_parse_pea` accepte désormais des listes de chemins de fichiers pour les relevés et les évaluations, permettant un contrôle externe plus fin. Elle stocke les positions de portefeuille et les soldes de liquidités en tant qu'attributs de la classe pour une récupération ultérieure.
*   **Extraction de la date de valorisation (`_extract_valuation_date`)**: Fonction cruciale qui tente d'extraire la date de valorisation du portefeuille en priorité depuis le nom du fichier (avec une robustesse améliorée pour divers formats de date comme `YYYYMM`), puis depuis le contenu textuel du PDF.
*   **Parsing des Relevés (Transactions)**:
    *   `_parse_pea_releve`: Lit le texte page par page et ligne par ligne.
    *   `_parse_pea_transaction_line`: Analyse chaque ligne de transaction avec une logique sophistiquée de reconnaissance de montants (gérant les formats avec espaces, virgules, et entiers) et de calcul des frais.
    *   **Classification des flux**: Identifie le type de flux (dividende, achat, vente, frais, dépôt) et la direction.
*   **Parsing des Évaluations (Positions et Liquidités)**:
    *   `_parse_pea_evaluation`: Extrait les tables pour les positions et le texte pour les soldes de liquidités.
    *   `_parse_pea_positions_to_portfolio`: Analyse les tableaux extraits par `pdfplumber`. Gère les données multi-lignes via `_parse_multiligne_synchronized` pour une extraction précise des désignations, quantités, prix, valeurs et pourcentages.
    *   `_is_section_header`: Détermine si une ligne est un en-tête de section ou un total, en se basant sur des mots-clés et, de manière cruciale, en ignorant les lignes contenant un ISIN.
    *   `_clean_pea_designation`: Nettoie les noms d'actifs PEA en supprimant les codes internes.
    *   `_classify_pea_asset`: Tente de classer l'actif (ETF, fonds, obligation, action) en fonction de son nom.
    *   **Extraction de liquidités**: La liquidité est extraite directement du texte de la page d'évaluation et stockée dans `self.pea_liquidity_balance`.

#### Fonctions Utilitaires (`backend.utils.file_helpers`)

Le parser s'appuie sur des fonctions externes pour :
*   `standardize_date`: Normaliser les formats de date.
*   `clean_amount`: Nettoyer et convertir les chaînes de caractères en montants numériques.
*   `clean_string_operation`, `safe_get`: Pour des opérations de nettoyage de chaînes et d'accès sécurisé aux données.

#### Points Forts du Parser

*   **Modularité et Extensibilité**: Facile d'ajouter de nouvelles plateformes.
*   **Robustesse du Parsing PDF**: La logique pour extraire les dates, les montants et les positions des PDF est très élaborée, gérant les variations de format et les données semi-structurées.
*   **Gestion Fiscale Détaillée**: La distinction entre montants bruts, nets et taxes est cruciale pour une analyse financière précise.
*   **Nettoyage et Standardisation**: Les fonctions utilitaires garantissent la cohérence des données.
*   **Journalisation (Logging)**: L'utilisation intensive du module `logging` est excellente pour le débogage et le suivi des erreurs.

#### Points à Surveiller / Améliorations Possibles

*   **Dépendance au Format Source**: Le parsing est intrinsèquement lié à la structure des fichiers sources. Tout changement majeur dans les relevés des plateformes pourrait nécessiter des ajustements.
*   **Complexité des Regex**: Les expressions régulières pour l'extraction des montants et des descriptions dans les PDF sont complexes et peuvent être difficiles à maintenir.
*   **Gestion des Erreurs**: Une gestion plus fine des erreurs (par exemple, des exceptions spécifiques pour des problèmes de format) pourrait être envisagée.
*   **Effets de Bord**: Le stockage des positions PEA et des soldes de liquidités comme attributs de la classe (`self.pea_portfolio_positions`, etc.) est un effet de bord dont le code appelant doit être conscient.

## 📈 Métriques Calculées

### **TRI Expert (XIRR)**
- Calcul avec **dates réelles** d'investissement (vs signatures) en utilisant `scipy.optimize.fsolve` pour une robustesse accrue (multiples tentatives de convergence).
- Prise en compte des **flux d'argent frais uniquement** et de la **valorisation actuelle du patrimoine** comme flux final.
- **Benchmark automatique** vs OAT 10Y (3.5%), Immobilier (5.5%) et ETF World (via `yfinance`), normalisé par rapport aux apports réels.
- **Analyse par plateforme** pour optimiser l'allocation

### **Capital en Cours**
```
Capital en Cours = Capital Investi - Capital Remboursé + Valorisation Actuelle
```
- **Suivi de l'exposition** par plateforme
- **Taux de remboursement** et rotation du capital
- **Projections de liquidité** à court/moyen terme
- **Taux de réinvestissement** et effet boule de neige
- **Indicateur de Maturité du Portefeuille**



### **Duration et Immobilisation**
- **Duration moyenne pondérée** par montant investi
- **Répartition par échéance** : <6m, 6-12m, >12m
- **Analyse des retards** vs dates prévues
- **Impact liquidité** et optimisation des flux
- **Indicateur de Maturité du Portefeuille**

### **Indicateur de Maturité du Portefeuille**
- **Indicateur de Maturité du Portefeuille** : Un score composite par plateforme évaluant la proportion d'investissements arrivant à terme, la liquidité disponible et la capacité de réinvestissement, donnant une idée de la "vieillesse" ou de la "jeunesse" du portefeuille.

## 🎯 Interprétation Expert

### **Seuils d'Alerte TRI**
- **🟢 > 8%** : Performance excellente
- **🟡 5-8%** : Performance satisfaisante  
- **🟠 3-5%** : Performance correcte
- **🔴 < 3%** : Sous-performance, révision stratégie

### **Concentration Émetteurs**
- **Indice de Herfindahl (HHI)** : Calculé pour évaluer la concentration des investissements par émetteur. Un HHI < 1500 indique une faible concentration, 1500-2500 une concentration modérée, et > 2500 une forte concentration.
- **Part en pourcentage par émetteur**



## 🔧 Architecture Technique

### **Backend Expert**
- **Moteur de calcul centralisé (`PatrimoineCalculator`)** : Gère les KPIs globaux, les métriques par plateforme, les détails des projets de crowdfunding, et la performance périodique.
- **Simulateur de Liberté Financière (`FinancialFreedomSimulator`)** : Projections Monte Carlo, analyse d'impact des allocations d'actifs et analyse de sensibilité.
- **Parser unifié** pour toutes les plateformes
- **Gestion fiscale avancée** (brut/net/taxes)
- **Calculs TRI optimisés** (Newton-Raphson + XIRR)
- **Cache des métriques** pour performances

### **Frontend**
- **Dashboard Expert** : Métriques avancées et recommandations
- **Interface responsive** avec Streamlit et Plotly
- **Graphiques interactifs** et analyses visuelles
- **Export des rapports** en JSON/Excel

## 📊 Cas d'Usage

### **1. Optimisation d'Allocation**
> *"Dois-je privilégier LPB ou PretUp pour mes prochains investissements ?"*

**Analyse TRI comparative** :
- LPB : 9.2% (excellent)
- PretUp : 6.8% (bon)
- BienPrêter : 7.5% (bon)

**Recommandation** : Privilégier LPB tout en surveillant la concentration.

### **2. Gestion de Liquidité**
> *"Combien de capital sera libéré dans les 6 prochains mois ?"*

**Analyse Duration** :
- 12% du portefeuille < 6 mois
- Capital attendu : 15,000€
- Impact liquidité : Faible

### **3. Optimisation Fiscale**
> *"Quel est l'impact fiscal réel de mes investissements ?"*

**Analyse Fiscale** :
- Taxes totales : 2,847€ (4.2% du capital)
- Flat tax moyenne : 28.5%
- Optimisation PEA : +1.2% performance nette

## 🛠️ Maintenance et Support

### **Mise à Jour des Données**
```bash
# Actualisation manuelle
python run_expert_patrimoine.py --load-data

# Validation qualité données
python run_expert_patrimoine.py --analysis-only
```

### **Sauvegarde**
```python
# Export complet des données
from backend.models.corrected_database import ExpertDatabaseManager
db = ExpertDatabaseManager()
export_data = db.export_user_data("your_user_id")
```

### **Performance**
- **Cache automatique** des métriques calculées
- **Requêtes optimisées** avec index sur dates/plateformes


## 🔒 Sécurité et Confidentialité

- **Chiffrement** des données sensibles
- **Isolation utilisateur** complète
- **Logs d'audit** des accès
- **Conformité RGPD** 

## 📞 Support Expert

**Développé par un agent expert** en gestion de patrimoine avec 5+ ans d'expérience dans les produits :
- **PEA/CTO** : Optimisation fiscale et allocation
- **Assurance Vie** : Gestion UC et fonds euros
- **Crowdfunding** : Analyse risque/rendement promoteurs
- **Investissements alternatifs** : Diversification patrimoniale

---

*💎 Expert Patrimoine - Transformez vos données en décisions d'investissement éclairées*

**Version** : 1.0.0  
**Dernière MAJ** : Décembre 2024  
**Licence** : Propriétaire  
**Support** : luc.nazarian@gmail.com