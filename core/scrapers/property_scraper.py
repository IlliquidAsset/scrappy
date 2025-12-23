import requests
from bs4 import BeautifulSoup
from rapidfuzz.fuzz import partial_ratio
from functools import wraps
from core.utils.normalizer import normalize_text
from core.utils.confirmation import ask_confirmation  # Use new module instead of main
from termcolor import colored
import time
import logging
"""
core/scrapers/property_scraper.py

This module is responsible for scraping property search results from county assessor websites.
It is designed to be configuration-driven, meaning that the specifics of how to interact
with a particular county's website (e.g., URLs, form fields, CSS selectors for data extraction)
are provided via a `county_config` dictionary rather than being hardcoded.

This approach allows for easier adaptation to different county websites that share similar
HTML structures or search patterns (especially those using common platforms like MyGovOnline).
"""
# SUPPORTED_LOCALES will no longer be used directly in this file after refactoring.
# from core.locales import SUPPORTED_LOCALES

# Set up logging
logger = logging.getLogger(__name__)

# --- Helper Functions for Safe Data Extraction ---

def safe_select_text(element, selector, default=''):
    """
    Safely selects a single element using a CSS selector from a given parent element
    and returns its stripped text content.

    Args:
        element (bs4.element.Tag): The parent BeautifulSoup element to search within.
        selector (str): The CSS selector to find the target child element.
        default (str, optional): The value to return if the element is not found
                                 or contains no text. Defaults to ''.

    Returns:
        str: The stripped text content of the found element, or the default value.
    """
    try:
        selected = element.select_one(selector)
        if selected and selected.text:
            return selected.text.strip()
    except AttributeError:
        logger.debug(f"AttributeError while trying to get text from selector '{selector}'. Element: {str(element)[:100]}")
    except Exception as e:
        logger.warning(f"Exception selecting text for selector '{selector}': {e}. Element: {str(element)[:100]}")
    return default

def safe_select_attribute(element, selector, attribute, default=''):
    """
    Safely selects a single element using a CSS selector from a given parent element
    and returns the value of a specified attribute.

    Args:
        element (bs4.element.Tag): The parent BeautifulSoup element to search within.
        selector (str): The CSS selector to find the target child element.
        attribute (str): The name of the HTML attribute to retrieve (e.g., 'href', 'value').
        default (str, optional): The value to return if the element or attribute
                                 is not found. Defaults to ''.

    Returns:
        str: The value of the specified attribute, or the default value.
    """
    try:
        selected = element.select_one(selector)
        if selected and selected.has_attr(attribute):
            return selected[attribute]
    except AttributeError:
        logger.debug(f"AttributeError while trying to get attribute '{attribute}' from selector '{selector}'. Element: {str(element)[:100]}")
    except Exception as e:
        logger.warning(f"Exception selecting attribute '{attribute}' for selector '{selector}': {e}. Element: {str(element)[:100]}")
    return default

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

def confirm_match(input_name, matched_name, address, confirmed_matches, threshold=80):
    """
    Confirm if the matched name is correct based on the input name, using fuzzy matching.
    Includes property address in the confirmation prompt for better user context.

    Args:
        input_name (str): The original name provided for searching.
        matched_name (str): The name found on the property record.
        address (str): The address of the property associated with matched_name.
        confirmed_matches (dict): A dictionary to cache confirmation results.
        threshold (int): The fuzzy match ratio threshold for prompting confirmation.

    Returns:
        bool: True if the match is confirmed (either directly or by user), False otherwise.
    """
    normalized_input = normalize_text(input_name)
    normalized_matched = normalize_text(matched_name)

    if normalized_input == normalized_matched:
        return True

    # If the names are not an exact match but meet the similarity threshold,
    # ask the user for confirmation, providing the address for context.
    if partial_ratio(normalized_input, normalized_matched) >= threshold:
        return ask_confirmation(matched_name, input_name, address)
    
    return False

@rate_limited(2) # 2 requests per second to avoid being blocked
def make_scrape_request(session, url, payload, request_type="POST"):
    """Make a rate-limited request to scrape data."""
    try:
        if request_type.upper() == "POST":
            response = session.post(url, data=payload)
        elif request_type.upper() == "GET":
            response = session.get(url, params=payload)
        else:
            logger.error(f"Unsupported request type: {request_type}")
            return None
        logger.debug(f"Request to {url} ({request_type}): Status {response.status_code}")
        return response
    except requests.RequestException as e:
        logger.error(f"Request error to {url}: {e}")
        raise

