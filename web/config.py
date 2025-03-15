"""Configuration settings for ScrapFlask"""
import os
from datetime import timedelta

class Config:
    """Base configuration"""
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL')
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    SQLALCHEMY_ENGINE_OPTIONS = {
        "pool_recycle": 300,
        "pool_pre_ping": True,
    }

    # Scrappy API Configuration
    SCRAPPY_API_URL = os.environ.get('SCRAPPY_API_URL', 'http://localhost:8080')
    SCRAPPY_API_TIMEOUT = 30  # seconds
    SCRAPPY_STATUS_CHECK_INTERVAL = timedelta(seconds=5)
    SCRAPPY_SESSION_EXPIRY = timedelta(hours=24)

    # Flask settings
    SECRET_KEY = os.environ.get('FLASK_SECRET_KEY', 'dev')
