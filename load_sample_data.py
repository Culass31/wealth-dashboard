"""
Script pour charger vos données réelles
"""
import os
import sys
from backend.data.data_loader import DataLoader
from backend.models.database import DatabaseManager

def load_user_data(user_id: str = "luc-nazarian"):
    """Load data for a specific user"""
    print(f"📥 Loading data for user: {user_id}")
    
    loader = DataLoader()
    
    # Files to load (adjust paths as needed)
    files_to_load = [
        ('data/raw/Portefeuille LPB 20250529.xlsx', 'lbp'),
        ('data/raw/Portefeuille PretUp 20250529.xlsx', 'pretup'),
        ('data/raw/Portefeuille BienPreter 20250529.xlsx', 'bienpreter'),
        ('data/raw/Portefeuille Homunity 20250529.xlsx', 'homunity'),
    ]
    
    success_count = 0
    
    for file_path, platform in files_to_load:
        if os.path.exists(file_path):
            print(f"\n📊 Loading {platform.upper()} data...")
            success = loader.load_platform_data(file_path, platform, user_id)
            if success:
                print(f"✅ {platform.upper()} data loaded successfully")
                success_count += 1
            else:
                print(f"❌ Failed to load {platform.upper()} data")
        else:
            print(f"⚠️  File not found: {file_path}")
    
    print(f"\n📋 Summary: {success_count}/{len(files_to_load)} platforms loaded")
    
    if success_count > 0:
        # Show summary
        db = DatabaseManager()
        investments_df = db.get_user_investments(user_id)
        cash_flows_df = db.get_user_cash_flows(user_id)
        
        print(f"\n📈 Data Summary:")
        print(f"  - Investments: {len(investments_df)}")
        print(f"  - Cash flows: {len(cash_flows_df)}")
        print(f"  - Total invested: €{investments_df['invested_amount'].sum():,.0f}")
        print(f"  - Platforms: {', '.join(investments_df['platform'].unique())}")
    
    return success_count > 0

if __name__ == "__main__":
    user_id = sys.argv[1] if len(sys.argv) > 1 else "29dec51d-0772-4e3a-8e8f-1fece8fefe0e"
    load_user_data(user_id)