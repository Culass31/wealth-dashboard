import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    DEFAULT_USER_ID = os.getenv("DEFAULT_USER_ID", "e8bb01e2-454c-4edb-ba99-f1d2b7dcf4b9") # Valeur par défaut si non définie
    
    # Paths
    DATA_RAW_PATH = "data/raw"
    DATA_PROCESSED_PATH = "data/processed"
    
    # Platform mappings
    PLATFORM_MAPPING = {
        "lbp": "LBP",
        "pretup": "PretUp", 
        "bienpreter": "BienPreter",
        "homunity": "Homunity",
        "pea": "PEA",
        "av": "AV"
    }
    
    # Investment types
    INVESTMENT_TYPES = {
        "crowdfunding": ["LBP", "PretUp", "BienPreter", "Homunity"],
        "stocks": ["PEA"],
        "insurance": ["AV"]
    }