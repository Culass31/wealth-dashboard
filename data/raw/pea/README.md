# Dossier PEA

## Structure des fichiers

Placez vos fichiers PDF de Bourse Direct dans ce dossier :

- `releve_pea_YYYYMM.pdf` : Relevé de compte mensuel
- `evaluation_pea_YYYYMM.pdf` : Évaluation de portefeuille

## Nommage recommandé

- Incluez 'releve' ou 'compte' dans le nom pour les relevés
- Incluez 'evaluation' ou 'portefeuille' dans le nom pour les évaluations
- Ajoutez la date pour organiser vos fichiers

## Exemples

- `releve_pea_202504.pdf`
- `evaluation_portefeuille_avril_2025.pdf`
- `compte_pea_30042025.pdf`

## Note sur la Stabilité du Code

**IMPORTANT** : Lors de toute refactorisation ou ajout de nouvelles fonctionnalités, une attention particulière doit être portée à ne pas casser les fonctionnalités existantes qui fonctionnent correctement. La non-régression est un principe clé de ce projet.

## Chargement

```bash
# Chargement automatique
python load_sample_data_pea.py

# Avec ID utilisateur spécifique
python load_sample_data_pea.py votre-user-id

# Mode interactif
python load_sample_data_pea.py votre-user-id
# puis choisir l'option 2
```
