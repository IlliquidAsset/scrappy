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
from core.utils.logging_setup import setup_logging

# Set up logging
logger = setup_logging("scrappy.main", os.environ.get('LOG_LEVEL', 'INFO'))

# Now import other modules
from core.scrapers.property_scraper import scrape_property_data
from core.scrapers.detail_scraper import scrape_details
from core.utils.session_cleaner import cleanup_old_sessions
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
        with requests.get(link, stream=True, timeout=30) as response:
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
    from core.locales import SUPPORTED_LOCALES
    
    # Check for environment variable first
    env_locale = os.getenv("SCRAPPY_LOCALE")
    if env_locale and env_locale in SUPPORTED_LOCALES:
        logger.info(f"Using locale from SCRAPPY_LOCALE environment variable: {env_locale}")
        return env_locale
    
    # Prepare a list of (locale_code, display_name) for selection
    # Sort by display name for consistent ordering.
    available_locales = sorted(
        [(code, data['name']) for code, data in SUPPORTED_LOCALES.items()],
        key=lambda item: item[1]
    )

    cli_options = {index + 1: code for index, (code, _) in enumerate(available_locales)}
    colors = ["green", "blue", "red", "cyan", "magenta"] # For colored output if termcolor is available

    print("\nSelect a locale:")
    for num, (code, display_name) in enumerate(available_locales, start=1):
        color = colors[(num - 1) % len(colors)]
        try:
            from termcolor import colored
            print(f"{colored(str(num), color)}. {colored(display_name, color)}")
        except ImportError:
            print(f"{num}. {display_name}")

    while True:
        try:
            raw_choice = input("Select locale number: ")
            locale_choice_num = int(raw_choice)
            if locale_choice_num in cli_options:
                selected_locale_code = cli_options[locale_choice_num]
                logger.info(f"User selected locale: {SUPPORTED_LOCALES[selected_locale_code]['name']}")
                return selected_locale_code
            print(f"Invalid selection '{raw_choice}'. Please choose a valid number from the list.")
        except ValueError:
            print(f"Invalid input '{raw_choice}'. Please enter a number.")

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
        # Dynamically import SUPPORTED_LOCALES here if not already at top level,
        # to ensure it's fresh if changed during a long-running app (though less relevant for CLI).
        from core.locales import SUPPORTED_LOCALES

        locale_code = os.getenv("SCRAPPY_LOCALE") or select_locale_cli()

        if not locale_code or locale_code not in SUPPORTED_LOCALES:
            logger.error(f"Invalid locale code '{locale_code}' selected or no locale provided. Exiting.")
            return {"error": f"Invalid locale code: {locale_code}"}

        # Load county configuration from JSON file
        config_details = SUPPORTED_LOCALES[locale_code]
        config_file_path = config_details['config_path']
        try:
            with open(config_file_path, 'r', encoding='utf-8') as f: # Specify UTF-8 encoding
                county_config = json.load(f)
            logger.info(f"Successfully loaded configuration for {county_config.get('county_name', locale_code)} from {config_file_path}")
        except FileNotFoundError:
            logger.error(f"Configuration file not found: {config_file_path} for locale {locale_code}. Exiting.")
            return {"error": f"Config file not found for {locale_code}"}
        except json.JSONDecodeError:
            logger.error(f"Error decoding JSON from configuration file: {config_file_path}. Exiting.")
            return {"error": f"Invalid JSON in config for {locale_code}"}
        except Exception as e:
            logger.error(f"An unexpected error occurred while loading config file {config_file_path}: {e}", exc_info=True)
            return {"error": f"Failed to load config for {locale_code}"}


        tax_year = os.getenv("TAX_YEAR") or input(f"Enter the tax year for {county_config.get('county_name', locale_code)} (default: 2024): ").strip() or "2024"

        # Get input names
        input_names = get_user_input()
        if not input_names:
            logger.error("No owner names provided. Exiting.")
            return {"error": "No owner names provided"}

        logger.info(f"Starting scrape for {len(input_names)} owners in {county_config.get('county_name', locale_code)} for tax year {tax_year}")
        
        # Scrape and process data using county_config
        property_data = scrape_property_data(
            owner_names=input_names,
            county_config=county_config,
            tax_year=tax_year
        )
        
        if not property_data:
            logger.warning("No properties found matching the search criteria.")
            return {"property_data": [], "message": "No properties found"}
            
        logger.info(f"Found {len(property_data)} properties")
        
        # Process each property
        for i, property in enumerate(property_data):
            # Log progress
            logger.info(f"Processing property {i+1} of {len(property_data)}: Account {property.get('Account', 'N/A')}, Name {property.get('Matched Name', 'Unknown')}")
            
            # Scrape details using county_config
            if property_item.get("Link"): # Ensure there's a link to scrape
                details = scrape_details(
                    link=property_item["Link"],
                    tax_year=tax_year,
                    county_config=county_config
                )
                property_item.update(details)
            else:
                logger.warning(f"Skipping detail scrape for property {i+1} due to missing 'Link'. Account: {property.get('Account', 'N/A')}")

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
        from core.outputs.excel_writer import write_to_excel
        from core.utils.logger import log_errors
        
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