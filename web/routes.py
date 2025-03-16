"""Routes for the Flask application"""
import os
import sys
import json
from datetime import datetime
from flask import Blueprint, jsonify, request, render_template, send_file, current_app
from werkzeug.utils import secure_filename
from web.models import db, ScrapingJob, ScrapingResult, ScrapingConfirmation
from web.services import ScrappyService
import requests
import logging
import uuid

# Configure logging
logging.basicConfig(level=logging.DEBUG)
logger = logging.getLogger(__name__)

bp = Blueprint('scraper', __name__)

@bp.route('/scrape', methods=['POST'])
def create_scraping_job():
    """Create a new scraping job with the provided session ID"""
    try:
        data = request.get_json()
        if not data:
            return jsonify({'error': 'Missing request data'}), 400

        required_fields = ['session_id', 'owners', 'locale']
        missing_fields = [field for field in required_fields if field not in data]
        if missing_fields:
            return jsonify({'error': f'Missing required fields: {", ".join(missing_fields)}'}), 400

        # Convert single owner string to list for consistency
        owner_names = [data['owners']] if isinstance(data['owners'], str) else data['owners']

        logger.info(f"Creating job for owners: {owner_names} with session_id: {data['session_id']}")

        # Create job with the provided session ID
        job = ScrappyService.create_scraping_job(
            owner_names=owner_names,
            locale=data.get('locale', 'davidson-tn'),
            tax_year=data.get('tax_year', '2024'),
            session_id=data['session_id']
        )

        return jsonify({
            'status': 'success',
            'job_id': job.id,
            'session_id': job.session_id
        })

    except Exception as e:
        logger.error(f"Error creating job: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.route('/')
def index():
    """Render the main page"""
    try:
        # Get supported locales from Scrappy API
        api_url = f"{current_app.config['SCRAPPY_API_URL']}/locales"
        logger.info(f"Requesting locales from: {api_url}")

        response = requests.get(api_url, timeout=current_app.config['SCRAPPY_API_TIMEOUT'])
        response.raise_for_status()
        data = response.json()

        logger.debug(f"Received locales response: {data}")  # Log the actual response

        # Handle different possible response formats
        if isinstance(data, dict):
            if 'locales' in data and isinstance(data['locales'], dict):
                locales = data['locales']  # If response is {"locales": {...}}
            elif all(isinstance(v, str) for v in data.values()):
                locales = data  # If response is {code: name} format
            else:
                logger.warning(f"Unexpected data structure in API response: {data}")
                locales = {'davidson-tn': 'Nashville/Davidson County, TN'}
        else:
            logger.error(f"Unexpected response type: {type(data)}, content: {data}")
            raise ValueError(f"Unexpected response format: {data}")

        logger.info(f"Successfully loaded {len(locales)} locales: {locales}")
        return render_template('index.html', locales=locales)

    except requests.exceptions.RequestException as e:
        logger.error(f"Failed to fetch locales from API: {str(e)}", exc_info=True)
        # Fallback to default locale
        default_locales = {
            'davidson-tn': 'Nashville/Davidson County, TN',
        }
        return render_template('index.html',
                             locales=default_locales,
                             error="Unable to load all locations. Showing default options.")
    except Exception as e:
        logger.error(f"Unexpected error fetching locales: {str(e)}", exc_info=True)
        return render_template('index.html',
                             error="Unable to load locations. Please try again later.",
                             locales={'davidson-tn': 'Nashville/Davidson County, TN'})

@bp.route('/api/jobs/<int:job_id>/status', methods=['GET'])
def get_job_status(job_id):
    """Get job status and handle confirmation directly from DB and API logs"""
    try:
        job = ScrapingJob.query.get_or_404(job_id)

        # First, check if there are any pending confirmations in our database
        pending_confirmation = ScrapingConfirmation.query.filter_by(
            job_id=job_id,
            response=None
        ).order_by(ScrapingConfirmation.created_at.desc()).first()

        # If pending confirmation exists, return it
        if pending_confirmation:
            logger.info(f"Found pending confirmation in database for job {job_id}")
            return jsonify({
                'status': 'confirmation_required',
                'owner': pending_confirmation.owner_name,
                'match': pending_confirmation.matched_name,
                'confirmation_id': pending_confirmation.id
            })

        # If job is already in confirmation_required state, check API directly
        api_url = f"{current_app.config['SCRAPPY_API_URL']}/files/{job.session_id}"

        # This special parameter tells the API we want status info too
        response = requests.get(f"{api_url}?include_status=true", timeout=5)

        if response.ok:
            data = response.json()

            # If API response has confirmation_required status, create a local record
            if data.get('status') == 'confirmation_required':
                logger.info(f"API reports confirmation_required for job {job_id}, creating local record")

                # Update job status
                job.status = 'confirmation_required'

                # Create confirmation record
                confirmation = ScrapingConfirmation(
                    id=data.get('confirmation_id', str(uuid.uuid4())),
                    job_id=job.id,
                    session_id=job.session_id,
                    owner_name=data.get('owner', ''),
                    matched_name=data.get('match', '')
                )
                db.session.add(confirmation)
                db.session.commit()

                return jsonify({
                    'status': 'confirmation_required',
                    'owner': data.get('owner'),
                    'match': data.get('match'),
                    'confirmation_id': data.get('confirmation_id')
                })

        # If no confirmation needed, return current job status
        return jsonify({
            'status': job.status,
            'message': 'Current job status',
        })

    except Exception as e:
        logger.error(f"Error checking job status: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500
    
@bp.route('/api/jobs/<int:job_id>', methods=['GET'])
def get_job(job_id):
    """Get job status and results"""
    page = request.args.get('page', 1, type=int)
    per_page = request.args.get('per_page', 10, type=int)

    try:
        job = ScrapingJob.query.get_or_404(job_id)

        # Check status with Scrappy API
        if job.status in ['pending', 'running']:
            status_data = ScrappyService.check_job_status(job)
            if not status_data:
                return jsonify({'error': 'Failed to check job status'}), 500

        # Get paginated results
        paginated_results = ScrapingResult.query.filter_by(job_id=job_id)\
            .order_by(ScrapingResult.created_at.desc())\
            .paginate(page=page, per_page=per_page, error_out=False)

        results = [{
            'owner_name': result.owner_name,
            'property_address': result.property_address,
            'parcel_id': result.parcel_id,
            'land_value': result.land_value,
            'improvement_value': result.improvement_value,
            'total_value': result.total_value,
            'tax_rate': result.tax_rate,
            'pdf_url': result.pdf_url,
            'created_at': result.created_at.isoformat()
        } for result in paginated_results.items]

        logger.debug(f"Returning {len(results)} results for job {job_id}")

        return jsonify({
            'job_id': job.id,
            'status': job.status,
            'created_at': job.created_at.isoformat(),
            'completed_at': job.completed_at.isoformat() if job.completed_at else None,
            'error_message': job.error_message,
            'results': results,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': paginated_results.total,
                'pages': paginated_results.pages,
                'has_next': paginated_results.has_next,
                'has_prev': paginated_results.has_prev
            }
        })

    except Exception as e:
        logger.error(f"Error getting job {job_id}: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.route('/api/jobs/<int:job_id>/confirm', methods=['POST'])
def confirm_match(job_id):
    """Handle property match confirmation"""
    data = request.get_json()
    if not data or 'confirmation' not in data:
        return jsonify({'error': 'Missing confirmation data'}), 400

    try:
        job = ScrapingJob.query.get_or_404(job_id)

        # Log the confirmation attempt
        confirmation_id = data.get('confirmation_id')
        logger.info(f"Received confirmation {data['confirmation']} for job {job_id}, confirmation ID: {confirmation_id}")

        # Store confirmation in our database first
        if confirmation_id:
            confirmation = ScrapingConfirmation.query.filter_by(id=confirmation_id).first()
            if confirmation:
                confirmation.response = data['confirmation']
                db.session.commit()
                logger.info(f"Updated local confirmation record {confirmation_id} with response: {data['confirmation']}")

        # Send confirmation to Scrappy API
        if ScrappyService.send_confirmation(job.id, job.session_id, data['confirmation']):
            return jsonify({'message': 'Confirmation sent', 'status': 'success'})
        return jsonify({'error': 'Failed to send confirmation'}), 500
    except Exception as e:
        logger.error(f"Error confirming match: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.route('/api/jobs/<int:job_id>/download/<string:format>', methods=['GET'])
def download_results(job_id, format):
    """Download job results in various formats"""
    try:
        job = ScrapingJob.query.get_or_404(job_id)

        if job.status != 'completed':
            return jsonify({'error': 'Job not completed'}), 400

        if format == 'excel':
            response = requests.get(
                f"{current_app.config['SCRAPPY_API_URL']}/files/{job.session_id}/excel",
                stream=True
            )
            response.raise_for_status()

            return send_file(
                response.raw,
                mimetype='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet',
                as_attachment=True,
                download_name=f'property_data_{job_id}.xlsx'
            )

        elif format == 'pdfs':
            response = requests.get(
                f"{current_app.config['SCRAPPY_API_URL']}/files/{job.session_id}/pdfs",
                stream=True
            )
            response.raise_for_status()

            return send_file(
                response.raw,
                mimetype='application/zip',
                as_attachment=True,
                download_name=f'property_pdfs_{job_id}.zip'
            )

        return jsonify({'error': 'Invalid format'}), 400

    except Exception as e:
        logger.error(f"Error downloading results: {e}", exc_info=True)
        return jsonify({'error': str(e)}), 500

@bp.errorhandler(404)
def not_found(e):
    """Handle 404 errors"""
    return jsonify({'error': 'Not found'}), 404

@bp.errorhandler(500)
def server_error(e):
    """Handle 500 errors"""
    return jsonify({'error': 'Internal server error'}), 500
