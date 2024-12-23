import openpyxl

# Normalization map for address components
NORMALIZATION_MAP = {
    "ln": "Lane",
    "lane": "Lane",
    "dr": "Drive",
    "drive": "Drive",
    "rd": "Road",
    "road": "Road",
    "st": "Street",
    "street": "Street",
    "blvd": "Boulevard",
    "boulevard": "Boulevard",
    "ave": "Avenue",
    "avenue": "Avenue",
    "ct": "Court",
    "court": "Court",
}

def normalize_text(text):
    """Normalize address components based on the normalization map."""
    if not text:
        return ""
    words = text.lower().split()
    normalized_words = [NORMALIZATION_MAP.get(word, word) for word in words]
    return " ".join(normalized_words).title()  # Capitalize each word properly

def _convert_to_number(value):
    """Convert text to a numeric value, handling commas and dollar signs."""
    try:
        return float(value.replace(",", "").replace("$", "").strip())
    except (ValueError, AttributeError):
        return ""


def write_to_excel(data, filename):
    """Write data to an Excel file matching the required format."""
    wb = openpyxl.Workbook()
    sheet = wb.active
    sheet.title = "enter data"

    # Define the exact column headers based on your provided file
    headers = [
        "Input Name", "Matched Name", "Address", "Account", "Year",
        "Parcel", "Tax Value", "Improvement Value", "Land Value",
        "Personal Property Value", "Assessment Rate", "Tax Rate",
        "Calculated Total Tax"
    ]
    sheet.append(headers)

    # Populate rows with scraped data
    for item in data:
        sheet.append([
            item.get("Input Name", ""),
            item.get("Matched Name", ""),
            item.get("Address", ""),
            item.get("Account", ""),
            item.get("Year", ""),
            item.get("Parcel", ""),
            _convert_to_number(item.get("Tax Value", "")),
            _convert_to_number(item.get("Improvement Value", "")),
            _convert_to_number(item.get("Land Value", "")),
            _convert_to_number(item.get("Personal Property Value", "")),
            item.get("Assessment Rate", ""),  # Insert formula or data
            item.get("Tax Rate", ""),  # Insert formula or data
            f"=H{sheet.max_row + 1} * 0.02922"  # Example formula for Total Tax
        ])

    wb.save(filename)
    print(f"Data written to {filename}")
