from pydantic import BaseModel, Field, validator
# Standard library imports
import os
import asyncio
import sys
import io
import json
import logging
import time
from datetime import datetime, timedelta
from typing import List, Optional
import uvicorn # ASGI server
import uuid

# Third-party imports
from pydantic import BaseModel, Field, validator, constr # For data validation and settings management
from fastapi import FastAPI, HTTPException, Body, Depends, BackgroundTasks # FastAPI framework components
from fastapi.middleware.cors import CORSMiddleware # For handling Cross-Origin Resource Sharing

# Local application/library specific imports
from main import get_session_folders  # Utility to manage session-specific folders
from core.locales import SUPPORTED_LOCALES # Dictionary of supported locales for scraping
from core.scrapers.property_scraper import scrape_property_data # Main scraper for property listings
from core.scrapers.detail_scraper import scrape_details # Scraper for detailed property information
from core.utils.logging_setup import setup_logging # Logging configuration
from core.utils.confirmation import Session as ConfirmationSession, Confirmation # Database session and model for confirmations

# --- Application Metadata ---
VERSION = "v1.0.0" # Application version

# --- Logging Setup ---
# Configures application-wide logging. Logs are typically output to 'scrappy_api.log'.
logger = setup_logging("scrappy.api", "INFO", "scrappy_api.log")

# --- Global Constants and Configuration ---
# These constants are defined for potential future use in managing API behavior,
# such as request timeouts, status polling intervals, or session expiry policies.
# Currently, they are not actively used in the implemented logic.
SCRAPPY_API_TIMEOUT = 30  # Intended for API request timeouts (in seconds). Future use.
SCRAPPY_STATUS_CHECK_INTERVAL = timedelta(seconds=5) # Intended for polling intervals. Future use.
SCRAPPY_SESSION_EXPIRY = timedelta(hours=24) # Intended for session data cleanup. Future use.


# --- FastAPI Application Instance ---
# Initializes the FastAPI application, setting the title, description, and version
# for API documentation purposes (e.g., in Swagger UI or ReDoc).
app = FastAPI(
    title="Scrappy API",
    description="API for property tax data scraping",
    version=VERSION
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins. For production, specify actual client origins.
    allow_credentials=True, # Allows cookies to be included in cross-origin requests.
    allow_methods=["*"],    # Allows all HTTP methods.
    allow_headers=["*"],    # Allows all HTTP headers.
)

# --- Pydantic Models for Request Validation ---

class ScrapeRequest(BaseModel):
    """
    Defines the expected request body for the /scrape endpoint.
    Validates input fields for scraping jobs.
    """
    session_id: str = Field(..., description="A unique identifier for the scraping session (e.g., UUID).", min_length=1, max_length=36)
    owners: str = Field(..., description="A semicolon-separated string of owner names to search for.", min_length=1, max_length=1000)
    locale: str = Field(..., description="The locale code (e.g., 'davidson-tn') to target for scraping.", min_length=1, max_length=50)
    tax_year: str = Field("2024", description="The tax year for which to scrape data (defaults to '2024').", min_length=4, max_length=4)

    @validator('locale')
    def locale_must_be_supported(cls, v: str) -> str:
        """Ensures the provided locale code is present in SUPPORTED_LOCALES."""
        if v not in SUPPORTED_LOCALES:
            raise ValueError(f'Locale {v} is not supported. See /locales for available options.')
        return v

class ConfirmationRequest(BaseModel):
    """
    Defines the expected request body for the /confirm endpoint.
    Used to submit user confirmations for potential property matches.
    """
    session_id: str = Field(..., description="The session ID associated with the confirmation.", min_length=1, max_length=36)
    confirmation: str = Field(..., description="User's response: 'yes' or 'no'.", min_length=2, max_length=3)
    confirmation_id: Optional[str] = Field(None, description="Optional specific ID of the confirmation being responded to. If None, the latest pending confirmation for the session is used.", min_length=1, max_length=36)

    @validator('confirmation')
    def confirmation_must_be_valid(cls, v: str) -> str:
        """Ensures the confirmation response is either 'yes' or 'no'."""
        if v not in ['yes', 'no']:
            raise ValueError("Confirmation must be 'yes' or 'no'.")
        return v

