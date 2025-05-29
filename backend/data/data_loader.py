from backend.models.database import DatabaseManager
from backend.data.parsers import LBPParser, PretUpParser, BienPreterParser
import os

class DataLoader:
    """Main class to load data from various platforms"""
    
    def __init__(self):
        self.db = DatabaseManager()
        
    def load_platform_data(self, file_path: str, platform: str, user_id: str) -> bool:
        """Load data from a platform file"""
        
        # Select appropriate parser
        if platform.lower() == 'lbp':
            parser = LBPParser(user_id)
        elif platform.lower() == 'pretup':
            parser = PretUpParser(user_id)
        elif platform.lower() == 'bienpreter':
            parser = BienPreterParser(user_id)
        else:
            print(f"Parser not implemented for platform: {platform}")
            return False
        
        try:
            # Parse data
            investments, cash_flows = parser.parse(file_path)
            
            # Insert into database
            success_inv = self.db.insert_investments(investments)
            success_cf = self.db.insert_cash_flows(cash_flows)
            
            print(f"Loaded {len(investments)} investments and {len(cash_flows)} cash flows from {platform}")
            return success_inv and success_cf
            
        except Exception as e:
            print(f"Error loading data from {platform}: {e}")
            return False
    
    def load_all_user_files(self, user_id: str, data_folder: str = "data/raw") -> bool:
        """Load all files from user's data folder"""
        
        platform_files = {
            'lbp': 'Portefeuille LPB 20250529.xlsx',
            'pretup': 'Portefeuille PretUp 20250529.xlsx',
            'bienpreter': 'Portefeuille BienPreter 20250529.xlsx',
            'homunity': 'Portefeuille Homunity 20250529.xlsx'
        }
        
        success_count = 0
        
        for platform, filename in platform_files.items():
            file_path = os.path.join(data_folder, filename)
            if os.path.exists(file_path):
                if self.load_platform_data(file_path, platform, user_id):
                    success_count += 1
                else:
                    print(f"Failed to load {platform}")
            else:
                print(f"File not found: {file_path}")
        
        print(f"Successfully loaded {success_count}/{len(platform_files)} platforms")
        return success_count > 0