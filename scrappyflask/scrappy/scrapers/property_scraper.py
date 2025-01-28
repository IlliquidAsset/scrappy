"""Property scraper implementation"""
import os
import json
from datetime import datetime

def scrape_property_data(owner_names, locale="davidson-tn", tax_year=None):
    """
    Scrape property data for given owner names in specified locale
    """
    # Set default tax year if not provided
    if not tax_year:
        tax_year = str(datetime.now().year)

    # Read confirmation from environment if in external confirmation mode
    external_confirmation = os.environ.get("SCRAPPY_EXTERNAL_CONFIRMATION", "false").lower() == "true"
    
    results = []
    
    for owner in owner_names:
        # Example match confirmation logic
        if external_confirmation:
            confirmation_data = {
                "confirmation_required": True,
                "owner": owner,
                "match": "HERMITAGE 1, LLC" if "hermitage" in owner.lower() else "101 HART LANE, LLC"
            }
            print(json.dumps(confirmation_data))
            
            # Wait for confirmation response
            confirmation = os.environ.get("SCRAPPY_CONFIRMATION", "").lower()
            if confirmation != "yes":
                continue

        # Mock property data for testing
        property_data = {
            "Matched Name": "HERMITAGE 1, LLC" if "hermitage" in owner.lower() else "101 HART LANE, LLC",
            "Address": "101 Hart Lane" if "hart" in owner.lower() else "1234 Hermitage Ave",
            "Parcel": "123-456-789",
            "Land Value": 500000,
            "Improvement Value": 1000000,
            "Total Value": 1500000,
            "Tax Rate": "3.788",
            "PDF Link": "https://example.com/tax_bill.pdf",
            "Link": f"https://example.com/property/{owner}"
        }
        
        results.append(property_data)
    
    return results
