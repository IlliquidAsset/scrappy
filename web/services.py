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
            # Use transaction to ensure data consistency
            db.session.begin_nested()
            
            # Check if session already exists
            existing_job = ScrapingJob.query.filter_by(session_id=session_id).first()
            if existing_job:
                db.session.commit()
                return existing_job

            # Create job record
            job = ScrapingJob(
                session_id=session_id,
                owner_names=owner_names,
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
                "owners": owner_names[0] if isinstance(owner_names, list) else owner_names,
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
                
                # Start background thread to poll for job status
                thread = threading.Thread(
                    target=ScrappyService._poll_job_status,
                    args=(job.id, session_id)
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
            try:
                db.session.rollback()
                if 'job' in locals():
                    job.status = 'failed'
                    job.error_message = str(e)
                    db.session.commit()
            except:
                pass  # If we can't even update the job status, just continue
            raise

    @staticmethod
    def _poll_job_status(job_id, session_id, max_attempts=30):
        """
        Background task to poll for job status updates
        
        Args:
            job_id (int): Job ID to poll
            session_id (str): Session ID to query
            max_attempts (int): Maximum number of status check attempts
        """
        logger.debug(f"Starting status polling for job {job_id}")
        
        interval = current_app.config.get('SCRAPPY_STATUS_CHECK_INTERVAL', 5)
        attempts = 0
        
        # Get application context
        with current_app.app_context():
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
                    
                    # Check status from API
                    api_url = f"{current_app.config['SCRAPPY_API_URL']}/files/{session_id}"
                    response = requests.get(api_url, timeout=5)
                    
                    if response.status_code != 200:
                        logger.warning(f"Failed to check status for job {job_id}: HTTP {response.status_code}")
                        continue
                    
                    data = response.json()
                    
                    # Update job last status check time
                    job.last_status_check = datetime.utcnow()
                    
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
                    
                except Exception as e:
                    logger.error(f"Error polling status for job {job_id}: {str(e)}", exc_info=True)
                
                # Sleep before next attempt
                import time
                time.sleep(interval)
            
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
        # In a real implementation, this would parse the files or get result data
        # from the Scrappy API and create ScrapingResult records
        
        # For now, we'll create a sample result record
        try:
            result = ScrapingResult(
                job_id=job.id,
                owner_name=job.owner_names[0] if isinstance(job.owner_names, list) else job.owner_names,
                property_address="123 Main St",
                parcel_id="123-456-789",
                land_value=500000.0,
                improvement_value=1000000.0,
                total_value=1500000.0,
                tax_rate="3.788",
                pdf_url=f"{current_app.config['SCRAPPY_API_URL']}/pdf/{job.session_id}/tax_bill.pdf",
                raw_data=data
            )
            db.session.add(result)
            db.session.commit()
            
            logger.info(f"Created result record for job {job.id}")
        except Exception as e:
            logger.error(f"Error creating result record for job {job.id}: {str(e)}", exc_info=True)
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
            db.session.commit()

            # Check for pending confirmation
            if job.status == 'confirmation_required':
                confirmation = ScrapingConfirmation.query.filter_by(
                    job_id=job.id,
                    response=None
                ).order_by(ScrapingConfirmation.created_at.desc()).first()
                
                if confirmation:
                    return {
                        'status': 'confirmation_required',
                        'owner': confirmation.owner_name,
                        'match': confirmation.matched_name,
                        'confirmation_id': confirmation.id,
                        'results': []
                    }

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
                
                # Start background thread to poll for job status
                thread = threading.Thread(
                    target=ScrappyService._poll_job_status,
                    args=(job.id, session_id)
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