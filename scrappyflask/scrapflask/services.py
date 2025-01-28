"""Services for ScrapFlask"""
import os
import uuid
from datetime import datetime
from flask import current_app
import requests
from sqlalchemy.exc import IntegrityError
from scrapflask.models import db, ScrapingJob, ScrapingResult, ScrapingConfirmation
import logging

class ScrappyService:
    """Service for interacting with the Scrappy API"""

    @staticmethod
    def create_scraping_job(owner_names, locale, tax_year, session_id=None):
        """Create a new scraping job"""
        if not session_id:
            session_id = str(uuid.uuid4())

        current_app.logger.debug(f"Creating new job with session_id: {session_id}")

        try:
            # Check if session already exists
            existing_job = ScrapingJob.query.filter_by(session_id=session_id).first()
            if existing_job:
                return existing_job

            # Create job record
            job = ScrapingJob(
                session_id=session_id,
                owner_names=owner_names,
                locale=locale,
                tax_year=tax_year,
                status='running'
            )
            db.session.add(job)
            db.session.commit()

            current_app.logger.debug(f"Created job record with ID: {job.id}")

            # Prepare the request to Scrappy API
            api_url = f"{current_app.config['SCRAPPY_API_URL']}/scrape"
            payload = {
                "session_id": session_id,
                "owners": owner_names[0] if isinstance(owner_names, list) else owner_names,
                "locale": locale,
                "tax_year": tax_year
            }

            # Make the API request
            current_app.logger.debug(f"Calling Scrappy API with payload: {payload}")
            response = requests.post(api_url, json=payload)
            response.raise_for_status()

            # Process API response
            data = response.json()
            current_app.logger.debug(f"Received API response: {data}")

            # Handle confirmation required status
            if data.get("status") == "confirmation_required":
                job.status = "confirmation_required"
                db.session.commit()

                # Create confirmation record
                confirmation = ScrapingConfirmation(
                    id=str(uuid.uuid4()),
                    job_id=job.id,
                    session_id=session_id,
                    owner_name=data.get("owner", ""),
                    matched_name=data.get("match", "")
                )
                db.session.add(confirmation)
                db.session.commit()

                current_app.logger.info(f"Created confirmation request for job {job.id}")
                return job

            elif data.get("status") == "success":
                current_app.logger.info(f"Successfully started scraping job with session_id: {session_id}")
                return job
            else:
                error_msg = data.get('error') or data.get('message') or data.get('error_message', "Unknown error")
                error_details = f"Response data: {data}"
                if error_msg:
                    error_details = f"{error_msg}. {error_details}"
                raise Exception(f"Scrappy API error: {error_details}")

        except IntegrityError as e:
            current_app.logger.error(f"Database integrity error: {str(e)}", exc_info=True)
            db.session.rollback()
            # Try to return existing job if it was a duplicate session
            return ScrapingJob.query.filter_by(session_id=session_id).first()
        except requests.exceptions.RequestException as e:
            current_app.logger.error(f"API request error: {str(e)}", exc_info=True)
            if 'job' in locals():
                job.status = 'failed'
                job.error_message = f"API request failed: {str(e)}"
                db.session.commit()
            raise
        except Exception as e:
            current_app.logger.error(f"Error during job creation: {str(e)}", exc_info=True)
            if 'job' in locals():
                job.status = 'failed'
                job.error_message = str(e)
                db.session.commit()
            raise

    @staticmethod
    def check_job_status(job):
        """Check job status and return results"""
        try:
            # Query for results
            results = ScrapingResult.query.filter_by(job_id=job.id).all()

            # Update last status check timestamp
            job.last_status_check = datetime.utcnow()
            db.session.commit()

            data = {
                'status': job.status,
                'error_message': job.error_message if job.status == 'failed' else None,
                'results': [{
                    'matched_name': result.owner_name,
                    'address': result.property_address,
                    'parcel': result.parcel_id,
                    'land_value': result.land_value,
                    'improvement_value': result.improvement_value,
                    'total_value': result.total_value,
                    'tax_rate': result.tax_rate,
                    'pdf_url': result.pdf_url,
                    'id': str(result.id)
                } for result in results]
            }

            return data

        except Exception as e:
            current_app.logger.error(f"Error checking job status: {e}", exc_info=True)
            return None

    @staticmethod
    def send_confirmation(job_id, session_id, confirmation):
        """Send confirmation response"""
        try:
            api_url = f"{current_app.config['SCRAPPY_API_URL']}/confirm"
            payload = {
                "session_id": session_id,
                "confirmation": confirmation
            }

            response = requests.post(api_url, json=payload)
            response.raise_for_status()

            # Update confirmation record
            confirmation_record = ScrapingConfirmation.query.filter_by(
                job_id=job_id,
                session_id=session_id,
                response=None
            ).first()

            if confirmation_record:
                confirmation_record.response = confirmation
                db.session.commit()

            return True

        except Exception as e:
            current_app.logger.error(f"Error sending confirmation: {e}", exc_info=True)
            return False