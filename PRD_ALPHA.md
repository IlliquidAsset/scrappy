# Scrappy - Alpha Product Requirements Document (PRD)

## 1. Introduction

This document outlines the product requirements for the Alpha release of Scrappy. The Alpha release aims to provide a functional and configurable property data scraping tool, focusing on core scraping capabilities, support for a selection of diverse Tennessee counties, and usability for technical users (developers, data analysts) via both CLI and API.

## 2. Goals for Alpha

*   **Validate Configuration-Driven Architecture:** Demonstrate that the new county-specific configuration system can effectively support scraping for different website structures.
*   **Core Functionality Stability:** Ensure reliable data extraction (property details, tax info, PDF links) for a defined set of Tennessee counties.
*   **Developer/Technical User Enablement:** Provide a usable CLI and a functional API for programmatic access.
*   **Clear Documentation:** Offer clear instructions for setup, usage, and (critically) how to configure Scrappy for new counties.
*   **Establish Foundation for Beta/GA:** Create a stable base that can be expanded upon for future releases with more features, broader county support, and enhanced user interfaces.

## 3. Target Users (Alpha)

*   **Data Analysts / Real Estate Professionals:** Users who need to gather property tax data for analysis, reporting, or due diligence, and are comfortable with CLI tools or basic API interaction.
*   **Developers:** Users who want to integrate Scrappy's data extraction capabilities into their own applications or data workflows.
*   **Internal Team / Early Adopters:** Users actively involved in testing and providing feedback to shape the product.

## 4. Key Features & Functionality (Alpha Scope)

### 4.1. Configurable Scraping Engine
*   **County Configuration Files:** Scrappy must load and interpret county-specific JSON configuration files (from `configs/`) that define URLs, request parameters, and CSS selectors for data extraction.
*   **Support for MyGovOnline Platform:** Demonstrate robust scraping for counties using the MyGovOnline platform (e.g., Davidson, Sumner, Montgomery - building on existing work).
*   **Support for New Diverse Counties:** Successfully configure and scrape data from at least 2-3 additional Tennessee counties that use *different* website platforms/structures than MyGovOnline. This is a key validation point for the architecture.
*   **Data Extraction:** For each supported county, the system must extract:
    *   Owner Name(s)
    *   Property Address
    *   Account/Parcel ID
    *   Tax Year
    *   Key Property Values (Land Value, Improvement Value, Total/Appraised Value as available)
    *   Taxable Assessment/Value
    *   Tax Rate (for the specified year)
    *   Link to Property Detail Page
    *   Link to PDF Tax Bill (if available and directly linkable)
*   **Pagination:** Handle paginated search results correctly.

### 4.2. Command-Line Interface (CLI - `main.py`)
*   **Interactive Mode:** Allow users to select locale, input tax year, and owner names.
*   **Environment Variable Configuration:** Support for bypassing prompts via environment variables (e.g., `SCRAPPY_OWNERS`, `SCRAPPY_LOCALE`).
*   **Output:**
    *   Generate an Excel file summarizing scraped data.
    *   Download PDF tax bills to a structured directory.
    *   Provide console output indicating progress and errors.
*   **Confirmation Flow:** Support interactive CLI confirmation for ambiguous owner name matches (including address context).

### 4.3. API (FastAPI - `app.py`)
*   **Endpoints:** Provide functional and documented endpoints for:
    *   Initiating a scrape job (POST /scrape).
    *   Confirming matches (POST /confirm).
    *   Listing supported locales (GET /locales).
    *   Retrieving session logs (GET /logs/{session_id}).
    *   Listing downloaded files (GET /files/{session_id}).
    *   Health check (GET /health).
*   **Data Enrichment:** API scraping jobs must include detailed data from property detail pages.
*   **Background Task Processing:** Scraping jobs initiated via API run as background tasks.
*   **Confirmation Flow (API):** Support the external confirmation flow (logging `confirmation_required` JSON, client uses `/confirm` endpoint).

### 4.4. Data Management & Output
*   **PDF Downloads:** Consistent PDF download capability for CLI and (if links are made available) potentially via API.
*   **Excel Output (CLI):** The CLI must produce a usable Excel summary.
*   **JSON Output (API):** API endpoints should return structured JSON responses. Logs related to `confirmation_required` are also JSON.
*   **Database (Confirmation):** The confirmation system (`core/utils/confirmation.py`) uses a database to store and manage confirmation requests.

### 4.5. Documentation
*   **Main README (`README.md`):** Provides a full-stack overview, setup, and usage for CLI & API.
*   **API README (`api/README.md`):** Detailed API endpoint documentation.
*   **County Configuration Guide:** Clear documentation (e.g., `docs/county_configurations.md` or similar) explaining the JSON configuration file structure and how to add new counties.
*   **Inline Code Comments:** Key parts of the codebase (especially scrapers, API, configuration loaders) should be well-commented.

## 5. User Stories (Examples)

*   **As a Data Analyst (CLI User):** I want to easily select a supported Tennessee county, input a list of owner names and a tax year, so that I can receive an Excel file with their property tax details and downloaded PDF bills.
*   **As a Developer (API User):** I want to programmatically start a scraping job for a list of owners in a specific county and tax year, so that I can integrate property data into my application.
*   **As a Developer (API User):** When a scraping job requires name confirmation, I want the API to provide me with the necessary information (owner, match, address, confirmation ID) so that my application can present this to a user and send back the confirmation.
*   **As a Technical User/Admin:** I want to be able to add support for a new Tennessee county by creating a JSON configuration file defining its website URLs and data selectors, so that Scrappy can scrape data from this new county.

## 6. Technical Requirements

*   **Python Version:** Python 3.8+
*   **Dependencies:** Clearly listed in `requirements.txt`.
*   **Configuration-Driven:** Scraping logic for specific counties must be primarily driven by external JSON configuration files.
*   **Error Handling:**
    *   Graceful handling of common website errors (e.g., page not found, server errors from target sites).
    *   Clear logging of errors and scraping progress.
    *   Informative error messages for API clients.
*   **Encoding:** All file handling and text processing should correctly manage character encodings (default to UTF-8 for outputs and configs).

## 7. Alpha Release Criteria (Definition of Done for Alpha)

*   All features listed in Section 4 are implemented and functional.
*   Successful, repeatable scraping for Davidson, Sumner, Montgomery counties using the new configuration system.
*   Successful, repeatable scraping for at least 2 new diverse (non-MyGovOnline if possible) Tennessee counties using the configuration system.
*   All documentation outlined in Section 4.5 is complete and accurate.
*   Known critical bugs or stability issues that prevent core functionality are resolved.
*   The system is usable by target Alpha users (technical users) for the defined scope.

## 8. Out of Scope for Alpha

*   Advanced GUI for non-technical users (beyond very basic web functions if M4 is achieved).
*   Support for counties outside of Tennessee.
*   Automated generation of county configurations (e.g., via UI or ML).
*   Advanced analytics or reporting features.
*   User accounts/authentication beyond basic API key (if implemented).
*   Database migrations (beyond initial schema setup for confirmation DB).
