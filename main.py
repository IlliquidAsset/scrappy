import os
import sys
import json
import requests
from termcolor import colored

# Ensure `scrappy` is in the Python path dynamically
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

# Imports
try:
    from locales import SUPPORTED_LOCALES
    from scrapers.property_scraper import scrape_property_data
    from scrapers.detail_scraper import scrape_details
    from outputs.excel_writer import write_to_excel
    from utils.logger import log_errors
except ModuleNotFoundError as e:
    print(colored(f"Error: {e}. Ensure Scrappy's folder structure is intact.", "red"))
    sys.exit(1)

# Define the output folder structure
OUTPUT_FOLDER = os.path.join(current_dir, "outputs")
PDF_FOLDER = os.path.join(OUTPUT_FOLDER, "pdfs")
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
        return confirmation == "yes" if confirmation in ["yes", "no"] else False
    return confirm_cli(current_owner, match)

def confirm_cli(current_owner, match):
    """Fallback confirmation for CLI use."""
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
    return env_owners.split(";") if env_owners else input("Enter owner names (semicolon-separated): ").split(";")

def select_locale():
    """Prompt the user to select a locale."""
    locales = {index + 1: locale for index, locale in enumerate(SUPPORTED_LOCALES)}
    colors = ["green", "blue", "red", "cyan", "magenta"]

    print("Select a locale:")
    for num, loc in locales.items():
        color = colors[(num - 1) % len(colors)]
        print(f"{colored(num, color)}. {colored(SUPPORTED_LOCALES[loc]['name'], color)}")

    while True:
        try:
            locale_choice = int(input("Search by Locale (" + ", ".join([colored(str(num), colors[(num - 1) % len(colors)]) for num in locales]) + "): "))
            return locales.get(locale_choice)
        except ValueError:
            print(colored("Invalid input. Please enter a valid number.", "red"))

def format_cli_output(property_data, errors, excel_file_path, error_log_path):
    """Format and display the CLI output for readability."""
    print("\n" + "=" * 40 + "\nSummary Report\n" + "=" * 40)
    print(f"Excel file saved to: {colored(excel_file_path, 'green')}")
    print(f"PDFs saved to: {colored(PDF_FOLDER, 'green')}")

    if property_data:
        print("\nProperty Data Summary:")
        for index, prop in enumerate(property_data, start=1):
            print(f"{index}. {colored(prop['Matched Name'], 'yellow')} - {colored(prop['Address'], 'cyan')} "
                  f"(Account: {prop['Account']}, Year: {prop['Year']})")
    else:
        print(colored("\nNo property data found.", "red"))

    if errors:
        print("\nErrors encountered:")
        for error in errors:
            print(f"- {colored(error, 'red')}")
    else:
        print(colored("\nNo errors encountered!", "green"))

    print("\nLogs saved to:")
    print(f"- Data: {colored(excel_file_path, 'green')}")
    print(f"- Errors: {colored(error_log_path, 'green')}")
    print("=" * 40)

def main():
    locale = select_locale()
    tax_year = input("Enter the tax year (default: 2024): ").strip() or "2024"
    input_names = [name.strip() for name in get_user_input() if name.strip()]

    errors = []
    property_data = scrape_property_data(input_names, locale=locale, tax_year=tax_year)
    process_properties(property_data, errors)

    excel_file_path = os.path.join(OUTPUT_FOLDER, "output.xlsx")
    write_to_excel(property_data, excel_file_path)

    error_log_path = os.path.join(OUTPUT_FOLDER, "errors.log")
    log_errors(property_data, error_log_path)

    format_cli_output(property_data, errors, excel_file_path, error_log_path)

def process_properties(property_data, errors):
    """Process each property by scraping details and downloading PDFs."""
    for property in property_data:
        try:
            details = scrape_details(property["Link"])
            property.update(details)
            pdf_filename = f"{property.get('Parcel', 'Unknown').replace('/', '_')}_{property.get('Matched Name', 'Unknown').replace('/', '_')}"
            download_pdf(property.get("PDF Link"), pdf_filename, property_data.index(property) + 1, len(property_data))
        except Exception as e:
            errors.append(f"Error processing property: {property.get('Matched Name', 'Unknown')} - {e}")

if __name__ == "__main__":
    main()
