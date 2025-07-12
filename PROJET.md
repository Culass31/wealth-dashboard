Structure Générale du Projet :

   * `.git/`: Répertoire de contrôle de version Git.
   * `backend/`: Contient la logique métier, les API, les modèles de données et les outils d'analyse.
   * `data/`: Stocke les données brutes et traitées, organisées par type (ex: pea).
   * `docs/`: Probablement pour la documentation du projet.
   * `exports/`: Pour les fichiers exportés ou les rapports générés.
   * `frontend/`: Contient l'interface utilisateur (dashboard).
   * `logs/`: Pour les fichiers de logs de l'application.
   * `scripts/`: Contient divers scripts pour des tâches spécifiques (chargement de données, débogage, etc.).
   * `temp_pea_uploads/`: Un répertoire temporaire, probablement pour les fichiers PDF de PEA avant traitement.
   * `venv/`: L'environnement virtuel Python, contenant les dépendances du projet.
   * Fichiers à la racine: README.md, requirements.txt, .gitignore, et des images de dashboards.

  Analyse Détaillée des Répertoires Clés :

   1. `backend/`: C'est le cœur de votre application.
       * `agents/`: Pour des agents autonomes ou des modules de traitement spécifiques.
       * `analytics/`: Contient la logique d'analyse financière.
           * advanced_metrics.py: Calcul de métriques financières avancées.
           * expert_metrics.py: Métriques spécifiques ou complexes.
           * financial_freedom.py: Logique liée au calcul de l'indépendance financière.
       * `api/`: Probablement pour définir les points d'accès de l'API REST.
       * `data/`: Gère le chargement et le parsing des données.
           * data_loader.py: Pour charger les données depuis différentes sources.
           * unified_parser.py: Pour unifier et parser les différents formats de données (notamment les PDF de PEA).
       * `models/`: Définit la structure de la base de données et les modèles de données.
           * database.py: Connexion et gestion de la base de données.
           * models.py: Définition des modèles ORM (par exemple, avec SQLAlchemy ou Django ORM).
           * schema_bd.sql: Le schéma SQL de la base de données, utile pour la création ou la migration.
       * `utils/`: Fonctions utilitaires générales.
           * file_helpers.py: Fonctions d'aide pour la manipulation des fichiers.

   2. `data/`:
       * `processed/pea/`: Données PEA après traitement et normalisation.
       * `raw/pea/`: Données PEA brutes, principalement des fichiers PDF (BD, evaluation, portefeuille, positions, releve). Le README.md ici
         pourrait contenir des informations sur la source ou le format de ces fichiers.

   3. `frontend/`:
       * dashboard.py: Indique que le frontend est probablement construit avec Streamlit, Dash, ou un autre framework Python pour les
         dashboards interactifs.

   4. `scripts/`:
       * check_constraint.py, check_import.py: Scripts de vérification ou de validation.
       * clear_database.py: Pour nettoyer la base de données.
       * config.py: Fichier de configuration pour les scripts.
       * debug_pea_parser.py, debug_pea_structure.py: Scripts de débogage spécifiques au parsing des données PEA.
       * load_sample_data.py: Pour charger des données d'exemple.
       * run_expert_patrimoine.py: Pour exécuter des analyses spécifiques.

  Fichiers Importants à la Racine :

   * requirements.txt: Liste toutes les dépendances Python du projet.
   * README.md: Devrait contenir une description du projet, les instructions d'installation et d'utilisation.
   * .gitignore: Spécifie les fichiers et répertoires à ignorer par Git.


    Base de donnée : Tables Principales et Leur Rôle :

   1. `investments`:
       * Rôle: Stocke les informations détaillées sur chaque investissement réalisé par un utilisateur.
       * Clé Primaire: id (UUID, généré automatiquement).
       * Clés Étrangères: user_id (UUID, non nulle).
       * Colonnes Clés:
           * platform: Plateforme d'investissement (LPB, PretUp, BienPreter, Homunity, PEA, Assurance\_Vie).
           * investment_type: Type d'investissement (crowdfunding, stocks, bonds, funds).
           * asset_class: Classe d'actifs (real\_estate, equity, fixed\_income, mixed).
           * project_name, company_name, isin: Détails spécifiques à l'investissement.
           * invested_amount, annual_rate, duration_months: Données financières.
           * capital_repaid, remaining_capital, monthly_payment: Suivi du capital et des flux.
           * investment_date, signature_date, expected_end_date, actual_end_date: Dates importantes pour le calcul du TRI (Taux de Rentabilité
             Interne).
           * status: Statut de l'investissement (active, completed, delayed, defaulted, in\_procedure).
           * is_delayed, is_short_term: Indicateurs pour l'analyse.
       * Commentaires: Très complet pour le suivi des investissements multi-plateformes, avec des champs spécifiques pour le calcul du TRI et
         l'analyse de liquidité.

   2. `cash_flows`:
       * Rôle: Enregistre tous les flux de trésorerie (dépôts, investissements, remboursements, intérêts, dividendes, frais, ventes, etc.)
         liés aux investissements ou au compte utilisateur.
       * Clé Primaire: id (UUID, généré automatiquement).
       * Clés Étrangères: investment_id (UUID, référence investments.id, peut être NULL pour les flux non liés à un investissement
         spécifique), user_id (UUID, non nulle).
       * Colonnes Clés:
           * platform: CRUCIAL pour la traçabilité et les calculs de TRI par plateforme.
           * flow_type: Type de flux (deposit, investment, repayment, interest, dividend, fee, sale, other).
           * flow_direction: Direction du flux (in, out).
           * gross_amount, net_amount, tax_amount: Montants détaillés pour la gestion fiscale.
           * capital_amount, interest_amount: Détail pour les analyses de TRI.
           * transaction_date: Date du flux.
       * Commentaires: La colonne platform ajoutée est une excellente initiative pour des analyses granulaires. La distinction entre
         gross_amount, net_amount, et tax_amount est essentielle pour une gestion fiscale précise.

   3. `portfolio_positions`:
       * Rôle: Suivi des positions actuelles pour les portefeuilles de type PEA et Assurance Vie.
       * Clé Primaire: id (UUID, généré automatiquement).
       * Clés Étrangères: user_id (UUID, non nulle).
       * Colonnes Clés:
           * platform: PEA, Assurance\_Vie.
           * isin: Code ISIN de l'actif.
           * asset_name, asset_class: Nom et classe de l'actif.
           * quantity, current_price, market_value, portfolio_percentage: Détails de la position.
           * valuation_date: Date de valorisation.
       * Commentaires: Permet une vue instantanée de la composition et de la valeur des portefeuilles gérés.

   4. `expert_metrics_cache`:
       * Rôle: Cache les métriques calculées (TRI, capital en cours, concentration, etc.) pour optimiser les performances et éviter des
         recalculs coûteux.
       * Clé Primaire: id (UUID, généré automatiquement).
       * Clés Étrangères: user_id (UUID, non nulle).
       * Colonnes Clés:
           * platform: Peut être NULL pour les métriques globales.
           * metric_type: Type de métrique.
           * metric_value, metric_percentage, metric_json: Valeurs des métriques (JSONB pour les données complexes).
           * calculation_date, calculation_period_start, calculation_period_end: Métadonnées du calcul.
       * Contrainte Unique: UNIQUE(user_id, platform, metric_type) assure l'unicité des entrées de cache.
       * Commentaires: Très bonne pratique pour une application orientée performance, surtout avec des calculs financiers complexes.

   5. `financial_goals`:
       * Rôle: Gère les objectifs financiers des utilisateurs.
       * Clé Primaire: id (UUID, généré automatiquement).
       * Clés Étrangères: user_id (UUID, référence auth.users.id avec ON DELETE CASCADE).
       * Colonnes Clés: goal_name, goal_type, target_amount, target_date, monthly_contribution, expected_return_rate.
       * Commentaires: Permet de suivre la progression vers des objectifs comme l'indépendance financière ou l'achat immobilier.

   6. `user_preferences`:
       * Rôle: Stocke les préférences et le profil d'investisseur de chaque utilisateur.
       * Clé Primaire: user_id (UUID, référence auth.users.id avec ON DELETE CASCADE).
       * Colonnes Clés: age, risk_tolerance, investment_horizon_years, default_currency, preferred_allocation (JSONB), notification_settings
         (JSONB).
       * Commentaires: Essentiel pour personnaliser l'expérience utilisateur et adapter les analyses.

   7. `liquidity_balances`:
       * Rôle: Suivi des soldes de liquidités par plateforme et par date.
       * Clé Primaire: id (UUID, généré automatiquement).
       * Clés Étrangères: user_id (UUID, non nulle).
       * Colonnes Clés: platform, balance_date, amount.
       * Contrainte Unique: UNIQUE(user_id, platform, balance_date) assure une seule entrée par jour et par plateforme.
       * Commentaires: Très utile pour l'analyse de la liquidité disponible sur chaque plateforme.

  Index pour les Performances :

  Des index sont créés sur les colonnes fréquemment utilisées dans les requêtes (user_id, platform, status, transaction_date, isin,
  metric_type, balance_date). C'est une excellente pratique pour garantir de bonnes performances, surtout avec des volumes de données
  croissants.

  Contraintes de Vérification (`CHECK`) :

  Des contraintes CHECK sont définies pour cash_flows (flow_direction, flow_type) et investments (status, platform). Cela assure l'intégrité
  des données en limitant les valeurs possibles pour ces colonnes à des ensembles prédéfinis.

  Fonctions et Triggers :

   * `update_updated_at_column()`: Une fonction PL/pgSQL qui met à jour automatiquement la colonne updated_at avec l'horodatage actuel lors
     d'une mise à jour de ligne.
   * Triggers `update_investments_updated_at` et `update_positions_updated_at`: Ces triggers appellent la fonction update_updated_at_column()
     avant chaque mise à jour sur les tables investments et portfolio_positions. C'est une pratique courante et recommandée pour le suivi des
     modifications.

  Vues pour Analyses Rapides :

  Trois vues sont définies pour faciliter les analyses courantes :

   * `v_platform_summary`: Résumé des investissements par utilisateur et par plateforme (nombre d'investissements, montants investis, statuts,
     durée moyenne, etc.).
   * `v_monthly_flows`: Agrégation des flux de trésorerie par mois, utilisateur, plateforme et direction du flux.
   * `v_concentration_analysis`: Analyse de la concentration des investissements par émetteur (company_name), calculant la part en pourcentage
     de chaque émetteur dans le portefeuille.

  Script de Migration (`DO $$...$$`) :

  Un bloc DO $$...$$ est inclus pour gérer la migration de la colonne platform dans la table cash_flows. Il vérifie si la colonne existe,
  l'ajoute si nécessaire, puis tente de la peupler en se basant sur investment_id ou la description du flux. C'est une approche robuste pour
  les mises à jour de schéma.

  Données de Test (`generate_test_data`) :

  Une fonction generate_test_data est fournie pour insérer des données d'exemple. C'est extrêmement utile pour le développement, les tests
  et la démonstration de l'application.

