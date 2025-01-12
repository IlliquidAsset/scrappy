# Scrappy - Command-Line Tool for Property Data Scraping

Scrappy is a command-line tool designed for scraping property tax data and generating detailed reports. With its customizable workflows and dynamic match-confirmation features, Scrappy empowers users to gather property-related insights efficiently.

---

## Getting Started with ScrappyLauncher.bat
For users who prefer a simpler setup, Scrappy now includes a convenient batch file: **ScrappyLauncher.bat**.

### What is ScrappyLauncher.bat?
ScrappyLauncher.bat is a Windows batch file designed to automate the installation and execution of Scrappy. It eliminates the need for technical know-how and sets up everything for you, including:
- Checking for required tools like Git and Python.
- Installing missing dependencies.
- Cloning or updating Scrappy's repository.
- Running Scrappy's main functionality.

### How to Use ScrappyLauncher.bat
1. **Download ScrappyLauncher.bat**:
   - Navigate to the `/dist` folder in this repository.
   - Download the `ScrappyLauncher.bat` file to a location on your computer (e.g., your Desktop).

2. **Run ScrappyLauncher.bat**:
   - Double-click the file to execute it. A command prompt window will appear.

3. **Follow the Prompts**:
   - The batch file will:
     - Check for Git and Python. If they are missing, it will guide you to install them.
     - Clone the Scrappy repository if it's not already present.
     - Pull the latest updates if Scrappy is already installed.
     - Install necessary dependencies.
     - Launch Scrappy for you to use.

4. **Enter Your Input**:
   - Provide the requested information in the command prompt, such as the locale, tax year, and owner names.

### Why Use ScrappyLauncher.bat?
- **Beginner-Friendly**: No need to understand Python or Git commands.
- **Automatic Setup**: Handles all installations and updates for you.
- **Consistent Execution**: Ensures Scrappy runs in the correct environment every time.

---

## Overview
**Currently supports the 2024 Tax Year and locales using MyGovOnline, including:**
- Nashville (Davidson County), TN
- Sumner County, TN (may not work)
- Montgomery County, TN

Additional locales can be added with minimal configuration.

Scrappy is perfect for:
- **Property Managers**: Collect property tax details and generate comprehensive reports.
- **Developers**: Integrate Scrappy into larger data pipelines.
- **Businesses**: Automate repetitive property data scraping tasks.

Key Features:
- **Fuzzy Match Confirmation**: Handle ambiguous matches with interactive or programmatic confirmations.
- **PDF and Excel Outputs**: Automatically download property bills and write results to Excel.
- **JSON Integration**: Produce structured JSON for seamless integration with other tools.
- **Locale Selection**: Dynamically choose supported locales before starting a search.
- **Dynamic Record Handling**: Ensures all records, even with similar attributes, are accurately captured and processed.

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
- **Enhanced CLI Logs**: Provides clear summaries and reduces verbosity in logs.

---

## Installation
### Prerequisites
- **Python 3.8+** installed.
- Required Python packages (install with `pip install -r requirements.txt`).

### Installation Steps
1. Clone the repository:
   ```bash
   git clone https://github.com/IlliquidAsset/scrappy/
   cd scrappy
   ```

2. Install dependencies:
   ```bash
   pip install -r requirements.txt
   ```

3. Verify installation:
   ```bash
   python main.py
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

### Locale and Tax Year Selection
- Scrappy prompts you to select a **locale** from a list of supported municipalities.
- By default, Scrappy searches the latest tax year (e.g., 2024). You can override this by providing a specific tax year when prompted.

### Environment Variables
You can bypass CLI input by setting environment variables:
- **SCRAPPY_OWNERS**: A semicolon-separated list of owner names.
- **SCRAPPY_EXTERNAL_CONFIRMATION**: Set to `true` to delegate match confirmations to an external handler.
- **SCRAPPY_LOCALE**: Specify the locale (e.g., `davidson-tn`, `sumner-tn`).
- **SCRAPPY_TAX_YEAR**: Specify the tax year (e.g., `2024`).

Example:
```bash
export SCRAPPY_OWNERS="John Smith;Jane Doe"
export SCRAPPY_LOCALE="sumner-tn"
export SCRAPPY_TAX_YEAR="2023"
python main.py
```

### Outputs
- **Excel File**: `outputs/output.xlsx`
- **PDFs**: Stored in `outputs/pdfs/`
- **JSON**: Produced as part of the CLI output for API integrations.

### Example Workflow
1. Run `python main.py` to start Scrappy.
2. Select the desired locale and tax year interactively or set them via environment variables.
3. Enter owner names interactively or set the `SCRAPPY_OWNERS` environment variable.
4. Confirm matches interactively (if required).
5. View outputs in the `outputs/` folder:
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
    "excel_file": "outputs/output.xlsx",
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
- Logs include locale and tax year for clearer insights and are formatted for readability with color-coded output.

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
- [x] Improve logging for clearer debugging.
- [x] Enhance error recovery when server errors occur.
- [x] Add more robust unit tests for edge cases.
- [ ] Make sure BeautifulSoup reads the links on the last column so that it works across all locales with this provider (i.e.: Sumner County)

### Medium-Term Goals
- **Customizable Reports**: Allow users to define their own report templates.
- **Advanced Integrations**: Support for third-party APIs to push data directly into external systems.
- **Dynamic Record Parsing**: Automatically handle cases of multiple matching records for the same owner.

### Long-Term Goals
- **GUI Interface**: Provide a desktop application for non-technical users.
- **Locale Expansion**: Extend support to all counties using MyGovOnline.
- **Performance Optimization**: Implement multithreading or asynchronous requests for handling large datasets efficiently.

---

## Contributions
Contributions are welcome! If you have ideas for new features or ways to improve Scrappy, feel free to submit an issue or a pull request.

---

## Contact
Developed by Kendrick Kirk. For inquiries, open an issue on GitHub or contact directly.

