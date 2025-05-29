"""
Script de réparation rapide pour corriger les problèmes courants
"""
import os
import sys
from pathlib import Path

def create_database_file():
    """Créer le fichier database.py correct"""
    print("🔧 Creating backend/models/database.py...")
    
    # Ensure directory exists
    os.makedirs('backend/models', exist_ok=True)
    
    database_content = '''# backend/models/database.py
from supabase import create_client, Client
import pandas as pd
from typing import List, Dict, Any, Optional
import uuid
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

class DatabaseManager:
    """Gestionnaire de base de données Supabase"""
    
    def __init__(self):
        # Get credentials from environment
        self.supabase_url = os.getenv("SUPABASE_URL")
        self.supabase_key = os.getenv("SUPABASE_KEY")
        
        if not self.supabase_url or not self.supabase_key:
            raise ValueError("SUPABASE_URL and SUPABASE_KEY must be set in .env file")
        
        try:
            self.supabase: Client = create_client(
                self.supabase_url, 
                self.supabase_key
            )
            print("✅ Connected to Supabase successfully")
        except Exception as e:
            raise ConnectionError(f"Failed to connect to Supabase: {e}")
    
    def test_connection(self) -> bool:
        """Test the database connection"""
        try:
            result = self.supabase.table('investments').select("count").limit(1).execute()
            return True
        except Exception as e:
            print(f"Connection test failed: {e}")
            return False
    
    def insert_investments(self, investments: List[Dict[str, Any]]) -> bool:
        """Insert multiple investments"""
        if not investments:
            return True
        try:
            result = self.supabase.table('investments').insert(investments).execute()
            print(f"✅ Inserted {len(investments)} investments")
            return True
        except Exception as e:
            print(f"❌ Error inserting investments: {e}")
            return False
    
    def insert_cash_flows(self, cash_flows: List[Dict[str, Any]]) -> bool:
        """Insert multiple cash flows"""
        if not cash_flows:
            return True
        try:
            result = self.supabase.table('cash_flows').insert(cash_flows).execute()
            print(f"✅ Inserted {len(cash_flows)} cash flows")
            return True
        except Exception as e:
            print(f"❌ Error inserting cash flows: {e}")
            return False
    
    def get_user_investments(self, user_id: str, platform: Optional[str] = None) -> pd.DataFrame:
        """Get user investments as DataFrame"""
        try:
            query = self.supabase.table('investments').select("*").eq('user_id', user_id)
            if platform:
                query = query.eq('platform', platform)
            result = query.execute()
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            print(f"❌ Error fetching investments: {e}")
            return pd.DataFrame()
    
    def get_user_cash_flows(self, user_id: str, start_date: Optional[str] = None) -> pd.DataFrame:
        """Get user cash flows as DataFrame"""
        try:
            query = self.supabase.table('cash_flows').select("*").eq('user_id', user_id)
            if start_date:
                query = query.gte('transaction_date', start_date)
            result = query.execute()
            return pd.DataFrame(result.data) if result.data else pd.DataFrame()
        except Exception as e:
            print(f"❌ Error fetching cash flows: {e}")
            return pd.DataFrame()
'''
    
    with open('backend/models/database.py', 'w', encoding='utf-8') as f:
        f.write(database_content)
    
    print("✅ backend/models/database.py created")

def create_init_files():
    """Créer les fichiers __init__.py"""
    print("🔧 Creating __init__.py files...")
    
    init_files = [
        'backend/__init__.py',
        'backend/models/__init__.py',
        'backend/data/__init__.py', 
        'backend/utils/__init__.py'
    ]
    
    for init_file in init_files:
        os.makedirs(os.path.dirname(init_file), exist_ok=True)
        Path(init_file).touch()
        print(f"✅ Created: {init_file}")

def create_env_template():
    """Créer un template .env si nécessaire"""
    if os.path.exists('.env'):
        print("✅ .env file already exists")
        return
    
    print("🔧 Creating .env template...")
    
    env_content = """# Supabase Configuration
SUPABASE_URL=https://your-project.supabase.co
SUPABASE_KEY=your_anon_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here

# Instructions:
# 1. Go to https://supabase.com
# 2. Create a new project
# 3. Go to Settings > API
# 4. Copy the URL and anon key above
# 5. Remove this comment block
"""
    
    with open('.env', 'w') as f:
        f.write(env_content)
    
    print("✅ .env template created")
    print("⚠️  Please update .env with your real Supabase credentials!")

def create_minimal_test():
    """Créer un test minimal pour vérifier que tout fonctionne"""
    print("🔧 Creating minimal test...")
    
    test_content = '''# test_minimal.py
import sys
import os

# Add current directory to path
sys.path.insert(0, os.getcwd())

def test_import():
    """Test minimal des imports"""
    try:
        print("Testing DatabaseManager import...")
        from backend.models.database import DatabaseManager
        print("✅ DatabaseManager import successful!")
        return True
    except Exception as e:
        print(f"❌ Import failed: {e}")
        return False

def test_env():
    """Test du fichier .env"""
    from dotenv import load_dotenv
    load_dotenv()
    
    url = os.getenv("SUPABASE_URL")
    key = os.getenv("SUPABASE_KEY")
    
    if url and "your-project" not in url:
        print("✅ SUPABASE_URL configured")
    else:
        print("❌ SUPABASE_URL not configured")
        return False
    
    if key and "your_anon_key" not in key:
        print("✅ SUPABASE_KEY configured")
    else:
        print("❌ SUPABASE_KEY not configured")
        return False
    
    return True

if __name__ == "__main__":
    print("🔍 MINIMAL TEST")
    print("=" * 30)
    
    import_ok = test_import()
    env_ok = test_env()
    
    if import_ok and env_ok:
        print("\\n🎉 All tests passed!")
        print("You can now run: python run_app.py")
    else:
        print("\\n⚠️  Some tests failed. Check the output above.")
'''
    
    with open('test_minimal.py', 'w', encoding='utf-8') as f:
        f.write(test_content)
    
    print("✅ test_minimal.py created")

def main():
    """Exécuter toutes les réparations"""
    print("🚀 QUICK FIX - WEALTH DASHBOARD")
    print("=" * 40)
    
    try:
        create_init_files()
        create_database_file()
        create_env_template()
        create_minimal_test()
        
        print("\n" + "=" * 40)
        print("✅ Quick fix completed!")
        print("\nNext steps:")
        print("1. Update .env with your Supabase credentials")
        print("2. Run: pip install -r requirements.txt")
        print("3. Test: python test_minimal.py")
        print("4. If test passes, run: python run_app.py")
        
    except Exception as e:
        print(f"❌ Error during quick fix: {e}")
        return False
    
    return True

if __name__ == "__main__":
    main()