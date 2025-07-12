
"""
Script pour charger vos données réelles
"""
import os
import sys
import logging
from typing import Optional, List

# Configuration du logging
logging.basicConfig(level=logging.DEBUG, format='%(asctime)s - %(levelname)s - %(message)s')
logging.getLogger().setLevel(logging.DEBUG)

# Ajouter de la racine du project au chemin Python
project_root = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
if project_root not in sys.path:
    sys.path.insert(0, project_root)

from backend.data.data_loader import DataLoader





def load_user_data_auto(user_id: str = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e", data_folder: str = "data/raw", platforms: Optional[List[str]] = None):
    """ Script automatique pour charger vos données, avec filtre optionnel par plateforme """
    
    logging.info("🚀 CHARGEMENT AUTOMATIQUE DONNÉES PATRIMOINE")   
    logging.info("=" * 50)
    
    # Créer le loader
    loader = DataLoader()
    
    # Validation des fichiers
    validation_report = loader.validate_all_files(data_folder, platforms_to_load=platforms)
    
    if validation_report['valid_count'] == 0:
        logging.error("❌ Aucun fichier valide trouvé")
        return False
    
    logging.info(f"📥 Début chargement pour utilisateur: {user_id}")
    success = loader.load_all_user_files(user_id, data_folder, platforms_to_load=platforms)
    
    if success:
        logging.info("🎉 CHARGEMENT TERMINÉ AVEC SUCCÈS!")
        
        # Résumé final
        summary = loader.get_platform_summary(user_id)
        if summary:
            logging.info("📊 RÉSUMÉ FINAL:")
            total_capital = sum(data['capital_total'] for data in summary.values())
            total_positions = sum(data['nb_investissements'] for data in summary.values())
            
            logging.info(f"  💰 Capital total: {total_capital:,.0f} €")
            logging.info(f"  📈 Positions totales: {total_positions}")
            logging.info(f"  🏢 Plateformes: {len(summary)}")

        # Afficher les détails des investissements LPB si LPB a été chargé
        if platforms and 'lpb' in platforms:
            loader.display_lpb_investment_details(user_id)

    else:
        logging.error("❌ ÉCHEC DU CHARGEMENT")
    
    return success





def clean_and_reload_data(user_id: str = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e", platforms: Optional[List[str]] = None):
    """Nettoyer et recharger les données, avec filtre optionnel par plateforme."""
    logging.info(f"Nettoyage et rechargement pour l'utilisateur : {user_id}")
    
    try:
        # Nettoyer les données existantes
        from backend.models.database import ExpertDatabaseManager
        db = ExpertDatabaseManager()
        
        logging.info("🗑️ Suppression des données existantes...")
        # Si des plateformes sont spécifiées, on ne supprime que celles-là.
        if platforms:
            for platform in platforms:
                db.clear_platform_data(user_id, platform)
        else:
            # Sinon, on supprime tout pour l'utilisateur.
            db.clear_user_data(user_id)
        
        # Recharger
        logging.info(f"Rechargement des données...")
        success = load_user_data_auto(user_id, platforms=platforms)
        
        if success:
            logging.info("🎉 Rechargement terminé avec succès !")
        else:
            logging.error("❌ Échec du rechargement")
        
        return success
        
    except Exception as e:
        logging.error(f"❌ Erreur lors du nettoyage/rechargement : {e}", exc_info=True)
        return False

def check_database_status(user_id: str = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e"):
    """Vérifier le statut des données en base"""
    logging.info(f"🔍 Vérification du statut de la base de données pour : {user_id}")
    
    try:
        from backend.models.database import ExpertDatabaseManager
        db = ExpertDatabaseManager()
        
        # Test connexion
        if not db.test_connection():
            logging.error("❌ Échec de la connexion à la base de données")
            return False
        
        logging.info("✅ Connexion à la base de données OK")
        
        # Récupérer données utilisateur
        investments_df = db.get_user_investments(user_id)
        cash_flows_df = db.get_user_cash_flows(user_id)
        portfolio_positions_df = db.get_portfolio_positions(user_id)
        
        logging.info(f"\n📊 Données de l'utilisateur {user_id} :")
        logging.info(f"  💼 Investissements : {len(investments_df)}")
        logging.info(f"  💰 Flux de trésorerie : {len(cash_flows_df)}")
        logging.info(f"  📊 Positions de portefeuille : {len(portfolio_positions_df)}")
        
        # Répartition par plateforme
        if not investments_df.empty:
            logging.info(f"\n🏢 Répartition des investissements par plateforme :")
            platform_summary = investments_df.groupby('platform')['invested_amount'].agg(['count', 'sum'])
            for platform, data in platform_summary.iterrows():
                count, amount = data['count'], data['sum']
                logging.info(f"  {platform} : {count} positions, {amount:,.2f}€")
        
        if not cash_flows_df.empty and 'platform' in cash_flows_df.columns:
            logging.info(f"\n💸 Répartition des flux par plateforme :")
            flow_summary = cash_flows_df.groupby('platform')['gross_amount'].agg(['count', 'sum'])
            for platform, data in flow_summary.iterrows():
                count, amount = data['count'], data['sum']
                logging.info(f"  {platform} : {count} flux, {amount:,.2f}€")
        
        if not portfolio_positions_df.empty:
            logging.info(f"\n📈 Valorisation du portefeuille :")
            total_value = portfolio_positions_df['market_value'].sum()
            logging.info(f"  Total : {total_value:,.2f}€")
            
            platform_positions = portfolio_positions_df.groupby('platform')['market_value'].agg(['count', 'sum'])
            for platform, data in platform_positions.iterrows():
                count, amount = data['count'], data['sum']
                logging.info(f"  {platform} : {count} positions, {amount:,.2f}€")
        
        return True
        
    except Exception as e:
        logging.error(f"❌ Erreur lors de la vérification de la base : {e}", exc_info=True)
        return False

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="Charger les données patrimoniales.")
    parser.add_argument("command", nargs='?', default="load", help="La commande à exécuter (load, clean, check). Défaut: load")
    parser.add_argument("--user_id", default="29dec51d-0772-4e3a-8e8f-1fece8fefe0e", help="L'ID de l'utilisateur.")
    parser.add_argument("--platforms", nargs='+', help="Liste des plateformes à charger (ex: lpb pretup).")

    args = parser.parse_args()

    if args.command == "load":
        load_user_data_auto(args.user_id, platforms=args.platforms)
    elif args.command == "clean":
        clean_and_reload_data(args.user_id, platforms=args.platforms)
    elif args.command == "check":
        check_database_status(args.user_id)
    else:
        logging.error(f"❌ Commande inconnue : {args.command}")
        logging.info("Commandes disponibles : load, clean, check")