def scrape_property_data(owner_names, county_config, tax_year):
    """
    Main function to orchestrate property data scraping for a list of owner names.
    It uses a county-specific configuration (`county_config`) to adapt its behavior.

    Args:
        owner_names (list): A list of owner names to search for.
        county_config (dict): A dictionary containing all necessary configurations
                              for scraping a specific county. This includes URLs,
                              payload templates, CSS selectors, etc.
        tax_year (str): The tax year for which to search.

    Returns:
        list: A list of dictionaries, where each dictionary represents a found
              and confirmed property record.
    """
    results = []
    session = requests.Session() # Use a session to persist cookies if needed.
    confirmed_matches = {} # Cache for confirmed name matches to avoid re-prompting for the same name.

    # Iterate through each owner name provided.
    for owner_name in owner_names:
        scrape_owner_data(session, owner_name, county_config, tax_year, confirmed_matches, results)
    return results

def scrape_owner_data(session, owner_name, county_config, tax_year, confirmed_matches, results):
    """
    Scrapes property data for a single owner name, handling pagination.
    All site-specific details (URLs, selectors, payload) are sourced from `county_config`.

    Args:
        session (requests.Session): The requests session object.
        owner_name (str): The owner name currently being searched.
        county_config (dict): Configuration for the target county.
        tax_year (str): The tax year for the search.
        confirmed_matches (dict): Cache for confirmed matches.
        results (list): The list to append found property data to.
    """
    normalized_owner_name = normalize_text(owner_name)
    seen_accounts = set() # Keeps track of processed account IDs to avoid duplicates.
    page = 1
    # Max pages to scrape, configurable per county, with a default.
    max_pages = county_config.get("max_search_pages", 20)

    # The base URL for property search, from county configuration.
    base_url = county_config['search_url']
    # HTTP request type (e.g., "POST", "GET") for the search, from county configuration.
    request_type = county_config.get('search_request_type', 'POST')

    while page <= max_pages:
        # Dynamically construct the search request payload using a template from county_config.
        # Placeholders like {tax_year}, {owner_name}, {page_number} are replaced.
        payload_template = county_config['search_payload_template']
        payload = {}
        for key, value_template in payload_template.items():
            if isinstance(value_template, str): # If template field is a string, format it.
                try:
                    payload[key] = value_template.format(
                        tax_year=tax_year,
                        owner_name=normalized_owner_name,
                        page_number=str(page)
                    )
                except KeyError as e:
                    logger.warning(f"Payload template key '{e}' not found in format args for county {county_config.get('locale_code', 'N/A')}. Key: {key}, Template: {value_template}")
                    payload[key] = value_template # Use template as is if formatting fails partially
            else: # For static values (e.g., numbers, booleans in template).
                payload[key] = value_template

        logger.debug(f"Scraping data for '{owner_name}' (Page {page} of max {max_pages}) using URL: {base_url} and Payload: {payload}")
        try:
            response = make_scrape_request(session, base_url, payload, request_type)
            
            if not handle_response(response, owner_name, page):
                break # Stop if response indicates an issue (e.g., server error, bad request).

            soup = BeautifulSoup(response.text, "html.parser")

            # Find the main results table using a CSS selector from county_config.
            results_table_selector = county_config['property_search_results_selectors']['results_table']
            table = soup.select_one(results_table_selector)

            if not table:
                logger.info(f"No results table found using selector '{results_table_selector}' on page {page} for '{owner_name}'. Stopping.")
                break

            # Process all rows found within the identified table.
            # The county_config is passed down to use appropriate selectors for row details.
            if not process_table_rows(soup, table, owner_name, county_config, confirmed_matches, results, seen_accounts):
                break # Stop if no more rows processed or pagination indicates the end.

            # Check if any new results were added on this page to prevent infinite loops on faulty pagination
            current_results_count = len(seen_accounts) # Assuming seen_accounts is modified in process_table_rows or process_table_row
            # This logic needs to be careful: if process_table_rows returns True but adds no new unique accounts,
            # we might loop. `new_results_on_page` from `process_table_rows` is better.
            # For now, let's assume process_table_rows returns False if no new results are made from that page.

            page += 1
        except requests.RequestException as e:
            logger.error(f"Error fetching data for '{owner_name}', Page: {page}: {e}", exc_info=True)
            break # Stop on request errors
    
    if page > max_pages:
        logger.warning(f"Reached maximum page limit ({max_pages}) for '{owner_name}'. Stopping to prevent infinite loop.")

