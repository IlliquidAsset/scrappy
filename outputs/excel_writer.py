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
    for row_index, item in enumerate(data, start=2):  # Start at the second row
        # Append the row data
        sheet.append([
            item.get("Input Name", ""),
            item.get("Matched Name", ""),
            item.get("Address", ""),
            item.get("Account", ""),
            item.get("Year", ""),
            item.get("Parcel", ""),
            _convert_to_number(item.get("Improvement Value", "")),
            _convert_to_number(item.get("Land Value", "")),
            _convert_to_number(item.get("Personal Property Value", "")),
            f"{_convert_to_number(item.get('Assessment Rate', ''))}%",  # Keep as percentage
            f"{_convert_to_number(item.get('Tax Rate', ''))}",  # Tax rate as decimal
            None,  # Placeholder for Total Value formula
            None,  # Placeholder for Assessed Value formula
            None,  # Placeholder for Tax formula
        ])

        # Insert formulas for Total Value, Assessed Value, and Tax
        sheet[f"L{row_index}"] = f"=G{row_index}+H{row_index}"  # Total Value
        sheet[f"M{row_index}"] = f"=L{row_index}*(J{row_index})"  # Assessed Value
        sheet[f"N{row_index}"] = f"=M{row_index}*(K{row_index}/100)"  # Tax

    wb.save(filename)
    print(f"Data written to {filename}")