# --- API Endpoints ---

@app.get("/")
async def root():
    """
    Root endpoint providing basic API information and discoverability.
    Returns the API name, version, and a list of available endpoints.
    """
    return {
        "name": "Scrappy API",
        "version": VERSION,
        "endpoints": {
            "POST /scrape": "Start scraping with provided parameters (owner names, locale, tax year).",
            "POST /confirm": "Submit confirmation for a potential property match.",
            "GET /files/{session_id}": "Get a list of PDF files generated during a session.",
            "GET /locales": "Get a list of supported locales for scraping.",
            "GET /logs/{session_id}": "Retrieve logs for a specific scraping session.",
            "GET /health": "Check the health status of the API."
        }
    }

@app.get("/health")
async def health_check():
    """
    Health check endpoint.
    Returns a simple status indicating the API is healthy and its version.
    Useful for monitoring and load balancers.
    """
    return {"status": "healthy", "version": VERSION}

@app.get("/locales")
async def get_locales():
    """
    Provides a list of supported locales for property scraping.
    The locales are sourced from the `SUPPORTED_LOCALES` dictionary,
    mapping locale codes to their human-readable names.
    """
    return {
        "locales": {
            locale: data["name"] # e.g., "davidson-tn": "Nashville/Davidson County, TN"
            for locale, data in SUPPORTED_LOCALES.items()
        }
    }

@app.get("/logs/{session_id}")
async def get_logs(session_id: str, since: Optional[str] = None, limit: int = 100):
    """
    Retrieves logs for a specific scraping session.
    Allows filtering logs by a starting timestamp (`since`) and limiting the number of log entries (`limit`).
    Interacts with `core.utils.session_logger.get_session_logs` to fetch the log data.

    Args:
        session_id (str): The ID of the session for which to retrieve logs.
        since (Optional[str]): ISO 8601 formatted timestamp. If provided, only logs after this time are returned.
        limit (int): Maximum number of log entries to return. Defaults to 100.
    """
    try:
        # Dynamically import to avoid issues if session_logger has complex dependencies or for modularity.
        from core.utils.session_logger import get_session_logs

        # Fetch logs using the utility function.
        logs = get_session_logs(session_id, since=since, limit=limit)
        return {
            "status": "success",
            "session_id": session_id,
            "logs": logs,
            "count": len(logs) # Number of log entries returned.
        }
    except Exception as e:
        # Log the full error for server-side debugging.
        logger.error(f"Error retrieving logs for session {session_id}: {e}", exc_info=True)
        # Return a generic error to the client.
        raise HTTPException(status_code=500, detail=f"An error occurred while retrieving logs for session {session_id}.")

