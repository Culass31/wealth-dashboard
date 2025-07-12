import os
from dotenv import load_dotenv

load_dotenv()

class Config:
    # Supabase
    SUPABASE_URL = os.getenv("SUPABASE_URL")
    SUPABASE_KEY = os.getenv("SUPABASE_KEY")
    SUPABASE_SERVICE_KEY = os.getenv("SUPABASE_SERVICE_KEY")
    
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