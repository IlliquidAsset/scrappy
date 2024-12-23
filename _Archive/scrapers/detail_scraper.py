import requests
from bs4 import BeautifulSoup

def scrape_details(link):
    if not link:
        return {}
    try:
        response = requests.get(link)
        if response.status_code == 200:
            soup = BeautifulSoup(response.text, "html.parser")

            # Safely extract property details, matching the variables from yesterday
            def safe_find(label):
                try:
                    return soup.find("td", string=label).find_next("td").text.strip()
                except AttributeError:
                    print(f"Warning: Could not find '{label}' in {link}")
                    return ""

            # Variables to match yesterday’s implementation
            parcel = safe_find("Parcel:")
            improvement_value = safe_find("Improvement Value:")
            land_value = safe_find("Land Value:")
            personal_property_value = safe_find("Personal Property Value:")
            assessment_rate = safe_find("Assessment Rate:")
            tax_rate = safe_find("Tax Rate:")
            total_tax = safe_find("Total Tax:")  # Ensure you’re capturing any additional fields

            return {
                "Parcel": parcel,
                "Improvement Value": improvement_value,
                "Land Value": land_value,
                "Personal Property Value": personal_property_value,
                "Assessment Rate": assessment_rate,
                "Tax Rate": tax_rate,
                "Total Tax": total_tax,  # Include if used in Excel
            }
        else:
            print(f"Failed to fetch details from {link}: HTTP {response.status_code}")
            return {}
    except Exception as e:
        print(f"Error fetching details from {link}: {e}")
        return {}
