# backend/models/database.py
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
