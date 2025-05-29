# test_minimal.py
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
        print("\n🎉 All tests passed!")
        print("You can now run: python run_app.py")
    else:
        print("\n⚠️  Some tests failed. Check the output above.")
