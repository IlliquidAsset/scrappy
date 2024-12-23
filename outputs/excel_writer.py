import openpyxl
from utils.normalizer import normalize_text  # Assuming the normalization function is in utils/normalizer.py

def _convert_to_number(value):
    """Convert text to a numeric value, handling commas, dollar signs, and non-numeric characters."""
    try:
        # Remove percentage signs, "x", and whitespace, then convert to float
        cleaned_value = value.replace(",", "").replace("$", "").replace("%", "").replace("x", "").strip()
        return float(cleaned_value)
    except (ValueError, AttributeError):
        return ""

def write_to_excel(data, filename):
    """Write data to an Excel file matching the required format."""
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "enter data"

    # Define the exact column headers
    headers = [
        "Input Name", "Matched Name", "Address", "Account", "Year",
        "Parcel", "Improvement Value", "Land Value", "Personal Property Value",
        "Assessment Rate", "Tax Rate", "Total Value", "Assessed Value", "Tax"
    ]
    sheet.append(headers)

    # Populate rows with scraped data
    for item in data:
        # Clean and convert the numeric values
        improvement_value = _convert_to_number(item.get("Improvement Value", ""))
        land_value = _convert_to_number(item.get("Land Value", ""))
        personal_property_value = _convert_to_number(item.get("Personal Property Value", ""))
        assessment_rate = _convert_to_number(item.get("Assessment Rate", ""))
        tax_rate = _convert_to_number(item.get("Tax Rate", ""))
        total_value = improvement_value + land_value
        assessed_value = total_value * (assessment_rate / 100 if assessment_rate else 0)
        tax = assessed_value * (tax_rate / 100 if tax_rate else 0)

        # Append the row
        sheet.append([
            item.get("Input Name", ""),
            item.get("Matched Name", ""),
            item.get("Address", ""),
            item.get("Account", ""),
            item.get("Year", ""),
            item.get("Parcel", ""),
            improvement_value,
            land_value,
            personal_property_value,
            f"{assessment_rate}%",  # Keep it formatted as a percentage
            f"{tax_rate}",  # Tax rate as a decimal
            total_value,
            assessed_value,
            tax,
        ])

    wb.save(filename)
    print(f"Data written to {filename}")