def handle_response(response, owner_name, page):
    """Handle the HTTP response from the server."""
    if response is None: # If make_scrape_request returned None due to bad request_type
        return False
    if response.status_code == 500:
        logger.warning(f"Server error (HTTP 500) for '{owner_name}', Page: {page}. May retry or skip.")
        # Depending on strategy, might return True to retry or False to stop for this owner.
        # For now, let's say we stop for this owner on a 500.
        return False
    if response.status_code != 200:
        logger.error(f"Failed to fetch data for '{owner_name}', Page: {page}: HTTP {response.status_code}")
        return False
    return True

def process_table_rows(soup, table, owner_name, county_config, confirmed_matches, results, seen_accounts):
    """
    Processes each row within the found results table.
    Uses CSS selectors from `county_config` to identify individual data rows
    and the pagination link (e.g., "Next" button).

    Args:
        soup (BeautifulSoup): The BeautifulSoup object for the current page.
        table (bs4.element.Tag): The BeautifulSoup element representing the results table.
        owner_name (str): The owner name being searched.
        county_config (dict): Configuration for the target county.
        confirmed_matches (dict): Cache for confirmed matches.
        results (list): List to append processed property data.
        seen_accounts (set): Set of account IDs already processed to avoid duplicates.

    Returns:
        bool: True if processing should continue (e.g., more pages might exist),
              False if no more results or pagination end is reached.
    """
    selectors = county_config['property_search_results_selectors']

    # Select all property data rows from the table using a selector from county_config.
    # Example: 'tbody tr' or 'tr.property-record'.
    row_selector = selectors['result_row']
    rows = table.select(row_selector)

    if not rows:
        logger.info(f"No property data rows found for '{owner_name}' using selector '{row_selector}'.")
        return False # No rows to process.

    new_results_on_page = 0
    for row_element in rows:
        # Process each row to extract property details.
        # county_config is passed to use specific selectors for data within the row.
        processed_count = process_table_row(row_element, owner_name, county_config, confirmed_matches, results, seen_accounts)
        if processed_count > 0:
            new_results_on_page += processed_count

    # Check for a "Next" page link using a selector from county_config.
    next_page_selector = selectors.get('next_page_link')
    if next_page_selector:
        pagination_element = soup.select_one(next_page_selector)
        # If no "Next" link is found, or if no new unique results were added on this page,
        # assume it's the end of results or a potential loop, so stop.
        if not pagination_element:
            logger.info(f"No 'Next' page link found using selector '{next_page_selector}' for '{owner_name}'. Assuming end of results.")
            return False
        if new_results_on_page == 0 and pagination_element: # Next link exists but no new unique properties found.
             logger.info(f"Next page link exists, but no new unique properties found on this page for '{owner_name}'. Stopping to prevent potential loop.")
             return False
    else:
        # If no 'next_page_link' selector is defined in the config, assume single-page results.
        logger.info(f"No 'next_page_link' selector in config for '{owner_name}'. Assuming single page of results.")
        return False

    return True # Indicates that a "Next" page link was found and new results were added.

