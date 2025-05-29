"""Utility functions for confirmation handling"""
import os
import json
import time
import uuid
import logging
from termcolor import colored
from sqlalchemy import Column, String, DateTime, Boolean, create_engine
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker
from datetime import datetime

# Set up logging
logger = logging.getLogger(__name__)

# Database-backed confirmation system
DB_URL = os.environ.get('DATABASE_URL', 'sqlite:///scrappy_confirmations.db')
engine = create_engine(DB_URL)
Base = declarative_base()
Session = sessionmaker(bind=engine)

class Confirmation(Base):
    """Model for storing confirmation data"""
    __tablename__ = 'confirmations'

    id = Column(String(36), primary_key=True)
    session_id = Column(String(36), nullable=False, index=True)  # ID of the scraping session.
    owner = Column(String(255), nullable=False)  # Original owner name searched for.
    match = Column(String(255), nullable=False)  # Potential matching owner name found.
    address = Column(String(255), nullable=True)  # Property address for the potential match, provides context.
    created_at = Column(DateTime, default=datetime.utcnow)  # Timestamp of when the confirmation was requested.
    response = Column(String(3), nullable=True)  # User's response ('yes' or 'no').

def create_db():
    """Create database tables if they don't exist"""
    Base.metadata.create_all(engine)

def ask_confirmation(match, current_owner, address):
    """
    Handle confirmation in both API and CLI contexts.
    Shows a nicely formatted prompt in CLI mode.

    Args:
        match (str): The matched property owner name found by the scraper.
        current_owner (str): The input owner name that was being searched for.
        address (str): The property address associated with the `match`. This is used
                       to provide context to the user during confirmation.

    Returns:
        bool: True if the user confirms the match, False otherwise (including timeout).
    """
    create_db()  # Ensure tables exist

    # Check for external confirmation mode
    external_mode = os.environ.get("SCRAPPY_EXTERNAL_CONFIRMATION", "false").lower() == "true"

    # Generate a unique ID for this confirmation
    confirmation_id = str(uuid.uuid4())
    session_id = os.environ.get("SCRAPPY_SESSION_ID", "default")

    # Create a database record for this confirmation
    with Session() as session:
        confirmation = Confirmation(
            id=confirmation_id,
            session_id=session_id,
            owner=current_owner,  # The name originally searched for.
            match=match,          # The name found on the site.
            address=address,      # The address of the property for `match`.
            created_at=datetime.utcnow()
        )
        session.add(confirmation)
        session.commit()

    if external_mode:
        # API mode - emit JSON response and wait for confirmation via database
        response = {
            "status": "confirmation_required",
            "confirmation_id": confirmation_id,
            "owner": current_owner,
            "match": match,
            "address": address,  # Address is included in the JSON for API consumers.
            "session_id": session_id
        }
        print(json.dumps(response), flush=True)

        # Poll database for response
        max_wait_time = 300  # 5 minutes timeout
        start_time = time.time()

        while time.time() - start_time < max_wait_time:
            with Session() as session:
                result = session.query(Confirmation).filter_by(id=confirmation_id).first()
                if result and result.response:
                    return result.response == "yes"
            time.sleep(0.5)

        # Timeout - log and return False
        logger.warning(f"Confirmation timed out after {max_wait_time} seconds")
        return False
    else:
        # CLI mode - interactive confirmation with improved formatting.
        # The address is shown to help the user decide.
        while True:
            response = input(f"Does {colored(current_owner, 'yellow')} at {colored(address, 'cyan')} match {colored(match, 'yellow')}? (y/n): ").strip().lower()
            if response in ["y", "n"]:
                # Update the database record
                with Session() as session:
                    result = session.query(Confirmation).filter_by(id=confirmation_id).first()
                    if result:
                        result.response = "yes" if response == "y" else "no"
                        session.commit()
                return response == "y"

            print("Invalid input. Please enter 'y' for yes or 'n' for no.")
