import pdfplumber
import sys
import os
import logging

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

def analyze_pdf_structure(pdf_path: str):
    """
    Analyse la structure d'un fichier PDF en extrayant le texte et les tables.
    """
    if not os.path.exists(pdf_path):
        logging.error(f"Erreur : Le fichier PDF '{pdf_path}' n'existe pas.")
        return
    
    if not pdf_path.lower().endswith('.pdf'):
        logging.error(f"Erreur : Le fichier '{pdf_path}' n'est pas un fichier PDF.")
        return

    logging.info(f"Analyse du fichier PDF : {pdf_path}")

    try:
        with pdfplumber.open(pdf_path) as pdf:
            logging.info(f"Nombre de pages : {len(pdf.pages)}")
            
            for i, page in enumerate(pdf.pages):
                logging.info(f"\n--- Page {i + 1} ---")
                
                # Extraire le texte
                text = page.extract_text()
                if text:
                    logging.info("\nTexte extrait :")
                    logging.info(text)
                else:
                    logging.info("\nAucun texte trouvé sur cette page.")
                
                # Extraire les tables
                tables = page.extract_tables()
                if tables:
                    logging.info("\nTables extraites :")
                    for j, table in enumerate(tables):
                        logging.info(f"  Table {j + 1} :")
                        for row in table:
                            logging.info(f"    {row}")
                else:
                    logging.info("\nAucune table trouvée sur cette page.")
                    
    except Exception as e:
        logging.error(f"Une erreur est survenue lors de l'analyse du PDF : {e}")

if __name__ == "__main__":
    if len(sys.argv) < 2:
        logging.info("Utilisation : python analyze_pea_pdf.py <chemin_vers_le_fichier_pdf>")
        sys.exit(1)
    
    pdf_file_path = sys.argv[1]
    analyze_pdf_structure(pdf_file_path)
