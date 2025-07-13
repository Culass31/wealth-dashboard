# backend/data/parser_constants.py
"""
Ce fichier centralise toutes les constantes utilisées par le UnifiedPortfolioParser.
Cela inclut les noms des feuilles Excel, les noms des colonnes, les mots-clés pour la classification
des transactions et les expressions régulières.
"""

# --- Noms des feuilles Excel ---
SHEET_PROJETS = 'Projets'
SHEET_RELEVE_COMPTE = 'Relevé compte'
SHEET_ECHEANCIER = 'Echéancier'

# Constantes spécifiques à PretUp
PRETUP_SHEET_NAMES = {
    'offres_sains': 'Projet Sains - Offres',
    'offres_procedures': 'Procédures - Offres',
    'offres_perdus': 'Perdu - Offres',
    'echeances_sains': 'Projets Sains - Echéances',
    'echeances_procedures': 'Procédures - Echéances',
    'echeances_perdus': 'Perdu - Echéances',
    'releve': 'Relevé compte'
}

# --- Plateformes ---
PLATFORM_LPB = 'La Première Brique'
PLATFORM_BIENPRETER = 'BienPrêter'
PLATFORM_HOMUNITY = 'Homunity'
PLATFORM_PRETUP = 'PretUp'
PLATFORM_ASSURANCE_VIE = 'Assurance_Vie'
PLATFORM_PEA = 'PEA'

# Mapping des noms abrégés aux noms complets des plateformes
PLATFORM_MAPPING = {
    'lpb': PLATFORM_LPB,
    'bienpreter': PLATFORM_BIENPRETER,
    'homunity': PLATFORM_HOMUNITY,
    'pretup': PLATFORM_PRETUP,
    'assurance_vie': PLATFORM_ASSURANCE_VIE,
    'pea': PLATFORM_PEA,
}

# --- Patterns de classification des flux de trésorerie (Cash Flow) ---
# Utilise des expressions régulières pour plus de flexibilité

# LPB
LPB_PATTERNS = {
    'tax': [r'csg', r'crds', r'ir', r'prélèvement'],
    'deposit': [r'crédit du compte'],
    'investment': [r'souscription'],
    'withdrawal': [r'retrait de l\'épargne'],
    'bonus': [r'rémunération', r'code cadeau'],
    'repayment': [r'remboursement mensualité'],
    'cancellation': [r'annulation']
}

# BienPrêter
BIENPRETER_PATTERNS = {
    'repayment': [r'remboursement'],
    'interest': [r'bonus'],
    'deposit': [r'dépôt'],
    'investment': [r'offre acceptée']
}

# Homunity
HOMUNITY_PATTERNS = {
    'deposit': [r'approvisionnement'],
    'investment': [r'investissement', r'souscription'],
    'repayment': [r'remboursement'],
}

# PretUp
PRETUP_PATTERNS = {
    'repayment': [r'échéance', r'remboursement anticipé'],
    'deposit': [r'alimentation'],
    'investment': [r'offre'],
    'balance': [r'solde.*compte']
}

# Assurance Vie
AV_PATTERNS = {
    'dividend': [r'dividende', r'dividend', r'coupon'],
    'fee': [r'frais', r'fee', r'commission'],
    'ignore': [r'arrêté', r'arrete', r'cloture', r'arbitrage', r'transfer'],
    'deposit': [r'versement', r'depot', r'apport']
}

# PEA
PEA_PATTERNS = {
    'dividend': [r'coupons', r'dividende'],
    'purchase': [r'ach cpt', r'achat'],
    'sale': [r'vte cpt', r'vente'],
    'fee': [r'ttf', r'taxe'],
    'deposit': [r'investissement especes'],
    'adjustment': [r'regularisation']
}

# --- Expressions Régulières (Regex) ---

# Regex générique pour extraire ce qui ressemble à un montant
AMOUNT_REGEX = r'(-?[\d\s.,]+)'

# Regex pour trouver un ISIN
ISIN_REGEX = r'([A-Z]{2}[A-Z0-9]{10})'

# Regex pour les liquidités dans les PDF PEA
PEA_LIQUIDITY_PATTERNS = [
    r'(?:TOTAL|SOLDE)?\\s*LIQUIDITES\\s+((?:[\\d\\s,.-]+))'
]

# Regex pour extraire la date de valorisation du contenu d'un PDF
PDF_DATE_PATTERNS = [
    r'Le (\\d{2}/\\d{2}/\\d{4})',
    r'le (\\d{2}/\\d{2}/\\d{4})',
    r'Date\\s*:\\s*(\\d{2}/\\d{2}/\\d{4})',
    r'Arrêté au (\\d{2}/\\d{2}/\\d{4})'
]

# Regex pour extraire la date du nom de fichier
FILENAME_DATE_PATTERNS = [
    r'(\\d{4}-\\d{2}-\\d{2})',  # YYYY-MM-DD
    r'(\\d{2}-\\d{2}-\\d{4})',  # DD-MM-YYYY
    r'(?:evaluation|portefeuille)_(\\d{4})(\\d{2})',  # evaluation_YYYYMM.pdf
    r'releve_pea_(\\d{4})(\\d{2})',  # releve_pea_YYYYMM.pdf
    r'releve_(\\d{4})(\\d{2})',  # releve_YYYYMM.pdf
    r'(?:evaluation|portefeuille)_(\\w+)_(\\d{4})',  # evaluation_mois_YYYY.pdf
    r'positions_(\\w+)_(\\d{4})',  # positions_mois_YYYY.pdf
    r'(\\d{4})[_-](\\d{2})[_-]',  # YYYY-MM-
    r'(\\d{4})[_-](\\w+)[_-]',  # YYYY-mois-
    r'pea_(\\d{4})_(\\w+)',  # pea_YYYY_mois
    r'(\\w+)(\\d{4})',  # moisYYYY
    r'(\\w+)[_-]?(\\d{2})'  # moisMM
]

# Mapping des mois pour l'extraction de date
MONTH_MAPPING = {
    'janvier': 1, 'jan': 1,
    'février': 2, 'fevrier': 2, 'fev': 2,
    'mars': 3, 'mar': 3,
    'avril': 4, 'avr': 4,
    'mai': 5,
    'juin': 6, 'jun': 6,
    'juillet': 7, 'juil': 7,
    'août': 8, 'aout': 8,
    'septembre': 9, 'sept': 9, 'sep': 9,
    'octobre': 10, 'oct': 10,
    'novembre': 11, 'nov': 11,
    'décembre': 12, 'decembre': 12, 'dec': 12
}
