"""
Script pour vider la base de données de façon sécurisée
Usage: python clear_database.py
"""

import sys
import os
sys.path.append(os.path.dirname(__file__))

from backend.models.database import DatabaseManager

def main():
    print("🗑️ SCRIPT DE NETTOYAGE BASE DE DONNÉES")
    print("=" * 50)
    
    try:
        db = DatabaseManager()
        
        # Test de connexion
        if not db.test_connection():
            print("❌ Impossible de se connecter à la base de données")
            return
        
        # Menu interactif
        while True:
            print("\n📋 MENU OPTIONS:")
            print("1. 📊 Voir les statistiques de la BDD")
            print("2. 🗑️ Supprimer TOUTES les données")
            print("3. 👤 Supprimer un utilisateur spécifique")
            print("4. 📄 Vider une table spécifique")
            print("5. 🚪 Quitter")
            
            choice = input("\n🔢 Votre choix (1-5): ").strip()
            
            if choice == "1":
                # Statistiques
                stats = db.get_database_stats()
                
            elif choice == "2":
                # Suppression totale
                stats = db.get_database_stats()
                total = stats.get('total_records', 0)
                
                if total == 0:
                    print("✅ La base de données est déjà vide !")
                    continue
                
                print(f"\n⚠️ ATTENTION : {total} enregistrements vont être supprimés !")
                confirm = input("❓ Tapez 'SUPPRIMER' pour confirmer: ")
                
                if confirm == 'SUPPRIMER':
                    print("\n🚀 Suppression en cours...")
                    success = db.clear_all_data(confirm=True)
                    
                    if success:
                        print("🎉 Suppression terminée !")
                    else:
                        print("❌ Échec de la suppression")
                else:
                    print("🛑 Suppression annulée")
            
            elif choice == "3":
                # Supprimer un utilisateur
                user_id = input("👤 ID utilisateur à supprimer: ").strip()
                if user_id:
                    confirm = input(f"❓ Supprimer l'utilisateur {user_id} ? (oui/non): ")
                    if confirm.lower() == 'oui':
                        success = db.clear_user_data(user_id)
                        if success:
                            print(f"✅ Utilisateur {user_id} supprimé")
                        else:
                            print(f"❌ Échec suppression {user_id}")
            
            elif choice == "4":
                # Vider une table
                table = input("📄 Nom de la table à vider: ").strip()
                if table:
                    confirm = input(f"❓ Vider la table '{table}' ? (oui/non): ")
                    if confirm.lower() == 'oui':
                        success = db.truncate_table(table, confirm=True)
                        if success:
                            print(f"✅ Table {table} vidée")
                        else:
                            print(f"❌ Échec vidage {table}")
            
            elif choice == "5":
                print("👋 Au revoir !")
                break
            
            else:
                print("❌ Choix invalide")
    
    except KeyboardInterrupt:
        print("\n🛑 Interruption utilisateur")
    except Exception as e:
        print(f"❌ Erreur: {e}")

if __name__ == "__main__":
    main()