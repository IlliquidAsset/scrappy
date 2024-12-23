import os
import sys
import json

# Ensure `scrappy` is in the Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
scrappy_root = os.path.dirname(current_dir)
sys.path.insert(0, scrappy_root)

# Imports
from scrapers.property_scraper import scrape_property_data
from scrapers.detail_scraper import scrape_details
from outputs.excel_writer import write_to_excel
from utils.logger import log_errors
import requests

# Define the output folder structure
OUTPUT_FOLDER = os.path.join(os.path.dirname(os.path.abspath(__file__)), "outputs")
PDF_FOLDER = os.path.join(OUTPUT_FOLDER, "pdfs")
os.makedirs(OUTPUT_FOLDER, exist_ok=True)
os.makedirs(PDF_FOLDER, exist_ok=True)

def ask_confirmation(match, current_owner):
    """Emit confirmation to ScrapFlask and wait for a response."""
    external_mode = os.getenv("SCRAPPY_EXTERNAL_CONFIRMATION", "false").lower() == "true"
    if external_mode:
        print(json.dumps({
            "confirmation_required": True,
            "owner": current_owner,
            "match": match
        }))
        confirmation = os.getenv("SCRAPPY_CONFIRMATION")
        if confirmation in ["yes", "no"]:
            return confirmation == "yes"
        else:
            raise ValueError("Invalid or missing confirmation response.")

    # Fallback for CLI use
    while True:
        response = input(f"Does '{current_owner}' match '{match}'? (y/n): ").strip().lower()
        if response in ["y", "n"]:
            return response == "y"

def download_pdf(link, output_folder, filename):
    if not link:
        print(f"Invalid PDF link for {filename}. Skipping.")
        return

    try:
        response = requests.get(link, stream=True)
        if response.status_code == 200:
            file_path = os.path.join(output_folder, f"{filename}.pdf")
            with open(file_path, "wb") as pdf_file:
                for chunk in response.iter_content(chunk_size=1024):
                    pdf_file.write(chunk)
            print(f"PDF downloaded successfully: {file_path}")
        else:
            print(f"Failed to download PDF for {filename}: HTTP {response.status_code}")
    except Exception as e:
        print(f"Error downloading PDF for {filename}: {e}")

def get_user_input():
    env_owners = os.environ.get("SCRAPPY_OWNERS")
    if env_owners:
        return env_owners.split(";")
    return input("Enter owner names (semicolon-separated): ").split(";")

def main():
    # Step 1: Get user input
    input_names = [name.strip() for name in get_user_input() if name.strip()]

    # Step 2: Scrape property data
    property_data = scrape_property_data(input_names)

    # Step 3: Scrape detailed data and download PDFs
    for property in property_data:
        details = scrape_details(property["Link"])
        property.update(details)

        # Save PDFs for each property
        pdf_filename = f"{property.get('Parcel', 'Unknown').replace('/', '_')}_{property.get('Matched Name', 'Unknown').replace('/', '_')}"
        download_pdf(property.get("PDF Link"), PDF_FOLDER, pdf_filename)

    # Step 4: Write results to Excel
    excel_file_path = os.path.join(OUTPUT_FOLDER, "output_davidsonco.xlsx")
    write_to_excel(property_data, excel_file_path)

    # Step 5: Log errors (if any)
    error_log_path = os.path.join(OUTPUT_FOLDER, "errors.log")
    log_errors(property_data, error_log_path)

    # Step 6: Return data as JSON
    output_data = {
        "excel_file": excel_file_path,
        "pdf_folder": PDF_FOLDER,
        "property_data": property_data,
        "errors": []  # Assuming log_errors appends to the errors list in `property_data`
    }

    # Print the JSON for integration with ScrapFlask
    print(json.dumps(output_data))

    # Completion message
    print(f"Data written to {excel_file_path}")
    print(f"Errors logged to {error_log_path}")
    print(f"PDFs saved to {PDF_FOLDER}")

if __name__ == "__main__":
    main()
