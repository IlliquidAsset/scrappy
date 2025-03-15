import requests
from bs4 import BeautifulSoup
from rapidfuzz.fuzz import partial_ratio
from functools import wraps
from core.utils.normalizer import normalize_text
from core.utils.confirmation import ask_confirmation  # Use new module instead of main
from termcolor import colored
import time
import logging
from core.locales import SUPPORTED_LOCALES  # Fixed import here

# Set up logging
logger = logging.getLogger(__name__)

def rate_limited(max_per_second):
    """Decorator to limit the rate of function calls"""
    min_interval = 1.0 / max_per_second
    last_called = [0.0]
    
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            elapsed = time.time() - last_called[0]
            to_wait = min_interval - elapsed
            if to_wait > 0:
                time.sleep(to_wait)
            result = func(*args, **kwargs)
            last_called[0] = time.time()
            return result
        return wrapper
    return decorator

def confirm_match(input_name, matched_name, confirmed_matches, threshold=80):
    """Confirm if the matched name is correct based on the input name."""
    normalized_input = normalize_text(input_name)
    normalized_matched = normalize_text(matched_name)

    if normalized_input == normalized_matched:
        return True

    if partial_ratio(normalized_input, normalized_matched) >= threshold:
        return ask_confirmation(matched_name, input_name)
    
    return False

@rate_limited(2)  # 2 requests per second to avoid being blocked
def make_scrape_request(session, url, payload):
    """Make a rate-limited request to scrape data"""
    try:
        response = session.post(url, data=payload)
        logger.debug(f"Request to {url}: Status {response.status_code}")
        return response
    except requests.RequestException as e:
        logger.error(f"Request error to {url}: {e}")
        raise

def scrape_property_data(owner_names, locale, tax_year):
    """Scrape property data for given owner names and locale."""
    validate_locale(locale)
    base_url = f"{SUPPORTED_LOCALES[locale]['url']}/mod.php?mod=propertytax&mode=public_lookup&action=&title="
    results = []
    session = requests.Session()
    confirmed_matches = {}

    for owner_name in owner_names:
        scrape_owner_data(session, owner_name, base_url, tax_year, confirmed_matches, results, locale)

    return results

def validate_locale(locale):
    """Check if the provided locale is supported."""
    if locale not in SUPPORTED_LOCALES:
        logger.error(f"Unsupported locale: {locale}")
        raise ValueError(f"Unsupported locale: {locale}")

def scrape_owner_data(session, owner_name, base_url, tax_year, confirmed_matches, results, locale):
    """Scrape data for each owner."""
    normalized_owner_name = normalize_text(owner_name)
    seen_accounts = set()
    page = 1

    while True:
        payload = {
            "selectMenu": "individual",
            "tax_year": tax_year,
            "owner_name": normalized_owner_name,
            "page": page
        }

        logger.debug(f"Scraping data for {owner_name} (page {page})")
        try:
            response = make_scrape_request(session, base_url, payload)
            
            if not handle_response(response, owner_name, page):
                break

            soup = BeautifulSoup(response.text, "html.parser")
            table = soup.find("table", id="data")
            if not table:
                logger.info(f"No table found on page {page} for {owner_name}. Stopping.")
                break

            if not process_table_rows(soup, table, owner_name, confirmed_matches, results, seen_accounts, locale):
                break

            page += 1
        except requests.RequestException as e:
            logger.error(f"Error fetching data for {owner_name}, Page: {page}: {e}")
            break

def handle_response(response, owner_name, page):
    """Handle the HTTP response from the server."""
    if response.status_code == 500:
        logger.warning(f"Server error (HTTP 500) for {owner_name}, Page: {page}. Retrying...")
        return False

    if response.status_code != 200:
        logger.error(f"Failed to fetch data for {owner_name}, Page: {page}: HTTP {response.status_code}")
        return False

    return True

def process_table_rows(soup, table, owner_name, confirmed_matches, results, seen_accounts, locale):
    """Process rows from the data table."""
    rows = table.find_all("tr", class_="odd")
    if not rows:
        logger.info(f"No rows found for {owner_name}. Stopping.")
        return False

    new_results = 0
    for row in rows:
        new_results += process_table_row(row, owner_name, confirmed_matches, results, seen_accounts, locale)

    pagination_element = soup.find("a", string="Next")
    if not pagination_element or new_results == 0:
        logger.info(f"No new results or pagination end reached for {owner_name}. Stopping.")
        return False

    return True

def process_table_row(row, owner_name, confirmed_matches, results, seen_accounts, locale):
    """Process a single row from the data table."""
    cells = row.find_all("td")
    if cells:
        account = cells[3].text.strip() if len(cells) > 3 else None

        # Ensure the account is unique
        if account and account in seen_accounts:
            return 0

        owner = cells[1].text.strip() if len(cells) > 1 else None
        address = cells[2].text.strip() if len(cells) > 2 else None
        year = cells[4].text.strip() if len(cells) > 4 else None

        # Get the last column (assumes the last column always contains the link)
        last_cell = cells[-1]
        link_suffix = last_cell.find("a")["href"] if last_cell.find("a") else None

        full_link = f"{SUPPORTED_LOCALES[locale]['url']}/{link_suffix}" if link_suffix else None
        id_value = link_suffix.split("id=")[1].split("&")[0] if link_suffix and "id=" in link_suffix else None
        pdf_link = f"{SUPPORTED_LOCALES[locale]['url']}/mod.php?mod=propertytax&mode=PDFBill&viewtype=public&bill[]={id_value}&show_ocr=1" if id_value else None

        # If there's a match, append it to results
        if confirm_match(owner_name, owner, confirmed_matches):
            results.append({
                "Input Name": owner_name,
                "Matched Name": owner,
                "Address": address,
                "Account": account,
                "Year": year,
                "Link": full_link,
                "PDF Link": pdf_link,
            })

            # Add to seen accounts to avoid duplicates
            if account:
                seen_accounts.add(account)

            return 1

    return 0