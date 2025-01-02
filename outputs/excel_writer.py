import openpyxl
from utils.normalizer import normalize_text

# Utility to convert text to numeric values
def _convert_to_number(value):
    """Convert text to a numeric value, handling commas, dollar signs, and non-numeric characters."""
    try:
        cleaned_value = value.replace(",", "").replace("$", "").replace("%", "").replace("x", "").strip()
        return float(cleaned_value)
    except (ValueError, AttributeError):
        return ""

# Write data to Excel
def write_to_excel(data, filename):
    """Write scraped data to an Excel file."""
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "enter data"

    # Define headers
    headers = [
        "Input Name", "Matched Name", "Address", "Account", "Year", "Locale",
        "Parcel", "Improvement Value", "Land Value", "Personal Property Value",
        "Assessment Rate", "Tax Rate", "Total Value", "Assessed Value", "Tax"
    ]
    sheet.append(headers)

    # Populate rows with scraped data
    for row_index, item in enumerate(data, start=2):
        # Add data to the sheet
        sheet.append([
            item.get("Input Name", ""),
            item.get("Matched Name", ""),
            item.get("Address", ""),
            item.get("Account", ""),
            item.get("Year", ""),
            item.get("Locale", ""),
            item.get("Parcel", ""),
            _convert_to_number(item.get("Improvement Value", "")),
            _convert_to_number(item.get("Land Value", "")),
            _convert_to_number(item.get("Personal Property Value", "")),
            f"{_convert_to_number(item.get('Assessment Rate', ''))}%",  # Keep percentage
            _convert_to_number(item.get("Tax Rate", "")),
            None,  # Placeholder for Total Value formula
            None,  # Placeholder for Assessed Value formula
            None   # Placeholder for Tax formula
        ])

        # Insert formulas
        sheet[f"M{row_index}"] = f"=H{row_index}+I{row_index}+j{row_index}"  # Total Value
        sheet[f"N{row_index}"] = f"=M{row_index}*(K{row_index})"  # Assessed Value
        sheet[f"O{row_index}"] = f"=N{row_index}*(L{row_index}/100)"  # Tax

    # Save the workbook
    wb.save(filename)
    print(f"Data written to {filename}")
