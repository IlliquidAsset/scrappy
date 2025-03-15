"""
Main module for Scrappy - Property Data Scraping Tool
"""
import os
import sys
import json
import time
import uuid
import logging
from typing import List, Dict, Any, Tuple, Optional
from pathlib import Path

# Ensure `scrappy` is in the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Import logging first to set up early
from utils.logging_setup import setup_logging

# Set up logging
logger = setup_logging("scrappy.main", os.environ.get('LOG_LEVEL', 'INFO'))

# Now import other modules
from scrapers.property_scraper import scrape_property_data
from scrapers.detail_scraper import scrape_details
from utils.session_cleaner import cleanup_old_sessions
import requests

def get_session_folders(session_id: Optional[str] = None) -> Tuple[str, str]:
    """
    Get or create session-specific output folders.
    
    Args:
        session_id (str, optional): Session ID for folder organization
        
    Returns:
        tuple: (session_folder_path, pdf_folder_path)
    """
    # Define base output folder
    OUTPUT_FOLDER = os.path.join(current_dir, 'data', 'outputs')
    os.makedirs(OUTPUT_FOLDER, exist_ok=True)
    
    if session_id:
        session_folder = os.path.join(OUTPUT_FOLDER, session_id)
        PDF_FOLDER = os.path.join(session_folder, "pdfs")
        os.makedirs(PDF_FOLDER, exist_ok=True)
        return session_folder, PDF_FOLDER
    else:
        # Default folders
        DEFAULT_PDF_FOLDER = os.path.join(OUTPUT_FOLDER, 'data', 'pdfs')
        os.makedirs(DEFAULT_PDF_FOLDER, exist_ok=True)
        return OUTPUT_FOLDER, DEFAULT_PDF_FOLDER

def download_pdf(link: str, pdf_folder: str, filename: str, current: int, total: int) -> Optional[str]:
    """
    Download PDF from the provided link.
    
    Args:
        link (str): URL to download PDF from
        pdf_folder (str): Folder to save PDF in
        filename (str): Filename for the PDF
        current (int): Current file number
        total (int): Total number of files
        
    Returns:
        str or None: Path to downloaded file or None if failed
    """
    if not link:
        logger.warning(f"Invalid PDF link for {filename}. Skipping.")
        return None

    try:
        response = requests.get(link, stream=True, timeout=30)
        if response.status_code == 200:
            file_path = os.path.join(pdf_folder, f"{filename}.pdf")
            with open(file_path, "wb") as pdf_file:
                for chunk in response.iter_content(chunk_size=1024):
                    pdf_file.write(chunk)
            logger.info(f"PDF {current} of {total} downloaded successfully: {file_path}")
            return file_path
        else:
            logger.error(f"Failed to download PDF. Status: {response.status_code}")
            return None
    except Exception as e:
        logger.error(f"Error downloading PDF: {e}")
        return None

def get_user_input() -> List[str]:
    """
    Get user input for owner names from environment or console.
    
    Returns:
        list: List of owner names
    """
    env_owners = os.getenv("SCRAPPY_OWNERS")
    if env_owners:
        return [name.strip() for name in env_owners.split(";") if name.strip()]
    
    raw_input = input("Enter owner names (semicolon-separated): ")
    return [name.strip() for name in raw_input.split(";") if name.strip()]

def select_locale_cli() -> str:
    """
    Interactive locale selection for CLI.
    
    Returns:
        str: Selected locale code
    """
    # Dynamically import to avoid circular references
    from locales import SUPPORTED_LOCALES
    
    # Check for environment variable first
    env_locale = os.getenv("SCRAPPY_LOCALE")
    if env_locale and env_locale in SUPPORTED_LOCALES:
        return env_locale
    
    locales = {index + 1: locale for index, locale in enumerate(SUPPORTED_LOCALES)}
    colors = ["green", "blue", "red", "cyan", "magenta"]

    print("Select a locale:")
    for num, (key, loc) in enumerate(locales.items(), start=1):
        color = colors[(num - 1) % len(colors)]
        try:
            from termcolor import colored
            print(f"{colored(num, color)}. {colored(loc, color)} - {SUPPORTED_LOCALES[loc]['name']}")
        except ImportError:
            print(f"{num}. {loc} - {SUPPORTED_LOCALES[loc]['name']}")

    while True:
        try:
            locale_choice = int(input("Select locale number: "))
            if locale_choice in locales:
                return locales[locale_choice]
            print("Invalid selection. Please choose a valid number.")
        except ValueError:
            print("Please enter a valid number.")

