import os
import sys
import json
import time
from termcolor import colored

# Ensure `scrappy` is in the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Imports
from scrapers.property_scraper import scrape_property_data, SUPPORTED_LOCALES
from scrapers.detail_scraper import scrape_details
from outputs.excel_writer import write_to_excel
from utils.logger import log_errors
import requests

def get_session_folders(session_id=None):
    """Get or create session-specific output folders."""
    OUTPUT_FOLDER = os.path.join(current_dir, "outputs")
    if session_id:
        session_folder = os.path.join(OUTPUT_FOLDER, session_id)
        PDF_FOLDER = os.path.join(session_folder, "pdfs")
        os.makedirs(PDF_FOLDER, exist_ok=True)
        return session_folder, PDF_FOLDER
    return OUTPUT_FOLDER, os.path.join(OUTPUT_FOLDER, "pdfs")

# Set up output folders (with session support)
SESSION_ID = os.getenv("SCRAPPY_SESSION_ID", "default")
OUTPUT_FOLDER, PDF_FOLDER = get_session_folders(SESSION_ID)

def ask_confirmation(match, current_owner):
    """Handle confirmation in both API and CLI contexts."""
    external_mode = os.getenv("SCRAPPY_EXTERNAL_CONFIRMATION", "false").lower() == "true"
    if external_mode:
        response = {
            "status": "confirmation_required",
            "owner": current_owner,
            "match": match,
            "session_id": os.getenv("SCRAPPY_SESSION_ID", "default")
        }
        print(json.dumps(response), flush=True)
        while True:
            confirmation = os.getenv("SCRAPPY_CONFIRMATION")
            if confirmation in ["yes", "no"]:
                os.environ["SCRAPPY_CONFIRMATION"] = ""  # Reset confirmation
                return confirmation == "yes"
            time.sleep(0.1)

    # Fallback for CLI use
    while True:
        response = input(f"Does {colored(current_owner, 'yellow')} match {colored(match, 'yellow')}? (y/n): ").strip().lower()
        if response in ["y", "n"]:
            return response == "y"

def download_pdf(link, filename, current, total):
    """Download PDF from the provided link."""
    if not link:
        print(f"Invalid PDF link for {filename}. Skipping.")
        return

    try:
        response = requests.get(link, stream=True)
        if response.status_code == 200:
            file_path = os.path.join(PDF_FOLDER, f"{filename}.pdf")
            with open(file_path, "wb") as pdf_file:
                for chunk in response.iter_content(chunk_size=1024):
                    pdf_file.write(chunk)
            print(f"PDF {current} of {total} " + colored("downloaded successfully", "green") + f": {file_path}")
        else:
            print(colored(f"Failed to download PDF. Status: {response.status_code}", "red"))
    except Exception as e:
        print(colored(f"Error downloading PDF: {e}", "red"))

def get_user_input():
    """Get user input for owner names."""
    env_owners = os.getenv("SCRAPPY_OWNERS")
    if env_owners:
        return env_owners.split(";")
    return input("Enter owner names (semicolon-separated): ").split(";")

def select_locale_cli():
    """Interactive locale selection for CLI."""
    locales = {index + 1: locale for index, locale in enumerate(SUPPORTED_LOCALES)}
    colors = ["green", "blue", "red", "cyan", "magenta"]

    print("Select a locale:")
    for num, (key, loc) in enumerate(locales.items(), start=1):
        color = colors[(num - 1) % len(colors)]
        print(f"{colored(num, color)}. {colored(loc, color)}")

    while True:
        try:
            locale_choice = int(input("Search by Locale (" + ", ".join([colored(str(num), colors[(num - 1) % len(colors)]) for num in locales]) + "): "))
            if locale_choice in locales:
                return locales[locale_choice]
            print(colored("Invalid selection. Please choose a valid number.", "red"))
        except ValueError:
            print(colored("Please enter a valid number.", "red"))

def main():
    """Main execution function with CLI interface."""
    # Use environment variables if available, otherwise use CLI
    locale = os.getenv("SCRAPPY_LOCALE") or select_locale_cli()
    tax_year = os.getenv("TAX_YEAR") or input("Enter the tax year (default: 2024): ").strip() or "2024"

    # Get input names
    input_names = [name.strip() for name in get_user_input() if name.strip()]

    # Scrape and process data
    property_data = scrape_property_data(input_names, locale=locale, tax_year=tax_year)
    
    for property in property_data:
        details = scrape_details(property["Link"])
        property.update(details)
        pdf_filename = f"{property.get('Parcel', 'Unknown').replace('/', '_')}_{property.get('Matched Name', 'Unknown').replace('/', '_')}"
        download_pdf(property.get("PDF Link"), pdf_filename, property_data.index(property) + 1, len(property_data))

    # Write outputs
    excel_file_path = os.path.join(OUTPUT_FOLDER, "output.xlsx")
    write_to_excel(property_data, excel_file_path)

    error_log_path = os.path.join(OUTPUT_FOLDER, "errors.log")
    log_errors(property_data, error_log_path)

    # Prepare output data
    output_data = {
        "excel_file": excel_file_path,
        "pdf_folder": PDF_FOLDER,
        "property_data": property_data,
        "errors": []
    }

    # CLI output
    print(json.dumps(output_data))
    print(colored(f"Data written to {excel_file_path}", "green"))
    print(colored(f"Errors logged to {error_log_path}", "red"))

    return output_data

if __name__ == "__main__":
    main()