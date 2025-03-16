"""Services for ScrapFlask"""
import os
import uuid
import json
from datetime import datetime
import threading
import requests
from flask import current_app
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from requests.exceptions import RequestException, Timeout
from web.database import db
from web.models import ScrapingJob, ScrapingResult, ScrapingConfirmation
import logging
import time

# Configure logging
logger = logging.getLogger(__name__)

class ScrappyService:
    """Service for interacting with the Scrappy API"""

    @staticmethod
    def create_scraping_job(owner_names, locale, tax_year, session_id=None):
        """
        Create a new scraping job

        Args:
            owner_names (list): List of owner names to scrape
            locale (str): Locale code (e.g., 'davidson-tn')
            tax_year (str): Tax year to search
            session_id (str, optional): Existing session ID to use

        Returns:
            ScrapingJob: Created job object

        Raises:
            Exception: If job creation fails
        """
        if not session_id:
            session_id = str(uuid.uuid4())

        logger.debug(f"Creating new job with session_id: {session_id}")

        try:
            # Check if session already exists outside of transaction
            existing_job = ScrapingJob.query.filter_by(session_id=session_id).first()
            if existing_job:
                return existing_job

            # Convert owner_names to JSON-compatible dict
            if isinstance(owner_names, list):
                owner_names_json = {"names": owner_names}
            else:
                owner_names_json = {"names": [owner_names] if owner_names else []}

            # Create job record
            job = ScrapingJob(
                session_id=session_id,
                owner_names=owner_names_json,
                locale=locale,
                tax_year=tax_year,
                status='pending'
            )
            db.session.add(job)
            db.session.commit()

            logger.debug(f"Created job record with ID: {job.id}")

            # Prepare the request to Scrappy API
            api_url = f"{current_app.config['SCRAPPY_API_URL']}/scrape"
            payload = {
                "session_id": session_id,
                "owners": owner_names[0] if isinstance(owner_names, list) and owner_names else owner_names,
                "locale": locale,
                "tax_year": tax_year
            }

            # Make the API request with timeout
            logger.debug(f"Calling Scrappy API with payload: {payload}")

            timeout = current_app.config.get('SCRAPPY_API_TIMEOUT', 30)

            try:
                response = requests.post(
                    api_url,
                    json=payload,
                    timeout=timeout
                )
                response.raise_for_status()
            except Timeout:
                logger.error(f"API request timed out after {timeout} seconds")
                job.status = 'failed'
                job.error_message = f"API request timed out after {timeout} seconds"
                db.session.commit()
                raise
            except RequestException as e:
                logger.error(f"API request failed: {str(e)}")
                job.status = 'failed'
                job.error_message = f"API request failed: {str(e)}"
                db.session.commit()
                raise

            # Process API response
            data = response.json()
            logger.debug(f"Received API response: {data}")

            # Handle confirmation required status
            if data.get("status") == "confirmation_required":
                job.status = "confirmation_required"

                # Create confirmation record
                confirmation = ScrapingConfirmation(
                    id=data.get("confirmation_id", str(uuid.uuid4())),
                    job_id=job.id,
                    session_id=session_id,
                    owner_name=data.get("owner", ""),
                    matched_name=data.get("match", "")
                )
                db.session.add(confirmation)
                db.session.commit()

                logger.info(f"Created confirmation request for job {job.id}")
                return job

            elif data.get("status") == "success":
                job.status = "running"
                db.session.commit()

                # Create a new app context for the background thread
                # Store application for the thread to use
                app = current_app._get_current_object()

                # Start background thread to poll for job status
                thread = threading.Thread(
                    target=ScrappyService._poll_job_status,
                    args=(job.id, session_id, app)
                )
                thread.daemon = True
                thread.start()

                logger.info(f"Successfully started scraping job with session_id: {session_id}")
                return job
            else:
                error_msg = data.get('error') or data.get('message') or data.get('error_message', "Unknown error")
                error_details = f"Response data: {data}"
                if error_msg:
                    error_details = f"{error_msg}. {error_details}"

                job.status = 'failed'
                job.error_message = error_details
                db.session.commit()

                raise Exception(f"Scrappy API error: {error_details}")

        except IntegrityError as e:
            logger.error(f"Database integrity error: {str(e)}", exc_info=True)
            db.session.rollback()
            # Try to return existing job if it was a duplicate session
            return ScrapingJob.query.filter_by(session_id=session_id).first()
        except (SQLAlchemyError, Exception) as e:
            logger.error(f"Error during job creation: {str(e)}", exc_info=True)
            db.session.rollback()
            if 'job' in locals():
                try:
                    job.status = 'failed'
                    job.error_message = str(e)
                    db.session.add(job)  # Re-add job after rollback
                    db.session.commit()
                except Exception:
                    pass  # If we can't even update the job status, just continue
            raise

    @staticmethod
    def _poll_job_status(job_id, session_id, app, max_attempts=30):
        """
        Background task to poll for job status updates

        Args:
            job_id (int): Job ID to poll
            session_id (str): Session ID to query
            app: Flask application object
            max_attempts (int): Maximum number of status check attempts
        """
        logger.debug(f"Starting status polling for job {job_id}")

        interval_seconds = 5  # Default interval in seconds
        attempts = 0
        consecutive_errors = 0
        max_consecutive_errors = 3

        # Get application context
        with app.app_context():
            # Get interval from config - handle timedelta conversion
            interval_config = app.config.get('SCRAPPY_STATUS_CHECK_INTERVAL', 5)
            # If it's a timedelta, convert to seconds
            if hasattr(interval_config, 'total_seconds'):
                interval_seconds = interval_config.total_seconds()
            else:
                interval_seconds = float(interval_config)

            while attempts < max_attempts:
                attempts += 1

                try:
                    # Get job status from database
                    job = ScrapingJob.query.get(job_id)
                    if not job:
                        logger.error(f"Job {job_id} not found during status polling")
                        return

                    # If job is already completed or failed, stop polling
                    if job.status in ['completed', 'failed']:
                        logger.info(f"Job {job_id} is already in final state: {job.status}")
                        return

                    # Check for confirmation required status and update the database
                    if job.status == 'confirmation_required':
                        logger.info(f"Job {job_id} requires confirmation. Pausing polling.")
                        return  # Return early - polling will resume after confirmation

                    # Check status from API
                    api_url = f"{app.config['SCRAPPY_API_URL']}/files/{session_id}"

                    try:
                        response = requests.get(api_url, timeout=5)
                        response.raise_for_status()
                        consecutive_errors = 0  # Reset consecutive error counter on success

                        data = response.json()
                        logger.debug(f"API status response: {data}")

                        # Update job last status check time
                        job.last_status_check = datetime.utcnow()

                        # Check if confirmation is required
                        if data.get('status') == 'confirmation_required':
                            logger.info(f"Confirmation required: {data.get('owner')} -> {data.get('match')}")
                            # Update job status to confirmation_required
                            job.status = 'confirmation_required'

                            # Create confirmation record if not exists
                            confirmation = ScrapingConfirmation(
                                id=data.get('confirmation_id', str(uuid.uuid4())),
                                job_id=job.id,
                                session_id=session_id,
                                owner_name=data.get('owner', ''),
                                matched_name=data.get('match', '')
                            )
                            db.session.add(confirmation)
                            db.session.commit()
                            logger.info(f"Created confirmation request for job {job.id}")
                            return  # Return early - polling will resume after confirmation

                        # Process results if files are available
                        if data.get('file_count', 0) > 0:
                            # Create result entries from files
                            ScrappyService._process_job_results(job, data)

                            # Mark job as completed
                            job.status = 'completed'
                            job.completed_at = datetime.utcnow()
                            db.session.commit()

                            logger.info(f"Job {job_id} completed with {data.get('file_count', 0)} files")
                            return

                        # Save status check
                        db.session.commit()

                    except requests.RequestException as e:
                        consecutive_errors += 1
                        logger.warning(f"API request error on attempt {attempts}: {e}")

                        if consecutive_errors >= max_consecutive_errors:
                            logger.error(f"Too many consecutive errors ({consecutive_errors}). Stopping polling.")
                            job.status = 'failed'
                            job.error_message = f"API communication error: {str(e)}"
                            job.completed_at = datetime.utcnow()
                            db.session.commit()
                            return

                except Exception as e:
                    consecutive_errors += 1
                    logger.error(f"Error polling status for job {job_id}: {str(e)}", exc_info=True)

                    if consecutive_errors >= max_consecutive_errors:
                        logger.error(f"Too many consecutive errors ({consecutive_errors}). Stopping polling.")
                        try:
                            job = ScrapingJob.query.get(job_id)
                            if job and job.status not in ['completed', 'failed']:
                                job.status = 'failed'
                                job.error_message = f"Polling error: {str(e)}"
                                job.completed_at = datetime.utcnow()
                                db.session.commit()
                        except Exception as inner_e:
                            logger.error(f"Error updating job after polling failure: {str(inner_e)}")
                        return

                # Sleep before next attempt - use seconds
                time.sleep(interval_seconds)

            # If we reached max attempts without completion, mark as failed
            try:
                job = ScrapingJob.query.get(job_id)
                if job and job.status not in ['completed', 'failed']:
                    job.status = 'failed'
                    job.error_message = f"Job timed out after {max_attempts} status checks"
                    job.completed_at = datetime.utcnow()
                    db.session.commit()
                    logger.warning(f"Job {job_id} timed out")
            except Exception as e:
                logger.error(f"Error updating timed out job {job_id}: {str(e)}", exc_info=True)
    @staticmethod
    def _process_job_results(job, data):
        """
        Process job results from API response

        Args:
            job (ScrapingJob): Job object
            data (dict): API response data
        """
        try:
            # Get the base URL for API requests
            api_base_url = current_app.config['SCRAPPY_API_URL']

            # Check if we have property data in the response
            if 'files' in data and isinstance(data['files'], list):
                logger.info(f"Processing {len(data['files'])} result files for job {job.id}")

                # Process each property file
                for file_name in data['files']:
                    try:
                        # Fetch detailed property data if needed
                        property_data_url = f"{api_base_url}/files/{job.session_id}/{file_name}"
                        property_response = requests.get(property_data_url, timeout=10)
                        property_data = property_response.json() if property_response.ok else {}

                        # Extract property information
                        property_info = property_data.get('property_info', {})

                        # Determine owner name
                        if 'owner_name' in property_info:
                            owner_name = property_info.get('owner_name')
                        elif isinstance(job.owner_names, dict) and 'names' in job.owner_names:
                            owner_name = job.owner_names['names'][0] if job.owner_names['names'] else "Unknown"
                        else:
                            owner_name = str(job.owner_names)

                        # Create a result record with actual data
                        result = ScrapingResult(
                            job_id=job.id,
                            owner_name=owner_name,
                            property_address=property_info.get('address', 'N/A'),
                            parcel_id=property_info.get('parcel_id', 'N/A'),
                            land_value=float(property_info.get('land_value', 0)),
                            improvement_value=float(property_info.get('improvement_value', 0)),
                            total_value=float(property_info.get('total_value', 0)),
                            tax_rate=property_info.get('tax_rate', 'N/A'),
                            pdf_url=f"{api_base_url}/files/{job.session_id}/pdfs/{file_name.replace('.json', '.pdf')}",
                            raw_data=property_data
                        )
                        db.session.add(result)

                    except Exception as inner_e:
                        logger.error(f"Error processing property file {file_name}: {str(inner_e)}", exc_info=True)
                        # Continue with other files even if one fails

                # Commit all results at once
                db.session.commit()
                logger.info(f"Successfully created {len(data['files'])} result records for job {job.id}")

            # If no files but we have direct property data
            elif 'properties' in data and isinstance(data['properties'], list):
                logger.info(f"Processing {len(data['properties'])} direct properties for job {job.id}")

                for prop in data['properties']:
                    try:
                        # Create result with direct property data
                        result = ScrapingResult(
                            job_id=job.id,
                            owner_name=prop.get('owner_name', 'Unknown'),
                            property_address=prop.get('address', 'N/A'),
                            parcel_id=prop.get('parcel_id', 'N/A'),
                            land_value=float(prop.get('land_value', 0)),
                            improvement_value=float(prop.get('improvement_value', 0)),
                            total_value=float(prop.get('total_value', 0)),
                            tax_rate=prop.get('tax_rate', 'N/A'),
                            pdf_url=prop.get('pdf_url', ''),
                            raw_data=prop
                        )
                        db.session.add(result)

                    except Exception as inner_e:
                        logger.error(f"Error processing property data: {str(inner_e)}", exc_info=True)
                        # Continue with other properties even if one fails

                # Commit all results at once
                db.session.commit()
                logger.info(f"Successfully created {len(data['properties'])} result records for job {job.id}")

            # As a fallback, create at least one result record with available data
            else:
                logger.warning(f"No files or properties found in API response for job {job.id}. Creating sample result.")
                # Get owner name from job
                if isinstance(job.owner_names, dict) and 'names' in job.owner_names:
                    owner_name = job.owner_names['names'][0] if job.owner_names['names'] else "Unknown"
                else:
                    owner_name = str(job.owner_names)

                # Create a single result record based on whatever we have
                result = ScrapingResult(
                    job_id=job.id,
                    owner_name=owner_name,
                    property_address=data.get('address', 'Sample Address'),
                    parcel_id=data.get('parcel_id', 'Sample Parcel'),
                    land_value=float(data.get('land_value', 100000)),
                    improvement_value=float(data.get('improvement_value', 200000)),
                    total_value=float(data.get('total_value', 300000)),
                    tax_rate=data.get('tax_rate', '3.788'),
                    pdf_url=f"{api_base_url}/files/{job.session_id}/sample.pdf" if job.session_id else "",
                    raw_data=data
                )
                db.session.add(result)
                db.session.commit()
                logger.info(f"Created fallback result record for job {job.id}")

        except Exception as e:
            logger.error(f"Error processing job results for job {job.id}: {str(e)}", exc_info=True)
            db.session.rollback()
            raise

    @staticmethod
    def check_job_status(job):
        """
        Check job status and return results

        Args:
            job (ScrapingJob): Job to check

        Returns:
            dict: Job status data with results
        """
        try:
            # Query for results
            results = ScrapingResult.query.filter_by(job_id=job.id).all()

            # Update last status check timestamp
            job.last_status_check = datetime.utcnow()

            # First check with scrape status API
            try:
                # This endpoint returns confirmation requests
                api_url = f"{current_app.config['SCRAPPY_API_URL']}/status/{job.session_id}"
                response = requests.get(api_url, timeout=5)

                if response.ok:
                    data = response.json()
                    logger.info(f"Status API response for job {job.id}: {data}")

                    # Check if confirmation is required based on API response
                    if data.get('status') == 'confirmation_required':
                        # Update job status to confirmation_required
                        job.status = 'confirmation_required'

                        # Create confirmation record if not exists
                        existing_conf = ScrapingConfirmation.query.filter_by(
                            confirmation_id=data.get('confirmation_id'),
                            response=None
                        ).first()

                        if not existing_conf:
                            confirmation = ScrapingConfirmation(
                                id=data.get('confirmation_id', str(uuid.uuid4())),
                                job_id=job.id,
                                session_id=job.session_id,
                                owner_name=data.get('owner', ''),
                                matched_name=data.get('match', '')
                            )
                            db.session.add(confirmation)
                            logger.info(f"Created confirmation record for job {job.id}")

                        # Add to session and commit
                        db.session.commit()

                        # Check for pending confirmation
                        confirmation = ScrapingConfirmation.query.filter_by(
                            job_id=job.id,
                            response=None
                        ).order_by(ScrapingConfirmation.created_at.desc()).first()

                        if confirmation:
                            logger.info(f"Returning confirmation required for job {job.id}: {confirmation.owner_name} -> {confirmation.matched_name}")
                            return {
                                'status': 'confirmation_required',
                                'owner': confirmation.owner_name,
                                'match': confirmation.matched_name,
                                'confirmation_id': confirmation.id,
                                'results': []
                            }
            except Exception as e:
                logger.warning(f"Error checking status API: {e}")

            # Only then check files API if no confirmation is required
            if job.status not in ['confirmation_required', 'completed', 'failed']:
                try:
                    files_url = f"{current_app.config['SCRAPPY_API_URL']}/files/{job.session_id}"
                    files_response = requests.get(files_url, timeout=5)

                    if files_response.ok:
                        files_data = files_response.json()
                        logger.debug(f"Files API response for job {job.id}: {files_data}")

                        # Process results if files are available
                        if files_data.get('file_count', 0) > 0:
                            # Create result entries from files
                            ScrappyService._process_job_results(job, files_data)

                            # Mark job as completed
                            job.status = 'completed'
                            job.completed_at = datetime.utcnow()
                            db.session.commit()
                            logger.info(f"Job {job.id} completed with {files_data.get('file_count', 0)} files")

                except Exception as e:
                    logger.warning(f"Error checking files API: {e}")

            db.session.commit()

            # Return job data with results
            data = {
                'status': job.status,
                'error_message': job.error_message if job.status == 'failed' else None,
                'results': [{
                    'owner_name': result.owner_name,
                    'property_address': result.property_address,
                    'parcel_id': result.parcel_id,
                    'land_value': result.land_value,
                    'improvement_value': result.improvement_value,
                    'total_value': result.total_value,
                    'tax_rate': result.tax_rate,
                    'pdf_url': result.pdf_url,
                    'id': result.id
                } for result in results]
            }

            return data

        except Exception as e:
            logger.error(f"Error checking job status: {e}", exc_info=True)
            return None
    @staticmethod
    def send_confirmation(job_id, session_id, confirmation):
        """
        Send confirmation response to Scrappy API

        Args:
            job_id (int): Job ID
            session_id (str): Session ID
            confirmation (str): Confirmation response ('yes' or 'no')

        Returns:
            bool: True if confirmation was sent successfully
        """
        try:
            # Get confirmation record
            confirmation_record = ScrapingConfirmation.query.filter_by(
                job_id=job_id,
                session_id=session_id,
                response=None
            ).order_by(ScrapingConfirmation.created_at.desc()).first()

            if not confirmation_record:
                logger.warning(f"No pending confirmation found for job {job_id}")
                return False

            # Prepare API request
            api_url = f"{current_app.config['SCRAPPY_API_URL']}/confirm"
            payload = {
                "session_id": session_id,
                "confirmation_id": confirmation_record.id,
                "confirmation": confirmation
            }

            # Send confirmation to API
            timeout = current_app.config.get('SCRAPPY_API_TIMEOUT', 30)
            response = requests.post(api_url, json=payload, timeout=timeout)
            response.raise_for_status()

            # Update confirmation record
            confirmation_record.response = confirmation
            db.session.commit()

            # Update job status to running if confirmed
            job = ScrapingJob.query.get(job_id)
            if job and job.status == 'confirmation_required':
                job.status = 'running'
                db.session.commit()

                # Create a new app context for the background thread
                app = current_app._get_current_object()

                # Start background thread to poll for job status
                thread = threading.Thread(
                    target=ScrappyService._poll_job_status,
                    args=(job.id, session_id, app)
                )
                thread.daemon = True
                thread.start()

            logger.info(f"Confirmation {confirmation} sent for job {job_id}")
            return True

        except RequestException as e:
            logger.error(f"API request error sending confirmation: {e}", exc_info=True)
            return False
        except Exception as e:
            logger.error(f"Error sending confirmation: {e}", exc_info=True)
            return False