def process_table_row(row_element, owner_name, county_config, confirmed_matches, results, seen_accounts):
    """
    Processes a single row from the results table to extract property information.
    Uses specific CSS selectors defined in `county_config` for each piece of data.

    Args:
        row_element (bs4.element.Tag): The BeautifulSoup element for the table row.
        owner_name (str): The owner name being searched.
        county_config (dict): Configuration for the target county.
        confirmed_matches (dict): Cache for confirmed matches.
        results (list): List to append extracted property data.
        seen_accounts (set): Set of account IDs already processed.

    Returns:
        int: 1 if a new, confirmed property record was added, 0 otherwise.
    """

    selectors = county_config['property_search_results_selectors']
    extraction_hints = county_config.get('extraction_hints', {})

    # Extract Account ID using its specific selector from county_config.
    account_id_selector = selectors['account_id']
    account = safe_select_text(row_element, account_id_selector)

    if not account: # If account ID (essential identifier) is not found, skip this row.
        logger.warning(f"Could not extract account ID using selector '{account_id_selector}' for '{owner_name}'. Row HTML: {str(row_element)[:200]}. Skipping row.")
        return 0 # Cannot process without account ID.

    if account in seen_accounts: # Avoid processing duplicate account entries.
        logger.debug(f"Account '{account}' for '{owner_name}' already processed. Skipping duplicate.")
        return 0

    # Extract Owner Name from the row using its selector from county_config.
    owner_name_selector = selectors['owner_name']
    found_owner_name = safe_select_text(row_element, owner_name_selector)

    # Extract Property Address from the row using its selector from county_config.
    address_selector = selectors['address']
    address = safe_select_text(row_element, address_selector)

    # Extract displayed Tax Year from the row using its selector from county_config.
    tax_year_display_selector = selectors['tax_year_display']
    year_display = safe_select_text(row_element, tax_year_display_selector)

    # Extract the detail page link suffix.
    # The attribute (e.g., 'href') is specified in 'extraction_hints' or defaults to 'href'.
    link_attribute = extraction_hints.get('detail_page_link_attribute', 'href')
    detail_page_link_selector = selectors['detail_page_link']
    link_suffix = safe_select_attribute(row_element, detail_page_link_selector, link_attribute)

    full_link = None
    if not link_suffix:
        logger.warning(f"Could not extract detail page link for account '{account}' of '{owner_name}' using selector '{detail_page_link_selector}'.")
    else:
        # Construct the full detail page URL using the base URL from county_config and the extracted suffix.
        # Handles relative and absolute URLs in link_suffix.
        detail_base_url = county_config.get('detail_page_base_url', county_config['search_url'].rsplit('/', 1)[0] + '/')
        from urllib.parse import urljoin # Import here to keep it localized if not used elsewhere broadly.
        full_link = urljoin(detail_base_url, link_suffix)

    # Construct PDF Link. This logic is often platform-specific (e.g., MyGovOnline).
    # It relies on parsing an 'id' from the detail link and using a 'pdf_link_template' from county_config.
    id_value = None
    if full_link and "id=" in full_link: # Example for MyGovOnline-style ID in URL.
        try:
            id_value = full_link.split("id=")[1].split("&")[0]
        except IndexError:
            logger.warning(f"Could not parse 'id' from detail link: {full_link} for PDF link construction.")

    pdf_link_template = county_config.get('pdf_link_template')
    pdf_link = None
    if pdf_link_template and id_value:
        try:
            # Base URL for PDF links can be specified or defaults similarly to detail_base_url.
            pdf_base = county_config.get('pdf_link_base_url', county_config.get('detail_page_base_url', county_config['search_url'].rsplit('/', 1)[0] + '/'))
            pdf_link = urljoin(pdf_base, pdf_link_template.format(id=id_value)) # Format template with ID.
        except Exception as e: # Catch errors during formatting (e.g., bad template string).
            logger.error(f"Error formatting PDF link for id '{id_value}' with template '{pdf_link_template}': {e}")

    # Confirm if the found owner name matches the input name (uses fuzzy matching and user confirmation if needed).
    if confirm_match(owner_name, found_owner_name, address, confirmed_matches):
        results.append({
            "Input Name": owner_name,
            "Matched Name": found_owner_name,
            "Address": address,
            "Account": account,
            "Year": year_display, # The tax year as displayed on the search result row.
            "Link": full_link,
            "PDF Link": pdf_link,
            "Locale": county_config['locale_code'] # Add locale_code for data traceability.
        })
        seen_accounts.add(account) # Add to set of processed accounts.
        return 1 # Signifies one new record successfully processed.
    else:
        logger.info(f"Match not confirmed for potential owner '{found_owner_name}' (Account: {account}) for input '{owner_name}'. Skipping.")
        return 0 # Match not confirmed, record not added.