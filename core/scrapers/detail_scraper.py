import requests
from bs4 import BeautifulSoup
import logging
from functools import wraps
import time

"""
core/scrapers/detail_scraper.py

This module is responsible for scraping detailed information from a specific property's page.
It is designed to be configuration-driven, similar to property_scraper.py. The `county_config`
provides the necessary CSS selectors or label information to locate and extract specific
data points from the property detail page.

The core extraction logic is handled by the `extract_detail_value` helper function,
which can try multiple methods (e.g., finding by label, using a CSS selector) to
robustly fetch each piece of information.
"""

# Set up logging
logger = logging.getLogger(__name__)

# --- Helper Function for Config-Driven Detail Extraction ---
def extract_detail_value(soup, field_config_list, link_for_logging=""):
    """
    Extracts a specific detail value from a BeautifulSoup soup object based on a list of
    extraction configurations. This function allows for flexible data extraction by trying
    multiple methods (e.g., by text label, by CSS selector) as defined in the configuration.

    Args:
        soup (BeautifulSoup): The BeautifulSoup object representing the HTML of the detail page.
        field_config_list (list): A list of dictionaries. Each dictionary represents one
                                  attempt/method to find the desired value.
                                  Each dictionary should have:
                                    - "type" (str): The extraction method, e.g., "label", "selector".
                                    - "value" (str): The actual label text or CSS selector string.
                                    - "target_attribute" (str, optional): If specified (e.g., 'href', 'data-value'),
                                      extracts this attribute from the found element instead of its text.
                                      If 'text' or not provided, .text.strip() is used.
                                    - "label_element_tag" (str, optional, for type="label"): The HTML tag
                                      of the label element itself (e.g., "td", "span"). Defaults to "td".
                                    - "value_element_tag" (str, optional, for type="label"): The HTML tag
                                      of the element containing the value, typically a sibling to the label
                                      element. Defaults to "td".
        link_for_logging (str, optional): The URL of the page being scraped. Used for logging
                                          to provide context in case of errors or debug messages.

    Returns:
        str: The extracted and stripped text value or attribute value. Returns an empty
             string if no method successfully extracts the value or if an error occurs.
    """
    # Ensure field_config_list is actually a list to prevent errors.
    if not isinstance(field_config_list, list):
        logger.warning(f"Invalid field_config_list (not a list) for link '{link_for_logging}'. Config: {field_config_list}")
        return ""

    # Iterate through each configured extraction method.
    for config_item in field_config_list:
        if not isinstance(config_item, dict): # Basic validation for each item.
            logger.warning(f"Invalid config item (not a dict) in field_config_list for link '{link_for_logging}'. Item: {config_item}")
            continue

        extract_type = config_item.get("type")  # e.g., "label", "selector"
        extract_value = config_item.get("value") # e.g., "Parcel:", "#parcelIdField"
        # 'target_attribute' allows extracting an attribute value instead of text content.
        # Defaults to 'text' if not specified or if explicitly 'text'.
        target_attribute = config_item.get("target_attribute")

        if not extract_type or not extract_value:
            logger.warning(f"Invalid config item (missing 'type' or 'value') for link '{link_for_logging}'. Item: {config_item}")
            continue

        try:
            if extract_type == "label":
                # Configuration for label-based extraction (finding an element by its text content).
                label_element_tag = config_item.get("label_element_tag", "td") # Tag of the label element.
                value_element_tag = config_item.get("value_element_tag", "td") # Tag of the value element, usually next sibling.

                # Find the label element: an element of `label_element_tag` type
                # whose stripped text exactly matches the `extract_value` (the label).
                label_element = soup.find(
                    lambda tag: tag.name == label_element_tag and tag.text.strip() == extract_value
                )

                if label_element:
                    # If label element is found, find the next sibling element of `value_element_tag` type.
                    value_element = label_element.find_next_sibling(value_element_tag)
                    if value_element:
                        # If a specific attribute is targeted, get its value.
                        if target_attribute and target_attribute != 'text':
                            attr_val = value_element.get(target_attribute)
                            return attr_val.strip() if attr_val else "" # Return stripped attribute or empty.
                        return value_element.text.strip() # Default to text content.
                    else:
                        logger.debug(f"Label '{extract_value}' found, but its next sibling '{value_element_tag}' was not found for link '{link_for_logging}'.")
                else:
                    logger.debug(f"Label '{extract_value}' (expected in a <{label_element_tag}>) not found for link '{link_for_logging}'.")

            elif extract_type == "selector":
                # CSS selector based extraction.
                element = soup.select_one(extract_value) # Find the first element matching the selector.
                if element:
                    # If a specific attribute is targeted, get its value.
                    if target_attribute and target_attribute != 'text':
                        attr_val = element.get(target_attribute)
                        return attr_val.strip() if attr_val else "" # Return stripped attribute or empty.
                    return element.text.strip() # Default to text content.
                else:
                    logger.debug(f"CSS Selector '{extract_value}' did not find any element for link '{link_for_logging}'.")

            # Future extraction types (e.g., "xpath") could be added here as new elif blocks.

        except Exception as e:
            # Log any exception during this specific extraction attempt and try the next method.
            logger.warning(f"Exception during extraction attempt with config {config_item} on link '{link_for_logging}': {e}", exc_info=True)
            continue

    # If all configured methods fail for this field.
    logger.debug(f"All extraction attempts failed for field_config_list: {field_config_list} on link '{link_for_logging}'.")
    return "" # Return default if no method succeeds.


