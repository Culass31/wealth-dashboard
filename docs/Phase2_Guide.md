# Wealth Dashboard Phase 2 - Guide d'Utilisation

## 🚀 Nouveautés Phase 2

### Navigation Unifiée
- **Dashboard Principal** : Vue d'ensemble classique
- **Analyses Avancées** : TRI, Sharpe, VaR, benchmarks
- **Simulateur Liberté** : Projections Monte Carlo
- **Gestion PEA** : Parser et analyse des PDFs Bourse Direct
- **Configuration** : Paramètres et maintenance

### Parser PEA Intégré
- Support des PDFs Bourse Direct
- Extraction automatique des transactions
- Classification des actifs (actions, ETFs, fonds)
- Calcul des positions et valorisations

## 🎯 Utilisation

### Lancement Principal
```bash
python launch_wealth_dashboard.py
# Ou directement :
streamlit run frontend/app.py
```

### Chargement des Données

#### Crowdfunding (existant)
1. Allez dans la barre latérale
2. Uploadez votre fichier Excel (.xlsx)
3. Sélectionnez la plateforme
4. Cliquez "Charger Crowdfunding"

#### PEA (nouveau)
1. **Option 1 - Interface Web** :
   - Uploadez vos PDFs dans la barre latérale
   - Relevé de compte + Évaluation de portefeuille
   - Cliquez "Charger PEA"

2. **Option 2 - Script Dédié** :
   ```bash
   python load_sample_data_pea.py
   ```

### Organisation des Fichiers

```
data/raw/
├── pea/                          # Fichiers PEA
│   ├── releve_pea_202504.pdf    # Relevé de compte
│   └── evaluation_pea_202504.pdf # Évaluation portefeuille
├── Portefeuille LPB 20250529.xlsx
├── Portefeuille PretUp 20250529.xlsx
└── ...
```

## 📊 Nouvelles Analyses

### TRI (Taux de Rendement Interne)
- TRI global du portefeuille
- TRI par plateforme
- Multiple de capital

### Métriques de Risque
- **Sharpe Ratio** : Rendement ajusté du risque
- **VaR** : Value at Risk (perte potentielle)
- **Volatilité** : Écart-type des rendements
- **Max Drawdown** : Plus grosse baisse

### Comparaisons Benchmark
- CAC 40, S&P 500, MSCI World
- Alpha (surperformance vs marché)
- Beta (sensibilité marché)

### Simulateur Liberté Financière
- Simulation Monte Carlo (1000+ scénarios)
- Probabilité d'atteindre l'objectif
- Impact des allocations d'actifs
- Analyse de sensibilité

## 🔧 Maintenance

### Tests
```bash
python test_pea_parser.py        # Test parser PEA
python test_and_load_complete.py # Test complet
```

### Nettoyage
- Utilisez l'onglet "Configuration" 
- Bouton "Vider Cache" pour actualiser
- Bouton "Supprimer Données" pour reset

## 💡 Conseils d'Usage

1. **Chargez d'abord vos données** via les uploads
2. **Commencez par le Dashboard Principal** pour vue d'ensemble
3. **Explorez les Analyses Avancées** pour le TRI et métriques
4. **Utilisez le Simulateur** pour planifier votre liberté financière
5. **Consultez la Gestion PEA** pour vos positions actions

## 🆘 Dépannage

### Erreur "Module not found"
```bash
pip install -r requirements_phase2.txt
```

### Erreur PDF PEA
- Vérifiez que vos PDFs ne sont pas corrompus
- Assurez-vous qu'ils viennent de Bourse Direct
- Essayez de les renommer avec 'releve' ou 'evaluation'

### Cache bloqué
- Utilisez le bouton "Vider Cache" dans Configuration
- Ou redémarrez l'application

### Données manquantes
- Vérifiez que vos uploads ont réussi
- Consultez les logs dans la console
- Utilisez les scripts de chargement dédiés

## 🔗 Navigation Rapide

| Page | Raccourci | Usage |
|------|-----------|-------|
| Dashboard | `?page=dashboard` | Vue d'ensemble |
| Avancé | `?page=advanced` | TRI, métriques |
| Simulateur | `?page=simulator` | Projections |
| PEA | `?page=pea` | Gestion actions |
| Config | `?page=config` | Paramètres |
