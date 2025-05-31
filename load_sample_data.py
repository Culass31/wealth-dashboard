"""
Script pour charger vos données réelles
"""
import os
import sys
from backend.models.database import ExpertDatabaseManager

def load_user_data(user_id: str = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e"):
    """Load data for a specific user"""
    print(f"📥 Loading data for user: {user_id}")
    
    from backend.data.data_loader import DataLoader
    
    loader = DataLoader()
    
    # Charger les plateformes crowdfunding
    files_to_load = [
        ('Portefeuille LPB.xlsx', 'lpb'),
        ('Portefeuille PretUp.xlsx', 'pretup'),
        ('Portefeuille BienPreter.xlsx', 'bienpreter'),
        ('Portefeuille Homunity.xlsx', 'homunity'),
        ('Portefeuille Linxea.xlsx', 'assurance_vie'),
    ]
    
    success_count = 0
    
    # Charger crowdfunding + AV
    for file_path, platform in files_to_load:
        if os.path.exists(file_path):
            print(f"\n📊 Loading {platform.upper()}...")
            
            if platform == 'assurance_vie':
                success = loader.load_assurance_vie_data(file_path, user_id)
            else:
                success = loader.load_platform_data(file_path, platform, user_id)
            
            if success:
                print(f"✅ {platform.upper()} chargé")
                success_count += 1
            else:
                print(f"❌ Échec {platform.upper()}")
        else:
            print(f"⚠️  Fichier non trouvé: {file_path}")
    
    # Charger PEA avec la nouvelle méthode
    print(f"\n🏦 Chargement PEA...")
    pea_success = load_pea_data(user_id)
    if pea_success:
        success_count += 1
    
    # Résumé final
    print(f"\n📋 RÉSUMÉ CHARGEMENT:")
    print(f"  ✅ Plateformes chargées: {success_count}")
    
    if success_count > 0:
        # Afficher résumé
        from backend.models.database import DatabaseManager
        db = DatabaseManager()
        
        investments_df = db.get_user_investments(user_id)
        cash_flows_df = db.get_user_cash_flows(user_id)
        portfolio_positions_df = db.get_portfolio_positions(user_id)
        
        print(f"\n📈 Données chargées:")
        print(f"  💼 Investissements: {len(investments_df)}")
        print(f"  💰 Flux de trésorerie: {len(cash_flows_df)}")
        print(f"  📊 Positions portfolio: {len(portfolio_positions_df)}")
        
        if not investments_df.empty:
            total_invested = investments_df['invested_amount'].sum()
            print(f"  💵 Total investi: {total_invested:,.0f}€")
        
        if not portfolio_positions_df.empty:
            total_portfolio_value = portfolio_positions_df['market_value'].sum()
            print(f"  💎 Valorisation portfolio: {total_portfolio_value:,.0f}€")
    
    return success_count > 0

def load_pea_data(user_id: str = "29dec51d-0772-4e3a-8e8f-1fece8fefe0e"):
    """
    Charger PEA avec portfolio_positions pour l'évaluation
    """
    print(f"🏦 Chargement PEA corrigé pour utilisateur: {user_id}")
    
    from backend.data.unified_parser import UnifiedPortfolioParser
    from backend.models.database import DatabaseManager
    
    # Chercher fichiers PEA
    releve_pea = None
    evaluation_pea = None
    
    # Chercher dans le répertoire
    import os
    for file in os.listdir('.'):
        if 'pea' in file.lower() and file.lower().endswith('.pdf'):
            if any(keyword in file.lower() for keyword in ['releve', 'compte', 'transaction']):
                releve_pea = file
            elif any(keyword in file.lower() for keyword in ['evaluation', 'portefeuille', 'position']):
                evaluation_pea = file
    
    if not releve_pea and not evaluation_pea:
        print("⚠️  Aucun fichier PEA trouvé")
        return False
    
    print(f"📂 Fichiers trouvés:")
    print(f"  📄 Relevé: {releve_pea or 'Non trouvé'}")
    print(f"  📊 Évaluation: {evaluation_pea or 'Non trouvé'}")
    
    try:
        # Parser PEA
        parser = UnifiedPortfolioParser(user_id)
        investments, cash_flows = parser._parse_pea(releve_pea, evaluation_pea)
        
        # Récupérer les positions de portefeuille
        portfolio_positions = parser.get_pea_portfolio_positions()
        
        # Connexion BDD
        db = DatabaseManager()
        
        # Insérer données
        success_cf = True
        success_pp = True
        
        if cash_flows:
            success_cf = db.insert_cash_flows(cash_flows)
            print(f"📊 Cash flows: {len(cash_flows)} transactions")
        
        if portfolio_positions:
            success_pp = db.insert_portfolio_positions(portfolio_positions)
            print(f"📊 Portfolio positions: {len(portfolio_positions)} positions")
        
        if success_cf and success_pp:
            print("✅ PEA chargé avec succès!")
            
            # Résumé
            if portfolio_positions:
                total_value = sum(pos.get('market_value', 0) for pos in portfolio_positions)
                print(f"💰 Valorisation totale PEA: {total_value:,.0f}€")
            
            return True
        else:
            print("❌ Échec chargement PEA")
            return False
            
    except Exception as e:
        print(f"❌ Erreur chargement PEA: {e}")
        import traceback
        traceback.print_exc()
        return False

if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else "29dec51d-0772-4e3a-8e8f-1fece8fefe0e"
    load_user_data(user_id)