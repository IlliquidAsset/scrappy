import os
import sys
import json
import requests
from termcolor import colored
from pprint import pprint
import io
from contextlib import redirect_stdout

# Add scrappy to Python path
current_dir = os.path.dirname(os.path.abspath(__file__))
scrappy_dir = os.path.join(current_dir, 'scrappy')
if scrappy_dir not in sys.path:
    sys.path.insert(0, scrappy_dir)

from scrappy.scrapers.property_scraper import scrape_property_data
from scrappy.scrapers.detail_scraper import scrape_details

def download_pdf(link, output_folder, filename, current, total):
    """Download PDF from the provided link."""
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
            print(f"PDF {current} of {total} " + colored("downloaded successfully", "green") + f": {file_path}")
        else:
            print(colored(f"Failed to download PDF. Status: {response.status_code}", "red"))
    except Exception as e:
        print(colored(f"Error downloading PDF: {e}", "red"))

def process_properties(property_data, errors):
    """Process each property by scraping details and downloading PDFs."""
    results = []
    for property in property_data:
        try:
            details = scrape_details(property["Link"])
            property.update(details)
            results.append(property)
            pdf_filename = f"{property.get('Parcel', 'Unknown').replace('/', '_')}_{property.get('Matched Name', 'Unknown').replace('/', '_')}"
            download_pdf(property.get("PDF Link"), "outputs/pdfs", pdf_filename, property_data.index(property) + 1, len(property_data))
        except Exception as e:
            errors.append(f"Error processing property: {property.get('Matched Name', 'Unknown')} - {e}")
    return results

def handle_scrappy_output(output_line, desired_matches):
    """Handle JSON output from Scrappy's confirmation system."""
    try:
        data = json.loads(output_line)
        if data.get("confirmation_required"):
            owner = data.get("owner")
            match = data.get("match")

            # Auto-confirm matches based on criteria
            if "HERMITAGE 1, LLC" in match or "101 HART LANE, LLC" in match:
                os.environ["SCRAPPY_CONFIRMATION"] = "yes"
                print(colored(f"Confirmed match: {match}", "green"))
                return True
            else:
                os.environ["SCRAPPY_CONFIRMATION"] = "no"
                print(colored(f"Rejected match: {match}", "yellow"))
                return False
    except json.JSONDecodeError:
        return False
    return False

def test_scrappy():
    """Test Scrappy with specific search terms"""
    # Enable external confirmation mode
    os.environ["SCRAPPY_EXTERNAL_CONFIRMATION"] = "true"
    os.environ["SCRAPPY_TAX_YEAR"] = "2024"

    # Test terms
    search_terms = ["Hermitage 1", "101 Hart ln"]
    locale = "davidson-tn"
    all_results = []
    errors = []

    desired_matches = {
        "Hermitage 1": ["HERMITAGE 1, LLC"],
        "101 Hart ln": ["101 HART LANE, LLC"]
    }

    for term in search_terms:
        print(f"\nSearching for: {term}")
        try:
            # Capture and process stdout for confirmation handling
            buffer = io.StringIO()
            results = None
            with redirect_stdout(buffer):
                results = scrape_property_data([term], locale=locale, tax_year="2024")

            # Process confirmations from captured output
            for line in buffer.getvalue().splitlines():
                handle_scrappy_output(line, desired_matches)

            # Process the results
            if results and isinstance(results, list):
                print(colored(f"Found {len(results)} matches", "green"))
                processed_results = process_properties(results, errors)
                all_results.extend(processed_results)
                print(colored(f"Processed {len(processed_results)} properties", "cyan"))
            else:
                print(colored("No matches found", "yellow"))

        except Exception as e:
            print(colored(f"Error processing {term}: {e}", "red"))
            errors.append(f"Top-level error for {term}: {e}")
            continue

    # Print summary
    print(f"\n{colored('Results Summary', 'cyan')}")
    print(f"Total matches found: {colored(str(len(all_results)), 'green')}")

    if all_results:
        print("\nSample matches:")
        for idx, result in enumerate(all_results[:3], 1):
            print(colored(f"\nResult {idx}:", "yellow"))
            print(f"Owner: {result.get('Matched Name')}")
            print(f"Address: {result.get('Address')}")
            print(f"Account: {result.get('Account')}")
            print(f"Year: {result.get('Year')}")

    if errors:
        print(f"\n{colored('Errors encountered:', 'red')}")
        for error in errors:
            print(f"- {error}")

    return all_results

if __name__ == "__main__":
    results = test_scrappy()