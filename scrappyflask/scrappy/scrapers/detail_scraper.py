"""Detail scraper implementation for property details"""
import json

def scrape_details(property_url):
    """
    Scrape detailed property information from a given URL
    Args:
        property_url (str): URL to the property details page
    Returns:
        dict: Detailed property information
    """
    # Mock implementation for testing
    details = {
        "Account": "123456",
        "Year": "2024",
        "Tax Rate": "3.788",
        "Additional Details": {
            "Zone": "Residential",
            "Last Sale Date": "2023-01-01",
            "Last Sale Price": "$1,500,000"
        }
    }
    
    return details
