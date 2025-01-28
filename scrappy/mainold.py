import os
import sys
import json
from termcolor import colored

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
        response = input(f"Does {colored(current_owner, 'yellow')} match {colored(match, 'yellow')}? (y/n): ").strip().lower()
        if response in ["y", "n"]:
            return response == "y"

def download_pdf(link, output_folder, filename, current, total):
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
            print(f"PDF {current} of {total} " + colored("downloaded successfully", "green") + f": scrappy\\outputs\\pdfs\\{filename}.pdf")
        else:
            print(colored("Failed to download PDF. Server responded with status: {response.status_code}", "red"))
    except Exception as e:
        print(colored(f"Error downloading PDF: {e}", "red"))

def get_user_input():
    env_owners = os.environ.get("SCRAPPY_OWNERS")
    if env_owners:
        return env_owners.split(";")
    return input("Enter owner names (semicolon-separated): ").split(";")

def main():
    # Locale selection
    from scrapers.property_scraper import SUPPORTED_LOCALES  # Dynamically fetch locales
    locales = {index + 1: locale for index, locale in enumerate(SUPPORTED_LOCALES)}
    colors = ["green", "blue", "red", "cyan", "magenta"]  # Dynamic color palette

    print("Select a locale:")
    for num, (key, loc) in enumerate(locales.items(), start=1):
        color = colors[(num - 1) % len(colors)]  # Cycle through colors dynamically
        print(f"{colored(num, color)}. {colored(loc, color)}")

    while True:
        try:
            locale_choice = int(input("Search by Locale (" + ", ".join([colored(str(num), colors[(num - 1) % len(colors)]) for num in locales]) + "): "))
            if locale_choice in locales:
                locale = locales[locale_choice]
                break
            else:
                print(colored("Invalid selection. Please choose a valid number.", "red"))
        except ValueError:
            print(colored("Please enter a valid number.", "red"))

    # Tax year input
    tax_year = input("Enter the tax year (default: 2024): ").strip() or "2024"

    # Step 1: Get user input
    input_names = [name.strip() for name in get_user_input() if name.strip()]

    # Step 2: Scrape property data
    property_data = scrape_property_data(input_names, locale=locale, tax_year=tax_year)

    # Step 3: Scrape detailed data and download PDFs
    for property in property_data:
        details = scrape_details(property["Link"])
        property.update(details)

        pdf_filename = f"{property.get('Parcel', 'Unknown').replace('/', '_')}_{property.get('Matched Name', 'Unknown').replace('/', '_')}"
        download_pdf(property.get("PDF Link"), PDF_FOLDER, pdf_filename, property_data.index(property) + 1, len(property_data))

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

    print(json.dumps(output_data))
    print(colored(f"Data written to {excel_file_path}", "green"))
    print(colored(f"Errors logged to {error_log_path}", "red"))

if __name__ == "__main__":
    main()
