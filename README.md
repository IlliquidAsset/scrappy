# Scrappy - Command-Line Tool for Property Data Scraping

Scrappy is a powerful and flexible command-line tool designed for scraping property data and generating detailed reports. With its customizable workflows and dynamic match-confirmation features, Scrappy empowers users to gather property-related insights efficiently.

---

## Overview
 **Currently only works for 2024 Tax Year, Nashville (Davidson County), TN**
Scrappy is perfect for:
- **Property Managers**: Collect property tax details and generate comprehensive reports.
- **Developers**: Integrate Scrappy into larger data pipelines.
- **Businesses**: Automate repetitive property data scraping tasks.

Key Features:
- **Fuzzy Match Confirmation**: Handle ambiguous matches with interactive or programmatic confirmations.
- **PDF and Excel Outputs**: Automatically download property bills and write results to Excel.
- **JSON Integration**: Produce structured JSON for seamless integration with other tools.

---

## Features
### 1. Intelligent Scraping
Scrappy automatically navigates through web pages, extracts key property details, and handles server-side challenges like rate limiting and session persistence.

### 2. Customizable Match Logic
- Built-in **fuzzy logic** for owner name matching.
- Interactive CLI or API-based confirmation for ambiguous results.

### 3. Comprehensive Output
- **Excel Report**: Organizes property data into a clear, user-friendly format.
- **PDF Downloads**: Saves bills for each property in a structured directory.
- **JSON Responses**: Delivers detailed, machine-readable outputs.

---

## Installation
### Prerequisites
- **Python 3.8+** installed.
- Required Python packages (install with `pip install -r requirements.txt`).

### Installation Steps
1. Clone the repository:
   ```bash
   git clone <repository-url>
   cd scrappy
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Verify installation:
   ```bash
   python main.py --help
   ```

---

## Usage
### Basic Command-Line Execution
Scrappy accepts a list of owner names and generates an Excel report and PDFs:
```bash
python main.py
```

- When prompted, input owner names separated by semicolons:
  ```
  Enter owner names (semicolon-separated): John Smith; Jane Doe
  ```

### Environment Variables
You can bypass CLI input by setting environment variables:
- **SCRAPPY_OWNERS**: A semicolon-separated list of owner names.
- **SCRAPPY_EXTERNAL_CONFIRMATION**: Set to `true` to delegate match confirmations to an external handler.

Example:
```bash
export SCRAPPY_OWNERS="John Smith;Jane Doe"
python main.py
```

### Outputs
- **Excel File**: `outputs/output_davidsonco.xlsx`
- **PDFs**: Stored in `outputs/pdfs/`
- **JSON**: Produced as part of the CLI output for API integrations.

### Example Workflow
1. Run `python main.py` to start Scrappy.
2. Enter owner names interactively or set the `SCRAPPY_OWNERS` environment variable.
3. Confirm matches interactively (if required).
4. View outputs in the `outputs/` folder:
   - **Excel Report**: Comprehensive property details.
   - **PDFs**: Downloaded property bills.
   - **JSON**: For programmatic use.

---

## JSON Integration
Scrappy outputs structured JSON containing:
- File paths for generated Excel reports and PDFs.
- Detailed property data, including:
  - Owner information.
  - Property values.
  - Tax details.
- Errors (if any).

Example JSON Output:
```json
{
    "excel_file": "outputs/output_davidsonco.xlsx",
    "pdf_folder": "outputs/pdfs",
    "property_data": [
        {
            "Input Name": "John Smith",
            "Matched Name": "SMITH, JOHN",
            "Address": "123 Main St",
            "Parcel": "001",
            "Improvement Value": "$100,000",
            "Land Value": "$50,000",
            "Tax Rate": "3.2%"
        }
    ],
    "errors": []
}
```

---

## Debugging and Logging
### Debugging Tips
- Scrappy writes detailed logs to `outputs/errors.log`.
- Use the logs to troubleshoot issues like server errors or failed downloads.
- Adjust fuzzy match thresholds in `scrapers/property_scraper.py` to refine matching logic.

### Common Issues and Solutions
1. **No Results Found**:
   - Ensure the input owner name is accurate.
   - Check the `outputs/errors.log` for server-related errors.

2. **500 Server Error**:
   - Scrappy automatically retries after encountering server issues.
   - If the error persists, verify the target website’s availability.

---

## Roadmap
### Immediate Goals
1. Improve logging for clearer debugging.
2. Enhance error recovery when server errors occur.
3. Add more robust unit tests for edge cases.

### Long-Term Goals
- **Customizable Reports**: Allow users to define their own report templates.
- **Advanced Integrations**: Support for third-party APIs to push data directly into external systems.
- **GUI Interface**: Provide a desktop application for non-technical users.

---

## Contributions
Contributions are welcome! If you have ideas for new features or ways to improve Scrappy, feel free to submit an issue or a pull request.

---

## Contact
Developed by Kendrick Isaac Reed Kirk. For inquiries, open an issue on GitHub or contact directly.