def retry(max_attempts=3, delay=1):
    """Retry decorator with exponential backoff"""
    def decorator(func):
        @wraps(func)
        def wrapper(*args, **kwargs):
            attempts = 0
            while attempts < max_attempts:
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    attempts += 1
                    if attempts == max_attempts:
                        logger.error(f"Failed after {max_attempts} attempts: {e}")
                        raise
                    logger.warning(f"Attempt {attempts} failed: {e}. Retrying in {delay * 2**attempts} seconds...")
                    time.sleep(delay * 2**attempts)
        return wrapper
    return decorator

@retry(max_attempts=3)
def scrape_details(link, tax_year, county_config):
    """
    Scrapes detailed property information from a given property page URL.
    This function is configuration-driven, relying on `county_config` for CSS selectors
    and extraction strategies.

    Args:
        link (str): The URL of the property detail page to scrape.
        tax_year (str): The tax year being targeted. This is used to dynamically
                        formulate the label for the tax rate (e.g., "2023 Tax Rate:").
        county_config (dict): A dictionary containing county-specific configurations,
                              particularly `property_detail_selectors`.

    Returns:
        dict: A dictionary containing the extracted property details. Keys are field names
              (e.g., "Parcel", "Improvement Value"), and values are the scraped data.
              Returns an empty dictionary if scraping fails or essential data is missing.
    """
    if not link:
        logger.warning("No link provided for detail scraping.")
        return {} # Cannot proceed without a link.
    if not county_config:
        logger.error(f"County configuration not provided for detail scraping of link '{link}'.")
        return {} # Cannot proceed without configuration.

    # Get the specific selectors for property details from the overall county configuration.
    detail_selectors = county_config.get('property_detail_selectors', {})
    if not detail_selectors: # If no detail selectors are defined in the config.
        logger.error(f"No 'property_detail_selectors' found in county_config for link '{link}'.")
        return {}

    try:
        response = requests.get(link, timeout=10) # HTTP GET request; timeout can be made configurable.
        if response.status_code == 200: # Proceed only if the request was successful.
            soup = BeautifulSoup(response.text, "html.parser") # Parse HTML content.

            # --- Extract individual data fields using `extract_detail_value` ---
            # Each call to `extract_detail_value` uses a list of extraction attempts
            # defined in `county_config.property_detail_selectors` for that specific field.

            # Extract Parcel ID.
            parcel = extract_detail_value(soup, detail_selectors.get('parcel_id', []), link)

            # Extract Improvement Value.
            improvement_value = extract_detail_value(soup, detail_selectors.get('improvement_value', []), link)

            # Extract Land Value.
            land_value = extract_detail_value(soup, detail_selectors.get('land_value', []), link)

            # Extract Personal Property Value.
            personal_property_value = extract_detail_value(soup, detail_selectors.get('personal_property_value', []), link)

            # Extract Taxable Property / Assessment Rate information.
            # This might require specific cleaning (e.g., removing 'x', '%').
            # Such cleaning logic could also be hinted at in the config if it becomes complex or varies.
            taxable_property_raw = extract_detail_value(soup, detail_selectors.get('taxable_property', []), link)
            taxable_property = taxable_property_raw.replace("x", "").strip()

            # Dynamically construct the tax rate label (e.g., "2023 Tax Rate:") using the
            # `tax_rate_label_pattern` from config and the provided `tax_year`.
            tax_rate_label_pattern = detail_selectors.get('tax_rate_label_pattern', "{year} Tax Rate:") # Default pattern.
            tax_rate_label = tax_rate_label_pattern.replace('{year}', tax_year)
            # Create a temporary field_config_list for this dynamically generated label.
            tax_rate_config_list = [{"type": "label", "value": tax_rate_label}]
            tax_rate = extract_detail_value(soup, tax_rate_config_list, link) # Extract tax rate.

            # Attempt to extract Total Appraised Value if configured.
            total_appraised_value = extract_detail_value(soup, detail_selectors.get('total_appraised_value', []), link)
            # Convert monetary values to numbers where appropriate.
            # Log a warning and default to 0 if conversion fails.
            try:
                # Generic cleaning for currency values, could be enhanced or made configurable
                cleaned_improvement = improvement_value.replace('$', '').replace(',', '')
                improvement_value_float = float(cleaned_improvement) if cleaned_improvement else 0.0
            except (ValueError, AttributeError):
                logger.warning(f"Could not convert Improvement Value '{improvement_value}' to float for link {link}. Defaulting to 0.0.", exc_info=True)
                improvement_value_float = 0.0

            try:
                cleaned_land = land_value.replace('$', '').replace(',', '')
                land_value_float = float(cleaned_land) if cleaned_land else 0.0
            except (ValueError, AttributeError):
                logger.warning(f"Could not convert Land Value '{land_value}' to float for link {link}. Defaulting to 0.0.", exc_info=True)
                land_value_float = 0.0

            try:
                cleaned_personal_property = personal_property_value.replace('$', '').replace(',', '')
                personal_property_value_float = float(cleaned_personal_property) if cleaned_personal_property else 0.0
            except (ValueError, AttributeError):
                logger.warning(f"Could not convert Personal Property Value '{personal_property_value}' to float for link {link}. Defaulting to 0.0.", exc_info=True)
                personal_property_value_float = 0.0

            # Calculate total value from the successfully converted float values.
            # Note: If total_appraised_value is directly available and reliable, it might be preferred.
            # The current logic sums components, which is also common.
            calculated_total_value = improvement_value_float + land_value_float + personal_property_value_float

            data_to_return = {
                "Parcel": parcel,
                "Improvement Value": improvement_value,
                "Improvement Value Float": improvement_value_float,
                "Land Value": land_value,
                "Land Value Float": land_value_float,
                "Personal Property Value": personal_property_value,
                "Personal Property Value Float": personal_property_value_float,
                "Calculated Total Value": calculated_total_value, # Sum of components
                "Assessment Rate": taxable_property, # This was 'Taxable Property' before, ensure consistency
                "Tax Rate": tax_rate,
            }
            if total_appraised_value: # Add if found
                 data_to_return["Total Appraised Value (from page)"] = total_appraised_value

            return data_to_return
        else:
            logger.error(f"Failed to fetch details from {link}: HTTP {response.status_code}.")
            return {} # Return empty dict on HTTP error

    except requests.RequestException as e:
        logger.error(f"Request error fetching details from {link}: {e}", exc_info=True)
        raise # Re-raise to be handled by the caller, possibly retry decorator
    except Exception as e:
        logger.error(f"Unexpected error processing details from {link}: {e}", exc_info=True)
        raise # Re-raise for visibility or specific handling by caller
