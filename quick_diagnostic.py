"""
Script de diagnostic rapide pour identifier les problèmes
"""
import os
import sys
from pathlib import Path

def check_file_structure():
    """Vérifier la structure des fichiers"""
    print("📁 Checking file structure...")
    
    required_files = {
        '.env': 'Configuration Supabase',
        'backend/models/database.py': 'Gestionnaire base de données',
        'backend/data/parsers.py': 'Parsers des plateformes',
        'backend/utils/file_helpers.py': 'Utilitaires fichiers',
        'frontend/app.py': 'Dashboard Streamlit'
    }
    
    required_dirs = [
        'backend', 'backend/models', 'backend/data', 'backend/utils',
        'frontend', 'data/raw', 'data/processed'
    ]
    
    # Check directories
    for directory in required_dirs:
        if os.path.exists(directory):
            print(f"✅ Directory: {directory}")
        else:
            print(f"❌ Missing directory: {directory}")
            os.makedirs(directory, exist_ok=True)
            print(f"  → Created: {directory}")
    
    # Check files
    missing_files = []
    for file_path, description in required_files.items():
        if os.path.exists(file_path):
            size = os.path.getsize(file_path)
            print(f"✅ {file_path} ({size} bytes)")
        else:
            print(f"❌ Missing: {file_path} - {description}")
            missing_files.append(file_path)
    
    return missing_files

def check_env_file():
    """Vérifier le fichier .env"""
    print("\n🔧 Checking .env configuration...")
    
    if not os.path.exists('.env'):
        print("❌ .env file not found!")
        print("Creating template .env file...")
        
        env_template = """# Supabase Configuration
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here

# Example:
# SUPABASE_URL=https://xxxxx.supabase.co
# SUPABASE_KEY=eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9...
"""
        
        with open('.env', 'w') as f:
            f.write(env_template)
        print("✅ Created .env template - PLEASE UPDATE WITH YOUR CREDENTIALS!")
        return False
    
    # Check .env content
    with open('.env', 'r') as f:
        content = f.read()
    
    required_vars = ['SUPABASE_URL', 'SUPABASE_KEY']
    configured_vars = []
    
    for var in required_vars:
        if f"{var}=" in content and "your_" not in content.split(f"{var}=")[1].split('\n')[0]:
            configured_vars.append(var)
            print(f"✅ {var} configured")
        else:
            print(f"❌ {var} not configured (still has placeholder)")
    
    return len(configured_vars) == len(required_vars)

def test_python_imports():
    """Tester les imports Python"""
    print("\n🐍 Testing Python imports...")
    
    imports_to_test = [
        ('supabase', 'Supabase client'),
        ('pandas', 'Data manipulation'),
        ('streamlit', 'Dashboard framework'),
        ('plotly', 'Charts and graphs'),
        ('dotenv', 'Environment variables'),
    ]
    
    successful_imports = 0
    
    for module, description in imports_to_test:
        try:
            __import__(module)
            print(f"✅ {module} - {description}")
            successful_imports += 1
        except ImportError:
            print(f"❌ {module} - {description} (run: pip install {module})")
    
    return successful_imports == len(imports_to_test)

def test_database_import():
    """Tester l'import de DatabaseManager spécifiquement"""
    print("\n🗄️  Testing DatabaseManager import...")
    
    try:
        # Add current directory to path
        current_dir = os.getcwd()
        if current_dir not in sys.path:
            sys.path.insert(0, current_dir)
        
        # Try to import
        from backend.models.database import DatabaseManager
        print("✅ DatabaseManager imported successfully")
        
        # Try to instantiate (this will test Supabase connection)
        try:
            db = DatabaseManager()
            print("✅ DatabaseManager instantiated successfully")
            return True
        except Exception as e:
            print(f"⚠️  DatabaseManager import OK, but instantiation failed: {e}")
            return False
            
    except ImportError as e:
        print(f"❌ Cannot import DatabaseManager: {e}")
        
        # Check if the file exists and has content
        db_file = 'backend/models/database.py'
        if os.path.exists(db_file):
            with open(db_file, 'r') as f:
                content = f.read()
            
            if 'class DatabaseManager' in content:
                print("  → File exists and contains DatabaseManager class")
                print("  → Check for syntax errors in the file")
            else:
                print("  → File exists but doesn't contain DatabaseManager class")
                print("  → Please copy the correct content")
        else:
            print("  → backend/models/database.py file not found")
        
        return False

def create_missing_files():
    """Créer les fichiers manquants avec du contenu minimal"""
    print("\n🔧 Creating missing files...")
    
    # Create __init__.py files for Python packages
    init_files = [
        'backend/__init__.py',
        'backend/models/__init__.py',
        'backend/data/__init__.py',
        'backend/utils/__init__.py'
    ]
    
    for init_file in init_files:
        if not os.path.exists(init_file):
            Path(init_file).touch()
            print(f"✅ Created: {init_file}")

def main():
    """Exécuter tous les diagnostics"""
    print("🚀 DIAGNOSTIC RAPIDE - WEALTH DASHBOARD\n")
    print("=" * 50)
    
    # Tests
    missing_files = check_file_structure()
    env_ok = check_env_file()
    imports_ok = test_python_imports()
    
    # Create missing Python package files
    create_missing_files()
    
    # Test specific import
    db_import_ok = test_database_import()
    
    print("\n" + "=" * 50)
    print("📋 RÉSUMÉ DU DIAGNOSTIC")
    print("=" * 50)
    
    if not missing_files:
        print("✅ Structure de fichiers: OK")
    else:
        print(f"⚠️  Fichiers manquants: {len(missing_files)}")
    
    if env_ok:
        print("✅ Configuration .env: OK")
    else:
        print("❌ Configuration .env: À configurer")
    
    if imports_ok:
        print("✅ Dépendances Python: OK")
    else:
        print("❌ Dépendances Python: À installer")
    
    if db_import_ok:
        print("✅ DatabaseManager: OK")
    else:
        print("❌ DatabaseManager: Problème")
    
    print("\n🎯 ACTIONS RECOMMANDÉES:")
    
    if not env_ok:
        print("1. Configurer vos clés Supabase dans le fichier .env")
    
    if not imports_ok:
        print("2. Installer les dépendances: pip install -r requirements.txt")
    
    if not db_import_ok:
        print("3. Vérifier le contenu du fichier backend/models/database.py")
    
    if missing_files:
        print("4. Créer les fichiers manquants avec le bon contenu")
    
    if env_ok and imports_ok and db_import_ok and not missing_files:
        print("🎉 Tout semble OK! Vous pouvez lancer: python run_app.py")
    
    return env_ok and imports_ok and db_import_ok and not missing_files

if __name__ == "__main__":
    success = main()
    if not success:
        print(f"\n⚠️  Des problèmes ont été détectés. Veuillez les corriger avant de continuer.")
    sys.exit(0 if success else 1)