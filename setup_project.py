"""
Script d'initialisation automatique du projet
"""
import os
import shutil
from pathlib import Path

def create_project_structure():
    """Create the recommended project structure"""
    print("📁 Creating project structure...")
    
    directories = [
        'backend/api',
        'backend/data', 
        'backend/models',
        'backend/utils',
        'backend/agents',
        'frontend',
        'data/raw',
        'data/processed',
        'docs',
        'tests'
    ]
    
    for directory in directories:
        Path(directory).mkdir(parents=True, exist_ok=True)
        print(f"✅ Created: {directory}")

def create_config_files():
    """Create basic configuration files"""
    print("\n⚙️  Creating configuration files...")
    
    # .env template
    env_content = """# Supabase Configuration
SUPABASE_URL=your_supabase_project_url_here
SUPABASE_KEY=your_supabase_anon_key_here
SUPABASE_SERVICE_KEY=your_service_role_key_here

# Development settings
DEBUG=true
LOG_LEVEL=INFO
"""
    
    if not os.path.exists('.env'):
        with open('.env', 'w') as f:
            f.write(env_content)
        print("✅ Created: .env template")
    
    # .gitignore
    gitignore_content = """# Environment
.env
venv/
__pycache__/
*.pyc
*.pyo
*.pyd
.Python

# Data files
data/raw/*.xlsx
data/raw/*.pdf
data/processed/

# IDE
.vscode/
.idea/

# OS
.DS_Store
Thumbs.db

# Logs
*.log

# Temporary files
temp_*
"""
    
    if not os.path.exists('.gitignore'):
        with open('.gitignore', 'w') as f:
            f.write(gitignore_content)
        print("✅ Created: .gitignore")

def create_readme():
    """Create project README"""
    readme_content = """# Wealth Dashboard

Personal wealth management dashboard with AI-powered insights.

## Quick Start

1. **Setup Environment**
   ```bash
   python -m venv venv
   source venv/bin/activate  # or venv\\Scripts\\activate on Windows
   pip install -r requirements.txt
   ```

2. **Configure Supabase**
   - Create account at https://supabase.com
   - Create new project
   - Copy URL and keys to .env file
   - Run SQL schema in Supabase SQL editor

3. **Test Setup**
   ```bash
   python test_setup.py
   ```

4. **Load Data**
   - Copy your Excel files to `data/raw/`
   - Run the dashboard: `python run_app.py`
   - Upload files via the web interface

## Project Structure

```
wealth-dashboard/
├── backend/           # Data processing & API
├── frontend/          # Streamlit dashboard  
├── data/             # Raw and processed data
└── docs/             # Documentation
```

## Supported Platforms

- LBP (La Brique Pierre)
- PretUp 
- BienPreter
- Homunity
- PEA (Bourse Direct)
- Assurance Vie (Linxea)

## Features

- 📊 Multi-platform portfolio tracking
- 💰 Real-time performance metrics
- 🤖 AI-powered investment insights
- 📱 Mobile-responsive interface
- 🔒 Secure data storage

## Development

This project uses:
- **Backend**: FastAPI + Supabase
- **Frontend**: Streamlit + Plotly
- **AI**: LangChain + OpenAI/Anthropic
"""
    
    if not os.path.exists('README.md'):
        with open('README.md', 'w') as f:
            f.write(readme_content)
        print("✅ Created: README.md")

def main():
    """Initialize the project"""
    print("🚀 Initializing Wealth Dashboard project...\n")
    
    create_project_structure()
    create_config_files()
    create_readme()
    
    print("\n🎉 Project initialized successfully!")
    print("\nNext steps:")
    print("1. Edit .env with your Supabase credentials")
    print("2. Run: python test_setup.py")
    print("3. Copy your data files to data/raw/")
    print("4. Start dashboard: python run_app.py")

if __name__ == "__main__":
    main()