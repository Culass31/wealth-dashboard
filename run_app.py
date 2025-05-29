
import subprocess
import sys
import os

def main():
    """Launch the Streamlit app"""
    
    # Check if in virtual environment
    if not hasattr(sys, 'real_prefix') and not (hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix):
        print("⚠️  Warning: You might want to activate your virtual environment first")
        print("Run: source venv/bin/activate (or venv\\Scripts\\activate on Windows)")
    
    # Change to frontend directory
    frontend_dir = os.path.join(os.path.dirname(__file__), 'frontend')
    if os.path.exists(frontend_dir):
        os.chdir(frontend_dir)
    
    # Run Streamlit
    try:
        subprocess.run([
            sys.executable, "-m", "streamlit", "run", "app.py",
            "--server.port", "8501",
            "--server.address", "localhost"
        ])
    except KeyboardInterrupt:
        print("\n👋 Dashboard stopped")
    except Exception as e:
        print(f"Error running dashboard: {e}")

if __name__ == "__main__":
    main()