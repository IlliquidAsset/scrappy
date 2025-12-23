# Scrappy - Alpha Release Roadmap

## Vision for Alpha

The Alpha release of Scrappy aims to deliver a stable and usable platform capable of scraping property tax data from a diverse set of Tennessee counties. This version will focus on validating the configuration-driven architecture, ensuring core features are functional through both CLI and API, and providing clear documentation for users and developers looking to add support for new counties.

## Key Milestones & Themes

The path to Alpha will be organized around the following key themes and milestones. These may be broken down into smaller sprints.

### M1: Solidify Core Configuration & Scraping Engine (Current Focus)

*   **Objective:** Ensure the new configuration-driven scraping engine is robust and well-documented.
*   **Key Results:**
    *   [x] Design and implement JSON-based county configuration file structure.
    *   [x] Refactor core scrapers (`property_scraper.py`, `detail_scraper.py`) to use these configurations.
    *   [x] Update CLI (`main.py`) to load and utilize county configurations.
    *   [ ] **Verify & Finalize Configurations for Initial Counties:**
        *   Create and thoroughly test accurate configuration files for Sumner County (`sumner-tn.json`).
        *   Create and thoroughly test accurate configuration files for Montgomery County (`montgomery-tn.json`).
        *   Ensure Davidson County (`davidson-tn.json`) is fully verified post-refactor.
    *   [ ] **Documentation for County Configuration:** Ensure the generated documentation for creating and understanding county configuration files is integrated into the project's main documentation (manual user step pending).

### M2: Expand County Coverage & Test Diverse Scenarios

*   **Objective:** Prove the flexibility of the configuration system by adding support for several new Tennessee counties, prioritizing those with different website structures or platforms (if not MyGovOnline).
*   **Key Results:**
    *   **Identify Target Counties:** Select 3-5 new Tennessee counties for Alpha support, aiming for diversity in data providers if possible.
    *   **Develop Configurations:** Create and test configuration files for these new counties.
    *   **Refine Scrapers (if needed):** Based on challenges encountered with new counties, make necessary improvements to the core scraping engine or configuration schema for greater flexibility.
    *   **Direct API Investigation:** For each new county, investigate the feasibility of accessing data via direct (potentially undocumented) API endpoints as an alternative to HTML scraping. Implement if viable for at least one new county.

### M3: Enhance Data Management & Persistence

*   **Objective:** Ensure scraped data is consistently managed and can be stored reliably.
*   **Key Results:**
    *   **Database Integration for API:** Ensure the API (`app.py`) can save successfully scraped and detailed property data to the database (using `web/models.py - ScrapingResult`).
    *   **CLI Data to DB (Optional for Alpha, Recommended):** Consider having `main.py` also save its results to the same database for unified data storage.
    *   **Align Confirmation Models:** Update `web/models.py - ScrapingConfirmation` to include the `address` field, consistent with `core/utils/confirmation.py`.
    *   **Basic Data Viewing/Export (Web):** If `web/` components are to be part of Alpha, provide a simple way to view or export scraped data from the database.

### M4: API Finalization & Web Interface (Basic)

*   **Objective:** Ensure the API is feature-complete for Alpha and provide a basic web interface for core tasks.
*   **Key Results:**
    *   **API Feature Parity:** Confirm all core scraping functionalities are accessible and robust via the API.
    *   **Job Status Endpoint (API):** Design and implement an API endpoint to check the status of ongoing or completed scraping jobs initiated via the API.
    *   **Basic Web UI (`web/`):**
        *   Allow users to initiate scrapes (select locale, input names, tax year).
        *   Display scraping job status.
        *   Handle user confirmations if required by a job.
        *   View basic results.
    *   **Authentication (Optional for Alpha):** If time permits and is deemed necessary, implement basic API key authentication for the API.

### M5: Testing, Documentation & Alpha Release Prep

*   **Objective:** Ensure the Alpha release is stable, well-documented, and easy to use for its target audience.
*   **Key Results:**
    *   **Testing:**
        *   Expand unit test coverage for core utilities and scraper components.
        *   Develop integration tests for the CLI and API flows for at least the initially supported counties (Davidson, Sumner, Montgomery) and one new county type.
    *   **Documentation:**
        *   Update main `README.md` to reflect all Alpha features and architecture.
        *   Ensure `api/README.md` is up-to-date.
        *   Review and finalize documentation for county configurations.
        *   User guide for CLI and basic Web UI usage.
    *   **Packaging (Optional):** Consider simple packaging or clear execution instructions for users.
    *   **Alpha Release Candidate:** Tag a version as the Alpha release candidate.

## Post-Alpha Considerations (Beyond this Roadmap)

*   Full GUI application.
*   Advanced reporting and analytics.
*   Support for all Tennessee counties and potentially other states.
*   Machine learning for complex data extraction or validation.

---

This roadmap provides a high-level guide. Detailed sprint planning will break these milestones into smaller, actionable tasks.
