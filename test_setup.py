"""
Script de test pour vérifier l'installation et la configuration
"""
import os
import sys
from dotenv import load_dotenv

def test_environment():
    """Test basic environment setup"""
    print("🔍 Testing environment setup...")
    
    # Test Python version
    python_version = sys.version_info
    if python_version >= (3, 8):
        print(f"✅ Python version: {python_version.major}.{python_version.minor}")
    else:
        print(f"❌ Python version too old: {python_version.major}.{python_version.minor}")
        return False
    
    # Test required packages
    required_packages = [
        'streamlit', 'pandas', 'plotly', 'supabase', 
        'fastapi', 'sqlalchemy', 'python-dotenv'
    ]
    
    missing_packages = []
    for package in required_packages:
        try:
            __import__(package)
            print(f"✅ {package}")
        except ImportError:
            print(f"❌ {package} - missing")
            missing_packages.append(package)
    
    if missing_packages:
        print(f"\n⚠️  Install missing packages: pip install {' '.join(missing_packages)}")
        return False
    
    return True

def test_configuration():
    """Test configuration files"""
    print("\n🔧 Testing configuration...")
    
    # Test .env file
    if os.path.exists('.env'):
        print("✅ .env file found")
        load_dotenv()
        
        required_vars = ['SUPABASE_URL', 'SUPABASE_KEY']
        for var in required_vars:
            if os.getenv(var):
                print(f"✅ {var} configured")
            else:
                print(f"❌ {var} missing in .env")
                return False
    else:
        print("❌ .env file not found")
        print("Create .env with your Supabase credentials")
        return False
    
    return True

def test_database_connection():
    """Test Supabase connection"""
    print("\n🗄️  Testing database connection...")
    
    try:
        from backend.models.database import DatabaseManager
        db = DatabaseManager()
        
        # Test simple query
        result = db.supabase.table('investments').select("count").execute()
        print("✅ Database connection successful")
        return True
        
    except Exception as e:
        print(f"❌ Database connection failed: {e}")
        print("Check your Supabase credentials in .env")
        return False

def test_data_parsing():
    """Test data parsing with sample file"""
    print("\n📊 Testing data parsing...")
    
    try:
        from backend.data.parsers import LBPParser
        
        # Test with dummy data (if sample file exists)
        sample_files = [
            'data/raw/Portefeuille LPB 20250529.xlsx',
            'Portefeuille LPB 20250529.xlsx'
        ]
        
        for file_path in sample_files:
            if os.path.exists(file_path):
                parser = LBPParser("test-user")
                investments, cash_flows = parser.parse(file_path)
                print(f"✅ Parsed {len(investments)} investments, {len(cash_flows)} cash flows")
                return True
        
        print("⚠️  No sample data files found - manual testing required")
        return True
        
    except Exception as e:
        print(f"❌ Parsing failed: {e}")
        return False

def run_all_tests():
    """Run all tests"""
    print("🚀 Starting setup validation...\n")
    
    tests = [
        test_environment,
        test_configuration,
        test_database_connection,
        test_data_parsing
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"❌ Test failed with error: {e}")
            results.append(False)
    
    print(f"\n📋 Results: {sum(results)}/{len(results)} tests passed")
    
    if all(results):
        print("🎉 All tests passed! You're ready to go!")
        print("\nNext steps:")
        print("1. Copy your Excel files to data/raw/")
        print("2. Run: python run_app.py")
        print("3. Open http://localhost:8501")
    else:
        print("⚠️  Some tests failed. Please fix the issues above.")
    
    return all(results)

if __name__ == "__main__":
    run_all_tests()