@app.post("/confirm")
async def confirm(request: ConfirmationRequest):
    """
    Handles user confirmation for a property match identified during scraping.
    It updates a `Confirmation` record in the database (e.g., SQLite via SQLAlchemy).
    The `Confirmation` model is defined in `core.utils.confirmation`.

    The endpoint looks for a confirmation record based on `session_id` and optionally
    `confirmation_id`. If `confirmation_id` is not given, it targets the most recent
    pending confirmation for the session.
    """
    try:
        # `ConfirmationSession` is an alias for `sqlalchemy.orm.sessionmaker` bound to the engine.
        # `Confirmation` is the SQLAlchemy model for the 'confirmations' table.
        # These are imported from `core.utils.confirmation`.

        logger.info(f"Received confirmation: '{request.confirmation}' for session {request.session_id}, confirmation ID: {request.confirmation_id or 'latest pending'}")

        with ConfirmationSession() as db_session: # Start a new database session
            confirmation_record = None
            # If a specific confirmation_id is provided, query by that ID.
            if request.confirmation_id:
                confirmation_record = db_session.query(Confirmation).filter_by(
                    id=request.confirmation_id,
                    session_id=request.session_id # Ensure confirmation_id belongs to the session
                ).first()
            else:
                # If no specific confirmation_id, find the latest unresponded confirmation for the session.
                confirmation_record = db_session.query(Confirmation).filter_by(
                    session_id=request.session_id,
                    response=None  # Indicates pending confirmation
                ).order_by(Confirmation.created_at.desc()).first()

            # Handle case where no matching confirmation record is found.
            if not confirmation_record:
                user_facing_confirmation_id = request.confirmation_id if request.confirmation_id else 'any pending'
                log_msg = f"No pending confirmation found for session {request.session_id} with confirmation ID '{user_facing_confirmation_id}'."
                logger.warning(log_msg)
                # Return a 404 error if no suitable confirmation found.
                raise HTTPException(
                    status_code=404,
                    detail=f"No pending confirmation found for session {request.session_id} and confirmation ID '{user_facing_confirmation_id}'. Please ensure the session is active and the confirmation ID is correct if provided."
                )

            # Update the found confirmation record with the user's response.
            confirmation_record.response = request.confirmation
            db_session.commit() # Persist changes to the database.

            logger.info(f"Updated confirmation {confirmation_record.id} with response: {request.confirmation} for session {request.session_id}")

            return {
                "status": "success",
                "data": {
                    "session_id": request.session_id,
                    "confirmation": request.confirmation,
                    "confirmation_id": confirmation_record.id # Return the ID of the updated record.
                },
                "message": "Confirmation received successfully."
            }
    except HTTPException: # Re-raise HTTPException directly to preserve its status code and detail.
        raise
    except Exception as e:
        # Log the full error for server-side debugging.
        logger.error(f"Error processing confirmation for session {request.session_id}: {e}", exc_info=True)
        # Return a generic 500 error to the client.
        raise HTTPException(status_code=500, detail="An unexpected error occurred while processing your confirmation. Please try again or contact support.")

