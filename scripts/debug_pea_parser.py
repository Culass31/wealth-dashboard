import pdfplumber
import json
import os
import logging

# Configure logging to output to console and file
# Le fichier de log sera créé à la racine du projet
script_dir = os.path.dirname(os.path.abspath(__file__))
project_root = os.path.abspath(os.path.join(script_dir, '..'))
log_file_path = os.path.join(project_root, 'pea_debug_log.txt')

logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
file_handler = logging.FileHandler(log_file_path)
file_handler.setLevel(logging.DEBUG)
file_handler.setFormatter(logging.Formatter('%(asctime)s - %(levelname)s - %(message)s'))
logging.getLogger().addHandler(file_handler)

logging.info("Démarrage du script de débogage PDF...")

# Définir le chemin vers le fichier PDF
# Le PDF est supposé être dans data/raw/pea/ par rapport à la racine du projet
pdf_path = os.path.join(project_root, 'data', 'raw', 'pea', 'positions_septembre_2024.pdf')
output_file_path = os.path.join(project_root, 'pea_debug_output.txt')

logging.info(f"Chemin du PDF : {pdf_path}")
logging.info(f"Le résultat sera écrit dans : {output_file_path}")

output = {}
if not os.path.exists(pdf_path):
    output['error'] = f"Fichier PDF non trouvé à : {pdf_path}"
    logging.error(output['error'])
else:
    try:
        with pdfplumber.open(pdf_path) as pdf:
            output['num_pages'] = len(pdf.pages)
            output['pages'] = []
            logging.info(f"Trouvé {output['num_pages']} page(s) dans le PDF.")
            for page_num, page in enumerate(pdf.pages):
                logging.debug(f"Traitement de la page {page_num + 1}...")
                page_data = {
                    'page_number': page_num + 1,
                    'text': page.extract_text(),
                    'tables': page.extract_tables()
                }
                output['pages'].append(page_data)
                logging.debug(f"Page {page_num + 1} extraite. Longueur du texte : {len(page_data['text'] or '')}, Tables trouvées : {len(page_data['tables'])}")
    except Exception as e:
        output['error'] = f"Erreur lors du traitement du PDF : {str(e)}"
        logging.exception(output['error'])

try:
    with open(output_file_path, 'w', encoding='utf-8') as f:
        json.dump(output, f, indent=2, ensure_ascii=False)
    logging.info(f"Écriture du résultat dans {output_file_path} réussie.")
except Exception as e:
    logging.error(f"Échec de l'écriture du résultat dans le fichier : {e}")

logging.info("Script de débogage PDF terminé.")
