"""Database models for ScrapFlask"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from scrapflask.database import db

class ScrapingJob(db.Model):
    """Model for tracking scraping jobs"""
    __tablename__ = 'scraping_job'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), nullable=False, unique=True)  # Scrappy API session ID
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, running, completed, failed
    owner_names = db.Column(JSONB, nullable=False)  # List of owner names to scrape
    locale = db.Column(db.String(50), nullable=False)
    tax_year = db.Column(db.String(4), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    last_status_check = db.Column(db.DateTime)  # Track last status check from Scrappy API


class ScrapingResult(db.Model):
    """Model for storing scraping results"""
    __tablename__ = 'scraping_result'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('scraping_job.id'), nullable=False)
    owner_name = db.Column(db.String(255), nullable=False)
    property_address = db.Column(db.String(255))
    parcel_id = db.Column(db.String(50))
    land_value = db.Column(db.Float)
    improvement_value = db.Column(db.Float)
    total_value = db.Column(db.Float)
    tax_rate = db.Column(db.String(20))
    pdf_url = db.Column(db.String(255))  # URL from Scrappy API to fetch the PDF
    raw_data = db.Column(JSONB)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    job = db.relationship('ScrapingJob', backref=db.backref('results', lazy=True))


class ScrapingConfirmation(db.Model):
    """Model for storing confirmation requests"""
    __tablename__ = 'scraping_confirmation'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    job_id = db.Column(db.Integer, db.ForeignKey('scraping_job.id'), nullable=False)
    session_id = db.Column(db.String(36), nullable=False)  # Scrappy API session ID
    owner_name = db.Column(db.String(255), nullable=False)
    matched_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    response = db.Column(db.String(3))  # yes/no