async def process_scraping(session_id: str, owners: str, locale: str, tax_year: str):
    """
    Asynchronous background task to perform the entire scraping process.
    This includes fetching initial property data and then enriching it with details.
    It's designed to run via FastAPI's BackgroundTasks to avoid blocking API responses.

    Args:
        session_id (str): Unique ID for this scraping session.
        owners (str): Semicolon-separated list of owner names to search.
        locale (str): The locale code for scraping.
        tax_year (str): The tax year for the data.
    """
    try:
        logger.info(f"Background scraping task started for session {session_id} (Locale: {locale}, Year: {tax_year}, Owners: {owners[:100]}...).")

        # Set environment variables specific to this scraping task.
        # SCRAPPY_SESSION_ID is used by other parts of the core logic (e.g., confirmation)
        # to associate actions with this session.
        os.environ["SCRAPPY_SESSION_ID"] = session_id
        # SCRAPPY_EXTERNAL_CONFIRMATION tells the confirmation utility to expect
        # confirmations via the API (/confirm endpoint) rather than CLI input.
        os.environ["SCRAPPY_EXTERNAL_CONFIRMATION"] = "true"
        os.environ["SCRAPPY_LOCALE"] = locale # Pass locale for potential use in deeper modules.
        os.environ["TAX_YEAR"] = tax_year # Pass tax year for potential use in deeper modules.

        # Prepare list of owner names from the input string.
        input_names = [name.strip() for name in owners.split(";") if name.strip()]

        # Ensure session-specific output folders (e.g., for PDFs) are created.
        # This function is imported from main.py but ideally could be in a shared utils.
        get_session_folders(session_id)

        # --- Step 1: Scrape initial property data (list of properties) ---
        # This is a potentially long-running I/O-bound operation, so it's run in a thread pool.
        results = await asyncio.to_thread(
            scrape_property_data, # The core function from property_scraper.py
            input_names,
            locale=locale,
            tax_year=tax_year
        )
        logger.info(f"Found {len(results)} initial property results for session {session_id}.")

        # --- Step 2: Enrich each property with detailed information ---
        # Iterate through the initial results and fetch more details for each property.
        for property_item in results:
            detail_link = property_item.get("Link") # Assumes "Link" key holds the URL to the detail page.
            if detail_link:
                try:
                    # Fetch details, also an I/O-bound operation.
                    details = await asyncio.to_thread(scrape_details, detail_link, tax_year)
                    property_item.update(details) # Merge detailed data into the property_item dictionary.
                    logger.info(f"Fetched details for '{property_item.get('Matched Name', 'Unknown Property')}' (Account: {property_item.get('Account', 'N/A')}) in session {session_id}")
                except Exception as detail_exc:
                    # Log errors during detail scraping but continue with other properties.
                    logger.error(f"Error fetching details for link {detail_link} in session {session_id}: {detail_exc}", exc_info=True)
            else:
                logger.warning(f"No detail link found for property '{property_item.get('Matched Name', 'Unknown Property')}' in session {session_id}.")

        logger.info(f"Completed detail fetching for session {session_id}. Total properties processed: {len(results)}.")

        # TODO: Persist enriched `results` to a database or file system.
        # Currently, results are only held in memory for the duration of this task.
        # For a production system, one would typically write these to a persistent store
        # and update a status record for the session_id indicating completion or errors.

    except Exception as e:
        # Catch-all for any unhandled exceptions during the entire background task.
        logger.error(f"Critical error in background scraping task for session {session_id}: {e}", exc_info=True)
        # Optionally, update a session status in a database to reflect the failure.

@app.post("/scrape")
async def scrape(request: ScrapeRequest, background_tasks: BackgroundTasks):
    """
    Initiates a property scraping job.
    It validates the request, generates a session ID if one is not provided,
    and schedules the actual scraping process (`process_scraping`) to run in the background.
    This ensures the API returns quickly to the client without waiting for the scrape to complete.

    Args:
        request (ScrapeRequest): Validated request data containing owners, locale, and tax year.
        background_tasks (BackgroundTasks): FastAPI dependency to schedule background tasks.
    """
    try:
        logger.info(f"[{VERSION}] Received /scrape request: Session: {request.session_id}, Locale: {request.locale}, Year: {request.tax_year}, Owners: {request.owners[:100]}...")

        # Use the provided session_id or generate a new one if not supplied.
        # This allows clients to potentially resume or group operations under one session.
        session_id = request.session_id # FastAPI ensures this is present due to Pydantic model

        logger.info(f"Processing /scrape request with session ID: {session_id}")

        # Create session-specific directories for outputs (e.g., PDFs, logs).
        # This helps organize files per scraping job.
        session_folder, pdf_folder = get_session_folders(session_id)

        # Schedule the `process_scraping` function to run in the background.
        # This allows the API to respond immediately while the scraping happens asynchronously.
        background_tasks.add_task(
            process_scraping, # The function to run.
            session_id=session_id,  # Arguments passed to process_scraping.
            owners=request.owners,
            locale=request.locale,
            tax_year=request.tax_year
        )

        # Return an immediate response to the client indicating the job has started.
        return {
            "status": "success",
            "message": "Scraping job successfully initiated.",
            "session_id": session_id, # Return the session_id for client tracking.
            "data": { # Echo back the main parameters of the request.
                "owners": request.owners,
                "locale": request.locale,
                "tax_year": request.tax_year
            }
        }

    except HTTPException: # Re-raise HTTPException directly if it's already handled (e.g., validation error).
        raise
    except Exception as e:
        # Catch any other unexpected errors during request handling.
        sid_for_log = request.session_id if request and hasattr(request, 'session_id') and request.session_id else "N/A"
        logger.error(f"[{VERSION}] Critical error during /scrape request initiation for session {sid_for_log}: {e}", exc_info=True)
        # Provide a generic error message to the client.
        detail_message = f"An unexpected server error occurred while initiating the scrape request. Please check server logs for session ID '{sid_for_log}' if provided, or contact support if the issue persists."
        raise HTTPException(status_code=500, detail=detail_message)