def main() -> Dict[str, Any]:
    """
    Main execution function with CLI interface.
    
    Returns:
        dict: Output data with results
    """
    try:
        # Set up session ID if provided in environment
        SESSION_ID = os.getenv("SCRAPPY_SESSION_ID", f"cli-{uuid.uuid4()}")
        OUTPUT_FOLDER, PDF_FOLDER = get_session_folders(SESSION_ID)
        
        # Clean up old sessions (older than 24 hours)
        cleanup_old_sessions(os.path.join(current_dir, 'data', 'outputs'))
        
        # Get locale and tax year
        locale = os.getenv("SCRAPPY_LOCALE") or select_locale_cli()
        tax_year = os.getenv("TAX_YEAR") or input("Enter the tax year (default: 2024): ").strip() or "2024"

        # Get input names
        input_names = get_user_input()
        if not input_names:
            logger.error("No owner names provided. Exiting.")
            return {"error": "No owner names provided"}

        logger.info(f"Starting scrape for {len(input_names)} owners in locale {locale} for tax year {tax_year}")
        
        # Scrape and process data
        property_data = scrape_property_data(input_names, locale=locale, tax_year=tax_year)
        
        if not property_data:
            logger.warning("No properties found matching the search criteria")
            return {"property_data": [], "message": "No properties found"}
            
        logger.info(f"Found {len(property_data)} properties")
        
        # Process each property
        for i, property in enumerate(property_data):
            # Log progress
            logger.info(f"Processing property {i+1} of {len(property_data)}: {property.get('Matched Name', 'Unknown')}")
            
            # Scrape details
            details = scrape_details(property["Link"])
            property.update(details)
            
            # Download PDF
            pdf_filename = f"{property.get('Parcel', 'Unknown').replace('/', '_')}_{property.get('Matched Name', 'Unknown').replace('/', '_')}"
            pdf_path = download_pdf(
                property.get("PDF Link"), 
                PDF_FOLDER, 
                pdf_filename, 
                i + 1, 
                len(property_data)
            )
            if pdf_path:
                property["PDF Path"] = pdf_path

        # Write outputs (importing here to avoid circular imports)
        from outputs.excel_writer import write_to_excel
        from utils.logger import log_errors
        
        excel_file_path = os.path.join(OUTPUT_FOLDER, "output.xlsx")
        write_to_excel(property_data, excel_file_path)

        error_log_path = os.path.join(OUTPUT_FOLDER, "errors.log")
        log_errors(property_data, error_log_path)

        # Prepare output data
        output_data = {
            "excel_file": excel_file_path,
            "pdf_folder": PDF_FOLDER,
            "property_data": property_data,
            "session_id": SESSION_ID,
            "errors": []
        }

        logger.info(f"Data written to {excel_file_path}")
        logger.info(f"PDFs saved to {PDF_FOLDER}")
        
        # Print output as JSON for potential API consumption
        if os.getenv("SCRAPPY_JSON_OUTPUT", "false").lower() == "true":
            print(json.dumps({
                "status": "success", 
                "session_id": SESSION_ID,
                "count": len(property_data),
                "excel_path": excel_file_path
            }))

        return output_data
        
    except Exception as e:
        logger.error(f"Error in main execution: {e}", exc_info=True)
        
        if os.getenv("SCRAPPY_JSON_OUTPUT", "false").lower() == "true":
            print(json.dumps({
                "status": "error",
                "error": str(e)
            }))
            
        return {"error": str(e)}

if __name__ == "__main__":
    main()