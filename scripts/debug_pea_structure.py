#!/usr/bin/env python3
"""
Script pour analyser la structure du fichier PEA et comprendre le problème
"""

import pdfplumber
import pandas as pd
import sys
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Add project root to Python path
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

def analyze_pea_file(file_path: str):
    """Analyser la structure du fichier PEA"""
    
    logging.info("🔍 ANALYSE STRUCTURE FICHIER PEA")
    logging.info("=" * 45)
    logging.info(f"📂 Fichier: {file_path}")
    
    if not os.path.exists(file_path):
        logging.error(f"❌ Fichier non trouvé: {file_path}")
        return
    
    # Déterminer le type de fichier
    if file_path.lower().endswith('.pdf'):
        analyze_pdf_structure(file_path)
    elif file_path.lower().endswith(('.xlsx', '.xls')):
        analyze_excel_structure(file_path)
    else:
        logging.error("❌ Format de fichier non supporté (attendu: PDF ou Excel)")

def analyze_pdf_structure(pdf_path: str):
    """Analyser structure PDF"""
    
    logging.info("📄 ANALYSE PDF...")
    
    try:
        with pdfplumber.open(pdf_path) as pdf:
            logging.info(f"📊 Nombre de pages: {len(pdf.pages)}")
            
            for page_num, page in enumerate(pdf.pages):
                logging.info(f"\n📖 PAGE {page_num + 1}:")
                
                # Extraire tableaux
                tables = page.extract_tables()
                logging.info(f"  📋 Tableaux trouvés: {len(tables)}")
                
                for table_idx, table in enumerate(tables):
                    if table:
                        logging.info(f"  📊 Tableau {table_idx + 1}: {len(table)} lignes, {len(table[0]) if table[0] else 0} colonnes")
                        
                        # Afficher l'en-tête
                        if table[0]:
                            logging.info(f"    En-tête: {table[0]}")
                        
                        # Afficher les 3 premières lignes de données
                        logging.info("    Échantillon données:")
                        for row_idx, row in enumerate(table[1:4]):  # 3 premières lignes
                            if row:
                                logging.info(f"      Ligne {row_idx + 1}: {row}")
                        
                        # Analyser la colonne des cours (colonne 2 selon votre extrait)
                        if len(table) > 1 and len(table[0]) >= 3:
                            cours_column = []
                            for row in table[1:6]:  # 5 premières lignes
                                if row and len(row) > 2:
                                    cours_column.append(row[2])
                            
                            logging.info(f"    Colonne 'Cours' (échantillon): {cours_column}")
                            
                            # Tester clean_amount sur chaque valeur
                            logging.info(f"    Test clean_amount:")
                            for i, cours in enumerate(cours_column):
                                try:
                                    from backend.utils.file_helpers import clean_amount
                                    cleaned = clean_amount(cours)
                                    logging.info(f"      '{cours}' → {cleaned}")
                                except Exception as e:
                                    logging.error(f"      '{cours}' → ERREUR: {e}")
                
                # Si pas de tableaux, essayer extraction texte
                if not tables:
                    text = page.extract_text()
                    if text:
                        lines = text.split('\n')[:10]  # 10 premières lignes
                        logging.info(f"  📝 Texte (échantillon):")
                        for line in lines:
                            if line.strip():
                                logging.info(f"    {line}")
    
    except Exception as e:
        logging.error(f"❌ Erreur analyse PDF: {e}")

def analyze_excel_structure(excel_path: str):
    """Analyser structure Excel"""
    
    logging.info("📊 ANALYSE EXCEL...")
    
    try:
        # Lire tous les onglets
        xl_file = pd.ExcelFile(excel_path)
        logging.info(f"📋 Onglets: {xl_file.sheet_names}")
        
        for sheet_name in xl_file.sheet_names:
            logging.info(f"\n📄 ONGLET: {sheet_name}")
            
            try:
                df = pd.read_excel(excel_path, sheet_name=sheet_name, nrows=10)
                logging.info(f"  📊 Dimensions: {df.shape}")
                logging.info(f"  📋 Colonnes: {list(df.columns)}")
                
                # Afficher échantillon
                logging.info("  📄 Échantillon:")
                for idx, row in df.head(5).iterrows():
                    logging.info(f"    Ligne {idx}: {list(row)}")
                
                # Si c'est un onglet avec des ISIN, analyser la structure
                if any('FR' in str(col) for col in df.columns) or any('FR' in str(cell) for cell in df.iloc[0] if pd.notna(cell)):
                    logging.info("  ✅ Onglet avec positions détecté")
                    
                    # Chercher la colonne cours
                    for col_idx, col in enumerate(df.columns):
                        if 'cours' in str(col).lower():
                            logging.info(f"    💰 Colonne cours trouvée: {col} (index {col_idx})")
                            sample_values = df[col].head(5).tolist()
                            logging.info(f"       Valeurs: {sample_values}")
            
            except Exception as e:
                logging.error(f"  ❌ Erreur lecture onglet {sheet_name}: {e}")
    
    except Exception as e:
        logging.error(f"❌ Erreur analyse Excel: {e}")

def test_problematic_string():
    """Tester la string problématique avec clean_amount améliorée"""
    
    logging.info("\n🧪 TEST STRING PROBLÉMATIQUE")
    logging.info("=" * 35)
    
    # La string problématique de l'erreur
    problematic_string = """144,00000
175,14000
59,66000
342,85000
101,92000
91,26000
29,94000
571,70000
86,85000
210,75000
91,70000
116,30000"""
    
    logging.info(f"String problématique (début): {problematic_string[:100]}...")
    
    # Essayer de diviser et nettoyer
    values = problematic_string.strip().split('\n')
    logging.info(f"Après split par lignes: {len(values)} valeurs")
    
    cleaned_values = []
    for i, value in enumerate(values[:5]):  # Tester 5 premières
        try:
            from backend.utils.file_helpers import clean_amount
            cleaned = clean_amount(value.strip())
            cleaned_values.append(cleaned)
            logging.info(f"  '{value.strip()}' → {cleaned}")
        except Exception as e:
            logging.error(f"  '{value.strip()}' → ERREUR: {e}")
    
    logging.info(f"Valeurs nettoyées: {cleaned_values}")

def main():
    """Script principal"""
    
    # Rechercher fichiers PEA
    pea_files = []
    pea_dir = os.path.join(project_root, 'data', 'raw', 'pea')
    
    if os.path.isdir(pea_dir):
        for file in os.listdir(pea_dir):
            if 'pea' in file.lower() and (file.endswith('.pdf') or file.endswith('.xlsx')):
                pea_files.append(os.path.join(pea_dir, file))
    
    if pea_files:
        logging.info(f"📂 Fichiers PEA trouvés: {pea_files}")
        
        for file in pea_files:
            analyze_pea_file(file)
    else:
        logging.error("❌ Aucun fichier PEA trouvé")
        logging.info("💡 Placez vos fichiers PEA (PDF ou Excel) dans le répertoire courant")
    
    # Tester la string problématique
    test_problematic_string()
    
    logging.info(f"\n🎯 DIAGNOSTIC:")
    logging.info(f"1. Le parser extrait toute la colonne au lieu de ligne par ligne")
    logging.info(f"2. clean_amount reçoit une string multi-lignes")
    logging.info(f"3. Solution: corriger l'extraction pour traiter ligne par ligne")

if __name__ == "__main__":
    main()
