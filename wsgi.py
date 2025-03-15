"""
WSGI entry point for Flask web application
"""
import os
import sys
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))

from web.app import create_app

app = create_app()

if __name__ == "__main__":
    # Import configuration
    from config import WEB_HOST, WEB_PORT
    app.run(host=WEB_HOST, port=WEB_PORT, debug=True)
