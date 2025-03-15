"""
Shared configuration for Scrappy application
"""
import os
from pathlib import Path

# Base directory
BASE_DIR = Path(__file__).resolve().parent

# API settings
API_HOST = os.getenv("API_HOST", "0.0.0.0")
API_PORT = int(os.getenv("API_PORT", 8080))
API_URL = os.getenv("API_URL", f"http://localhost:{API_PORT}")

# Web settings
WEB_HOST = os.getenv("WEB_HOST", "0.0.0.0")
WEB_PORT = int(os.getenv("WEB_PORT", 5000))
SECRET_KEY = os.getenv("SECRET_KEY", "dev-secret-key-change-in-production")

# Database
DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///scrappy.db")

# Paths
DATA_DIR = BASE_DIR / "data"
PDF_DIR = DATA_DIR / "pdfs"
OUTPUT_DIR = DATA_DIR / "outputs"

# Create directories if they don't exist
PDF_DIR.mkdir(parents=True, exist_ok=True)
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
