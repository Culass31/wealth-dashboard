"""
Script pour vider la base de données de façon sécurisée
Usage: python clear_database.py
"""

import sys
import os
import logging

# Configuration du logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')

# Ajouter de la racine du project au chemin Python
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.models.database import DatabaseManager

def main():
    logging.info("🗑️ SCRIPT DE NETTOYAGE BASE DE DONNÉES")
    logging.info("=" * 50)
    
    try:
        db = DatabaseManager()
        
        # Test de connexion
        if not db.test_connection():
            logging.error("❌ Impossible de se connecter à la base de données")
            return
        
        # Menu interactif
        while True:
            logging.info("\n📋 MENU OPTIONS:")
            logging.info("1. 📊 Voir les statistiques de la BDD")
            logging.info("2. 🗑️ Supprimer TOUTES les données")
            logging.info("3. 👤 Supprimer un utilisateur spécifique")
            logging.info("4. 📄 Vider une table spécifique")
            logging.info("5.  plateforme")
            logging.info("6. 🚪 Quitter")
            
            choice = input("\n🔢 Votre choix (1-6): ").strip()
            
            if choice == "1":
                # Statistiques
                stats = db.get_database_stats()
                
            elif choice == "2":
                # Suppression totale
                stats = db.get_database_stats()
                total = stats.get('total_records', 0)
                
                if total == 0:
                    logging.info("✅ La base de données est déjà vide !")
                    continue
                
                logging.warning(f"\n⚠️ ATTENTION : {total} enregistrements vont être supprimés !")
                confirm = input("❓ Tapez 'SUPPRIMER' pour confirmer: ")
                
                if confirm == 'SUPPRIMER':
                    logging.info("\n🚀 Suppression en cours...")
                    success = db.clear_all_data(confirm=True)
                    
                    if success:
                        logging.info("🎉 Suppression terminée !")
                    else:
                        logging.error("❌ Échec de la suppression")
                else:
                    logging.info("🛑 Suppression annulée")
            
            elif choice == "3":
                # Supprimer un utilisateur
                user_id = input("👤 ID utilisateur à supprimer: ").strip()
                if user_id:
                    confirm = input(f"❓ Supprimer l'utilisateur {user_id} ? (oui/non): ")
                    if confirm.lower() == 'oui':
                        success = db.clear_user_data(user_id)
                        if success:
                            logging.info(f"✅ Utilisateur {user_id} supprimé")
                        else:
                            logging.error(f"❌ Échec suppression {user_id}")
            
            elif choice == "4":
                # Vider une table
                table = input("📄 Nom de la table à vider: ").strip()
                if table:
                    confirm = input(f"❓ Vider la table '{table}' ? (oui/non): ")
                    if confirm.lower() == 'oui':
                        success = db.truncate_table(table, confirm=True)
                        if success:
                            logging.info(f"✅ Table {table} vidée")
                        else:
                            logging.error(f"❌ Échec vidage {table}")
            
            elif choice == "5":
                # Supprimer par plateforme
                user_id = input("👤 ID utilisateur pour lequel supprimer la plateforme: ").strip()
                platform_name = input("📛 Nom de la plateforme à supprimer: ").strip()
                if user_id and platform_name:
                    confirm = input(f"❓ Supprimer la plateforme '{platform_name}' pour l'utilisateur {user_id} ? (oui/non): ")
                    if confirm.lower() == 'oui':
                        success = db.clear_platform_data(user_id, platform_name)
                        if success:
                            logging.info(f"✅ Données de la plateforme '{platform_name}' supprimées")
                        else:
                            logging.error(f"❌ Échec de la suppression pour la plateforme '{platform_name}'")
            
            elif choice == "6":
                logging.info("👋 Au revoir !")
                break
            
            else:
                logging.warning("❌ Choix invalide")
    
    except KeyboardInterrupt:
        logging.info("\n🛑 Interruption utilisateur")
    except Exception as e:
        logging.error(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()
