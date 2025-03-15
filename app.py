from pydantic import BaseModel, Field, validator
from fastapi import FastAPI, HTTPException, Body, Depends, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, constr, validator
import os
import asyncio
import sys
import io
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional
import uvicorn
import uuid

from main import get_session_folders  # Correct import path
from core.locales import SUPPORTED_LOCALES
from core.scrapers.property_scraper import scrape_property_data
from core.utils.logging_setup import setup_logging

VERSION = "v1.0.0"

# Set up logging
logger = setup_logging("scrappy.api", "INFO", "scrappy_api.log")

# Define constants for timeouts and intervals
SCRAPPY_API_TIMEOUT = 30  # seconds
SCRAPPY_STATUS_CHECK_INTERVAL = timedelta(seconds=5)
SCRAPPY_SESSION_EXPIRY = timedelta(hours=24)

app = FastAPI(
    title="Scrappy API",
    description="API for property tax data scraping",
    version=VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, specify actual origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

class ScrapeRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=36)
    owners: str = Field(..., min_length=1, max_length=1000)
    locale: str = Field(..., min_length=1, max_length=50)
    tax_year: str = Field("2024", min_length=4, max_length=4)

    @validator('locale')
    def locale_must_be_supported(cls, v: str) -> str:
        if v not in SUPPORTED_LOCALES:
            raise ValueError(f'Locale {v} is not supported')
        return v

class ConfirmationRequest(BaseModel):
    session_id: str = Field(..., min_length=1, max_length=36)
    confirmation: str = Field(..., min_length=2, max_length=3)  # 'yes' or 'no'
    confirmation_id: Optional[str] = None

    @validator('confirmation')
    def confirmation_must_be_valid(cls, v: str) -> str:
        if v not in ['yes', 'no']:
            raise ValueError("Confirmation must be 'yes' or 'no'")
        return v
    
@app.get("/")
async def root():
    return {
        "name": "Scrappy API",
        "version": VERSION,
        "endpoints": {
            "POST /scrape": "Start scraping with provided parameters",
            "POST /confirm": "Confirm property match",
            "GET /files/{session_id}": "Get list of PDFs for a session",
            "GET /locales": "Get list of supported locales"
        }
    }

@app.get("/health")
async def health_check():
    return {"status": "healthy", "version": VERSION}

@app.get("/locales")
async def get_locales():
    return {
        "locales": {
            locale: data["name"]
            for locale, data in SUPPORTED_LOCALES.items()
        }
    }

@app.post("/confirm")
async def confirm(request: ConfirmationRequest):
    """Handle confirmation responses from users"""
    try:
        # Import here to avoid circular imports
        from core.utils.confirmation import Session, Confirmation

        logger.info(f"Received confirmation: {request.confirmation} for session {request.session_id}")

        with Session() as session:
            # If confirmation_id is provided, use it directly
            if request.confirmation_id:
                confirmation = session.query(Confirmation).filter_by(
                    id=request.confirmation_id
                ).first()
            else:
                # Otherwise find the latest pending confirmation for this session
                confirmation = session.query(Confirmation).filter_by(
                    session_id=request.session_id,
                    response=None
                ).order_by(Confirmation.created_at.desc()).first()

            if not confirmation:
                logger.warning(f"No pending confirmation found for session {request.session_id}")
                raise HTTPException(
                    status_code=404,
                    detail=f"No pending confirmation found for session {request.session_id}"
                )

            # Update the confirmation with the response
            confirmation.response = request.confirmation
            session.commit()

            logger.info(f"Updated confirmation {confirmation.id} with response: {request.confirmation}")

            return {
                "status": "success",
                "data": {
                    "session_id": request.session_id,
                    "confirmation": request.confirmation,
                    "confirmation_id": confirmation.id
                },
                "message": "Confirmation received"
            }
    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"Error processing confirmation: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Server error: {str(e)}")

async def process_scraping(session_id: str, owners: str, locale: str, tax_year: str):
    """Background task to process scraping without blocking the API response"""
    try:
        logger.info(f"Starting background scraping for session {session_id}")

        # Set environment variables for the scraping process
        os.environ["SCRAPPY_SESSION_ID"] = session_id
        os.environ["SCRAPPY_EXTERNAL_CONFIRMATION"] = "true"
        os.environ["SCRAPPY_LOCALE"] = locale
        os.environ["TAX_YEAR"] = tax_year

        # Split owner names and process each one
        input_names = [name.strip() for name in owners.split(";") if name.strip()]

        # Create session folders
        get_session_folders(session_id)

        # Run the scraping process
        results = await asyncio.to_thread(
            scrape_property_data,
            input_names,
            locale=locale,
            tax_year=tax_year
        )

        logger.info(f"Completed scraping for session {session_id}: {len(results)} results")

        # Store results in database or file system if needed
        # In a real application, you might update a status record with the results

    except Exception as e:
        logger.error(f"Error in background scraping task for session {session_id}: {e}", exc_info=True)

@app.post("/scrape")
async def scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """Start a scraping job with the provided parameters"""
    try:
        logger.info(f"[{VERSION}] Received scrape request")

        # Generate a session ID if not provided or use the existing one
        session_id = request.session_id or str(uuid.uuid4())
        logger.info(f"Using session ID: {session_id}")

        # Create session directories
        session_folder, pdf_folder = get_session_folders(session_id)

        # Start the scraping process in the background
        background_tasks.add_task(
            process_scraping,
            session_id=session_id,
            owners=request.owners,
            locale=request.locale,
            tax_year=request.tax_year
        )

        return {
            "status": "success",
            "message": "Scraping job started",
            "session_id": session_id,
            "data": {
                "owners": request.owners,
                "locale": request.locale,
                "tax_year": request.tax_year
            }
        }

    except HTTPException:
        raise
    except Exception as e:
        logger.error(f"[{VERSION}] Request handling error: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"[{VERSION}] Server error: {str(e)}")

@app.get("/files/{session_id}")
async def get_session_files(session_id: str, page: int = 1, per_page: int = 50):
    """Get list of files for a session with pagination"""
    try:
        session_folder, pdf_folder = get_session_folders(session_id)

        if not os.path.exists(pdf_folder):
            return {
                "files": [],
                "session_id": session_id,
                "pagination": {
                    "page": 1,
                    "per_page": per_page,
                    "total": 0,
                    "pages": 0,
                    "has_next": False,
                    "has_prev": False
                }
            }

        all_files = os.listdir(pdf_folder)
        total_files = len(all_files)
        total_pages = (total_files + per_page - 1) // per_page if total_files > 0 else 1

        # Validate page number
        page = max(1, min(page, total_pages))

        # Paginate files
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_files)
        paginated_files = all_files[start_idx:end_idx]

        return {
            "session_id": session_id,
            "files": paginated_files,
            "file_count": total_files,
            "pagination": {
                "page": page,
                "per_page": per_page,
                "total": total_files,
                "pages": total_pages,
                "has_next": page < total_pages,
                "has_prev": page > 1
            }
        }
    except Exception as e:
        logger.error(f"Error getting files for session {session_id}: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error getting files: {str(e)}")

if __name__ == "__main__":
    # Get port from environment or use default
    port = int(os.getenv('PORT', 8080))

    # Run with uvicorn
    uvicorn.run(
        app,
        host="0.0.0.0",
        port=port,
        log_level="info"
    )
