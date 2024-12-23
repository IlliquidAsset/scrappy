# Scrappy ReadMe

## Overview
Scrappy is a Python-based tool designed to scrape property tax data from an online database, populate the relevant information into an Excel spreadsheet, and download associated PDF tax bills. The tool is designed to streamline the process of gathering property tax details and generate a well-organized dataset for further use.

This version has been designed to work with Nashville/Davidson County Tennssee

---

## Features
1. **Data Scraping**:
   - Extracts property details such as parcel, improvement value, land value, personal property value, assessment rate, and tax rate.
   - Populates scraped data into specified columns in the Excel sheet.

2. **PDF Downloading**:
   - Downloads the PDF tax bill for each property and saves it in a designated folder.
   - Renames PDFs using the corresponding parcel number for easy identification.

3. **Excel Integration**:
   - Updates an Excel file with the scraped data.
   - Ensures numeric values are properly formatted for calculations within the spreadsheet.

4. **Error Handling**:
   - Skips rows with missing or invalid links.
   - Logs errors encountered during data scraping or PDF downloading.

5. **Flexible Input**:
   - Allows user input for filtering specific property owner names.

6. **Output Organization**:
   - Saves all data in structured outputs including Excel files, PDF files, and error logs.

---

## Requirements
- Python 3.10+
- Required Libraries:
  - `openpyxl`
  - `requests`
  - `bs4` (BeautifulSoup)
  - `os`

### Installation
1. Clone the repository or copy the script files to your local system.
2. Install dependencies using pip:
   ```bash
   pip install openpyxl requests beautifulsoup4
   ```

---

## Usage

### File Structure
Ensure the following files and folders are present in the same directory:
- `davidsonco.xlsx`: The Excel file containing property data.
- `outputs/pdf`: A folder to store downloaded PDF tax bills (created automatically).

### Excel File Format
The Excel file must include the following columns:

| Column Name                | Column Index | Notes                                   |
|----------------------------|--------------|-----------------------------------------|
| Owner                     | Column A     | Property owner details                 |
| Address                   | Column B     | Property address                       |
| Account #                 | Column C     | Property account number                |
| Year                      | Column D     | Tax year                               |
| Link                      | Column F     | Hyperlink to the "View Bill" page      |
| Parcel                    | Column G     | Will be populated with the parcel ID   |
| Improvement Value         | Column H     | Will be populated with the improvement value |
| Land Value                | Column I     | Will be populated with the land value  |
| Personal Property Value   | Column J     | Will be populated with the personal property value |
| Assessment Rate           | Column L     | Will be populated with the assessment rate (as a decimal) |
| Tax Rate                  | Column M     | Will be populated with the tax rate (as a decimal) |

### Running the Script
1. Place `davidsonco.xlsx` in the same directory as the script.
2. Execute the script:
   ```bash
   python main.py
   ```
3. The script will:
   - Prompt for property owner names (optional).
   - Scrape data for each property in the Excel file.
   - Populate the Excel file with scraped data.
   - Download and save the PDF tax bill for each property in the `outputs/pdf` folder.
   - Generate an error log if any issues occur.

### Output
- Updated `davidsonco.xlsx` file with populated data.
- PDF files saved in the `outputs/pdf` folder, named after the corresponding parcel number and owner.
- An error log (`errors.log`) saved in the `outputs` folder, containing any errors encountered during processing.

---

## Troubleshooting
1. **FileNotFoundError**:
   - Ensure the Excel file (`davidsonco.xlsx`) is present in the same directory as the script.
2. **No valid link found**:
   - Verify that the "Link" column contains valid hyperlinks in the correct format.
3. **Failed to download PDF**:
   - Check if the website is accessible and if the `outputs/pdf` folder has write permissions.

---

## Future Improvements
- Add a GUI for easier user interaction.
- Support for dynamic Excel column mapping.
- Enhanced error handling with detailed logs.
- Option to configure output folder paths.

---

## License
This project is licensed under the MIT License.

---

## Contributors
- Developer: Kendrick Kirk

---

For questions or support, contact: kendrick.kirk@gmail.com

