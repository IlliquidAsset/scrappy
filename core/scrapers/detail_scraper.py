import requests
from bs4 import BeautifulSoup
import logging
from functools import wraps
import time

# Set up logging
logger = logging.getLogger(__name__)

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
def scrape_details(link, tax_year):
    """
    Scrape detailed property information from a property page.

    Args:
        link (str): URL to the property details page.
        tax_year (str): The tax year for which to find the tax rate. This is used
                        to dynamically construct the label for the tax rate
                        (e.g., "2023 Tax Rate:") as websites often change this label
                        based on the selected tax year.

    Returns:
        dict: Detailed property information.
    """
    if not link:
        logger.warning("No link provided for detail scraping")
        return {}

    try:
        response = requests.get(link, timeout=10)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            def safe_find(label):
                """Safely find a value in the table by its label"""
                try:
                    element = soup.find("td", string=label)
                    if not element:
                        logger.debug(f"Label '{label}' not found in {link}")
                        return ""

                    value_element = element.find_next("td")
                    if not value_element:
                        logger.debug(f"Value for '{label}' not found in {link}")
                        return ""

                    return value_element.text.strip()
                except AttributeError as e:
                    logger.warning(f"Error finding '{label}' in {link}: {e}")
                    return ""

            # Extract property details
            parcel = safe_find("Parcel:")
            improvement_value = safe_find("Improvement Value:")
            land_value = safe_find("Land Value:")
            personal_property_value = safe_find("Personal Property Value:")
            taxable_property = safe_find("Taxable Property:").replace("x", "").strip()
            # Dynamically find the tax rate using the provided tax_year.
            tax_rate = safe_find(f"{tax_year} Tax Rate:")

            # Convert monetary values to numbers where appropriate.
            # Log a warning and default to 0 if conversion fails, including original value and link for debugging.
            try:
                improvement_value_float = float(improvement_value.replace('$', '').replace(',', ''))
            except (ValueError, AttributeError):
                logger.warning(f"Could not convert Improvement Value '{improvement_value}' to float for link {link}. Defaulting to 0.", exc_info=True)
                improvement_value_float = 0

            try:
                land_value_float = float(land_value.replace('$', '').replace(',', ''))
            except (ValueError, AttributeError):
                logger.warning(f"Could not convert Land Value '{land_value}' to float for link {link}. Defaulting to 0.", exc_info=True)
                land_value_float = 0

            try:
                personal_property_value_float = float(personal_property_value.replace('$', '').replace(',', ''))
            except (ValueError, AttributeError):
                logger.warning(f"Could not convert Personal Property Value '{personal_property_value}' to float for link {link}. Defaulting to 0.", exc_info=True)
                personal_property_value_float = 0

            # Calculate total value from the successfully converted float values.
            total_value = improvement_value_float + land_value_float + personal_property_value_float

            return {
                "Parcel": parcel,
                "Improvement Value": improvement_value,
                "Improvement Value Float": improvement_value_float,
                "Land Value": land_value,
                "Land Value Float": land_value_float,
                "Personal Property Value": personal_property_value,
                "Personal Property Value Float": personal_property_value_float,
                "Total Value": total_value,
                "Assessment Rate": taxable_property,
                "Tax Rate": tax_rate,
            }
        else:
            logger.error(f"Failed to fetch details from {link}: HTTP {response.status_code}")
            return {}

    except requests.RequestException as e:
        logger.error(f"Request error fetching details from {link}: {e}")
        raise
    except Exception as e:
        logger.error(f"Error processing details from {link}: {e}")
        raise
