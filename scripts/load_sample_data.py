"""
Script pour charger vos données réelles
"""
import sys
from backend.data.data_loader import DataLoader

def load_user_data_auto(user_id: str = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e", data_folder: str = "data/raw"):
    """ Script automatique pour charger toutes vos données """
    
    print("🚀 CHARGEMENT AUTOMATIQUE DONNÉES PATRIMOINE")   
    print("=" * 50)
    
    # Créer le loader
    loader = DataLoader()
    
    # Validation des fichiers
    validation_report = loader.validate_all_files(data_folder)
    
    if validation_report['valid_count'] == 0:
        print("❌ Aucun fichier valide trouvé")
        return False
    
    # ✅ CORRECTION : Utiliser la méthode corrigée
    print(f"\n📥 Début chargement pour utilisateur: {user_id}")
    success = loader.load_all_user_files(user_id, data_folder)
    
    if success:
        print("\n🎉 CHARGEMENT TERMINÉ AVEC SUCCÈS!")
        
        # Résumé final
        summary = loader.get_platform_summary(user_id)
        if summary:
            print("\n📊 RÉSUMÉ FINAL:")
            total_capital = sum(data['capital_total'] for data in summary.values())
            total_positions = sum(data['nb_investissements'] for data in summary.values())
            
            print(f"  💰 Capital total: {total_capital:,.0f} €")
            print(f"  📈 Positions totales: {total_positions}")
            print(f"  🏢 Plateformes: {len(summary)}")
    else:
        print("\n❌ ÉCHEC DU CHARGEMENT")
    
    return success

if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else "29dec51d-0772-4e3a-8e8f-1fece8fefe0e"
    load_user_data_auto(user_id)