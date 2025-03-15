"""Database models for ScrapFlask"""
from datetime import datetime
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.ext.mutable import MutableDict
from web.database import db

class ScrapingJob(db.Model):
    """Model for tracking scraping jobs"""
    __tablename__ = 'scraping_job'

    id = db.Column(db.Integer, primary_key=True)
    session_id = db.Column(db.String(36), nullable=False, unique=True, index=True)  # Scrappy API session ID
    status = db.Column(db.String(20), nullable=False, default='pending', index=True)  # pending, running, completed, failed, confirmation_required
    owner_names = db.Column(MutableDict.as_mutable(JSONB), nullable=False)  # List of owner names to scrape
    locale = db.Column(db.String(50), nullable=False, index=True)
    tax_year = db.Column(db.String(4), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    completed_at = db.Column(db.DateTime)
    error_message = db.Column(db.Text)
    last_status_check = db.Column(db.DateTime)  # Track last status check from Scrappy API
    
    def __repr__(self):
        return f"<ScrapingJob id={self.id} session_id={self.session_id} status={self.status}>"
    
    @classmethod
    def get_active_jobs(cls):
        """Get all jobs that are not in a final state"""
        return cls.query.filter(
            cls.status.in_(['pending', 'running', 'confirmation_required'])
        ).all()
    
    @classmethod
    def get_recent_jobs(cls, limit=10):
        """Get recent jobs ordered by creation date"""
        return cls.query.order_by(cls.created_at.desc()).limit(limit).all()
    
    @property
    def is_active(self):
        """Check if the job is still active"""
        return self.status in ['pending', 'running', 'confirmation_required']
    
    @property
    def duration(self):
        """Calculate job duration in seconds"""
        if not self.completed_at:
            return None
        return (self.completed_at - self.created_at).total_seconds()


class ScrapingResult(db.Model):
    """Model for storing scraping results"""
    __tablename__ = 'scraping_result'

    id = db.Column(db.Integer, primary_key=True)
    job_id = db.Column(db.Integer, db.ForeignKey('scraping_job.id', ondelete='CASCADE'), nullable=False, index=True)
    owner_name = db.Column(db.String(255), nullable=False, index=True)
    property_address = db.Column(db.String(255), index=True)
    parcel_id = db.Column(db.String(50), index=True)
    land_value = db.Column(db.Float)
    improvement_value = db.Column(db.Float)
    total_value = db.Column(db.Float)
    tax_rate = db.Column(db.String(20))
    pdf_url = db.Column(db.String(255))  # URL from Scrappy API to fetch the PDF
    raw_data = db.Column(MutableDict.as_mutable(JSONB))
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow)
    job = db.relationship('ScrapingJob', backref=db.backref('results', lazy=True, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f"<ScrapingResult id={self.id} job_id={self.job_id} owner={self.owner_name}>"
    
    @classmethod
    def get_by_parcel(cls, parcel_id):
        """Find results by parcel ID"""
        return cls.query.filter_by(parcel_id=parcel_id).all()
    
    @classmethod
    def get_by_owner(cls, owner_name):
        """Find results by owner name (partial match)"""
        return cls.query.filter(cls.owner_name.ilike(f"%{owner_name}%")).all()


class ScrapingConfirmation(db.Model):
    """Model for storing confirmation requests"""
    __tablename__ = 'scraping_confirmation'

    id = db.Column(db.String(36), primary_key=True)  # UUID
    job_id = db.Column(db.Integer, db.ForeignKey('scraping_job.id', ondelete='CASCADE'), nullable=False, index=True)
    session_id = db.Column(db.String(36), nullable=False, index=True)  # Scrappy API session ID
    owner_name = db.Column(db.String(255), nullable=False)
    matched_name = db.Column(db.String(255), nullable=False)
    created_at = db.Column(db.DateTime, nullable=False, default=datetime.utcnow, index=True)
    response = db.Column(db.String(3))  # yes/no
    job = db.relationship('ScrapingJob', backref=db.backref('confirmations', lazy=True, cascade='all, delete-orphan'))
    
    def __repr__(self):
        return f"<ScrapingConfirmation id={self.id} job_id={self.job_id} responded={self.response is not None}>"
    
    @classmethod
    def get_pending(cls):
        """Get all pending confirmations"""
        return cls.query.filter_by(response=None).order_by(cls.created_at.desc()).all()
    
    @property
    def is_pending(self):
        """Check if the confirmation is still pending a response"""
        return self.response is None