@app.get("/files/{session_id}")
async def get_session_files(session_id: str, page: int = 1, per_page: int = 50):
    """
    Retrieves a paginated list of PDF files generated for a given session_id.
    Files are expected to be stored in a session-specific subfolder within the 'data/outputs' directory,
    specifically in a 'pdfs' subfolder (e.g., 'data/outputs/{session_id}/pdfs/').

    Args:
        session_id (str): The ID of the session for which to list files.
        page (int): The page number for pagination (1-indexed).
        per_page (int): The number of files to list per page.
    """
    try:
        # Determine the session's main folder and the specific PDF folder path.
        session_folder, pdf_folder = get_session_folders(session_id)

        # Handle cases where the PDF folder might not exist (e.g., no PDFs generated yet).
        if not os.path.exists(pdf_folder):
            return {
                "session_id": session_id,
                "files": [], # Return an empty list if no PDF folder.
                "file_count": 0,
                "pagination": { # Standard pagination details.
                    "page": page,
                    "per_page": per_page,
                    "total": 0,
                    "pages": 0,
                    "has_next": False,
                    "has_prev": False
                }
            }

        # List all files in the PDF directory.
        all_files = [f for f in os.listdir(pdf_folder) if os.path.isfile(os.path.join(pdf_folder, f)) and f.lower().endswith('.pdf')]
        total_files = len(all_files)

        # Calculate total pages. Ensures at least 1 page even if no files.
        total_pages = (total_files + per_page - 1) // per_page if total_files > 0 else 1

        # Validate and adjust the requested page number to be within valid range.
        page = max(1, min(page, total_pages))

        # Calculate start and end indices for slicing the list of files for the current page.
        start_idx = (page - 1) * per_page
        end_idx = min(start_idx + per_page, total_files)
        paginated_files = all_files[start_idx:end_idx] # Get the slice of files for the current page.

        return {
            "session_id": session_id,
            "files": paginated_files, # The list of PDF filenames for the current page.
            "file_count": total_files, # Total number of PDF files found.
            "pagination": {
                "page": page, # Current page number.
                "per_page": per_page, # Files per page.
                "total": total_files, # Total number of files across all pages.
                "pages": total_pages, # Total number of pages.
                "has_next": page < total_pages, # Boolean indicating if there's a next page.
                "has_prev": page > 1  # Boolean indicating if there's a previous page.
            }
        }
    except Exception as e:
        # Log the full error for server-side debugging.
        logger.error(f"Error retrieving file list for session {session_id}: {e}", exc_info=True)
        # Return a generic error to the client.
        raise HTTPException(status_code=500, detail=f"An error occurred while retrieving files for session {session_id}.")

# --- Main Application Runner ---
# This block allows running the FastAPI application directly using Uvicorn,
# typically for development or simple deployments.
if __name__ == "__main__":
    # Get port from environment variable 'PORT', defaulting to 8080 if not set.
    # Useful for cloud environments like Google Cloud Run, Heroku, etc.
    port = int(os.getenv('PORT', 8080))

    # Run the Uvicorn ASGI server.
    # host="0.0.0.0" makes the server accessible externally (not just localhost).
    # log_level="info" sets Uvicorn's logging verbosity.
    uvicorn.run(
        app, # The FastAPI application instance.
        host="0.0.0.0",
        port=port,
        log_level="info" # Uvicorn's own log level.
    )