Fichier backend/data/unified_parser.py

Il contient la classe UnifiedPortfolioParser, qui est le cœur de votre système pour l'extraction et la normalisation des données financières provenant de diverses plateformes.

  1. Objectif Général

  Le UnifiedPortfolioParser vise à transformer des données brutes (principalement des fichiers Excel et PDF) issues de différentes
  plateformes d'investissement en un format structuré et unifié, prêt à être inséré dans votre base de données (investments, cash_flows,
  portfolio_positions, liquidity_balances).

  2. Architecture Modulaire

   * `platform_methods`: La classe utilise un dictionnaire platform_methods pour mapper chaque plateforme (LPB, PretUp, BienPrêter, Homunity, Assurance Vie, PEA) à une méthode de parsing spécifique (_parse_lpb, _parse_pretup, etc.). Cela rend le code modulaire et facile à étendre pour de nouvelles plateformes.
   * Point d'entrée `parse_platform`: Cette méthode est le point d'entrée principal, prenant le chemin du fichier et le nom de la plateforme, puis déléguant le travail à la méthode appropriée.

  3. Traitement des Fichiers Excel (LPB, BienPrêter, Homunity, Assurance Vie)

  Pour ces plateformes, le parser s'appuie fortement sur la bibliothèque pandas pour lire les fichiers Excel.

   * Lecture par onglet: Il lit généralement des onglets spécifiques comme 'Projets' (pour les investissements) et 'Relevé compte' (pour les flux de trésorerie).
   * Extraction de données: Il parcourt les lignes de chaque DataFrame Pandas, extrayant les informations pertinentes (nom du projet, montant investi, dates, taux, etc.) et les nettoyant à l'aide de fonctions utilitaires (standardize_date, clean_amount).
   * Classification des flux: Des méthodes comme _classify_lpb_transaction sont utilisées pour déterminer le type et la direction des flux de trésorerie en fonction de la description de l'opération.
   * Gestion des taxes: Pour LPB et BienPrêter, il y a une logique spécifique pour extraire et calculer les montants bruts, nets et les taxes (CSG/CRDS, IR) à partir des relevés.
   * Liaison Investissement-Flux: Il tente de lier les flux de trésorerie aux investissements correspondants en utilisant des identifiants de plateforme ou des noms de projets extraits des descriptions.
   * Post-traitement: Pour BienPrêter, un post-traitement est effectué pour mettre à jour le capital remboursé et restant dû dans les objets investissements après avoir traité tous les flux.

  4. Traitement des Fichiers PDF (PEA)

  Le parsing des PDF est la partie la plus complexe et la plus robuste du parser, utilisant pdfplumber pour l'extraction.

   * Approche Multi-fichiers: Pour le PEA, le parser ne se limite pas à un seul fichier. La méthode _parse_pea recherche tous les fichiers
     d'évaluation (evaluation, portefeuille, positions) et de relevé (releve) pertinents dans le répertoire data/raw/pea/ via _find_all_pea_evaluation_files.
   * Extraction de la date de valorisation (`_extract_valuation_date`): C'est une fonction cruciale qui tente d'extraire la date de
     valorisation du portefeuille en priorité depuis le nom du fichier (en gérant divers formats de noms de fichiers), puis, en dernier
     recours, depuis le contenu textuel du PDF.
   * Parsing des Relevés (Transactions):
       * _parse_pea_releve: Lit le texte page par page et ligne par ligne.
       * _parse_pea_transaction_line: Analyse chaque ligne de transaction. C'est ici que la logique la plus sophistiquée de reconnaissance de montants est mise en œuvre, avec plusieurs étapes de recherche (montants avec espaces, montants simples avec virgule, entiers, et un fallback clean_amount). Il tente également de calculer les frais de transaction.
       * Classification des flux: Identifie le type de flux (dividende, achat, vente, frais, dépôt) et la direction.
   * Parsing des Évaluations (Positions et Liquidités):
       * _parse_pea_evaluation: Extrait les tables pour les positions et le texte pour les soldes de liquidités.
       * _extract_liquidity_from_text: Recherche des patterns spécifiques dans le texte complet du PDF pour trouver le solde de liquidités
         (LIQUIDITES, SOLDE ESPECES).
       * _parse_pea_positions_to_portfolio: Analyse les tableaux extraits par pdfplumber. Il identifie les colonnes pertinentes (désignation, quantité, cours, valeur) et filtre les lignes d'en-tête ou de totaux grâce à _is_section_header (qui est très important pour ignorer les lignes qui ne sont pas des actifs réels).
       * _is_section_header: Une fonction clé qui détermine si une ligne est un en-tête de section ou un total, en se basant sur des mots-clés et, surtout, en vérifiant l'absence d'ISIN (code d'identification des titres).
       * _clean_pea_designation: Nettoie les noms d'actifs PEA en supprimant des codes internes comme "025".
       * _classify_pea_asset: Tente de classer l'actif (ETF, fonds, obligation, action) en fonction de son nom.

  5. Fonctions Utilitaires (`backend.utils.file_helpers`)

  Le parser s'appuie sur des fonctions externes pour :
   * standardize_date: Normaliser les formats de date.
   * clean_amount: Nettoyer et convertir les chaînes de caractères en montants numériques (gérant les virgules, points, espaces).
   * clean_string_operation, safe_get: Pour des opérations de nettoyage de chaînes et d'accès sécurisé aux données.

  6. Structure de Sortie

  Les méthodes de parsing retournent des tuples de listes de dictionnaires, par exemple (investissements, flux_tresorerie). Pour le PEA et
  PretUp, les positions de portefeuille et les soldes de liquidités sont stockés comme attributs de la classe (self.pea_portfolio_positions, self.pea_liquidity_balance, self.pretup_liquidity_balance) et peuvent être récupérés via des méthodes dédiées (get_pea_portfolio_positions, get_pea_liquidity_balance, get_pretup_liquidity_balance).

  Points Forts :

   * Modularité et Extensibilité: Facile d'ajouter de nouvelles plateformes.
   * Robustesse du Parsing PDF: La logique pour extraire les dates, les montants et les positions des PDF est très élaborée, gérant les
     variations de format et les données semi-structurées. L'utilisation de pdfplumber pour les tables et le texte est appropriée.
   * Gestion Fiscale Détaillée: La distinction entre montants bruts, nets et taxes est cruciale pour une analyse financière précise.
   * Nettoyage et Standardisation: Les fonctions utilitaires garantissent la cohérence des données.
   * Journalisation (Logging): L'utilisation intensive du module logging est excellente pour le débogage et le suivi des erreurs lors du
     traitement des fichiers.

  Points à Surveiller / Améliorations Possibles :

   * Dépendance au Format Source: Bien que robuste, le parsing est intrinsèquement lié à la structure des fichiers sources (colonnes Excel,
     mise en page PDF). Tout changement majeur dans les relevés des plateformes pourrait nécessiter des ajustements dans le code.
   * Complexité des Regex: Les expressions régulières pour l'extraction des montants et des descriptions dans les PDF sont complexes et
     peuvent être difficiles à maintenir ou à adapter.
   * Gestion des Erreurs: Bien que le logging soit présent, une gestion plus fine des erreurs (par exemple, des exceptions spécifiques pour
     des problèmes de format) pourrait être envisagée pour des pipelines de données plus robustes.
   * Effets de Bord: Le stockage des positions PEA et des soldes de liquidités comme attributs de la classe (self.pea_portfolio_positions,
     etc.) est un effet de bord. Le code appelant doit être conscient de cela et appeler les méthodes get_... appropriées après le parsing.