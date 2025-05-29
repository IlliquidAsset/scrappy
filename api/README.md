# Scrappy API Documentation

## 1. Overview

The Scrappy API provides endpoints to initiate, manage, and retrieve data from property scraping jobs. It allows users to scrape property tax information for specified owner names within supported locales and tax years. The API handles background processing of scraping tasks, user confirmation for potential matches, and provides access to session-specific logs and output files.

## 2. Getting Started

### Running the API Server

To run the Scrappy API server, navigate to the project's root directory (where `app.py` is located) and use Uvicorn:

```bash
uvicorn app:app --host 0.0.0.0 --port 8080
```

You can change the port using the `--port` argument or by setting the `PORT` environment variable.

### Environment Variables

The following environment variables should be configured for the API to operate correctly:

-   **`PORT`**: (Optional) The port on which the Uvicorn server will run. Defaults to `8080` if not set.
    -   Example: `PORT=8000`
-   **`DATABASE_URL`**: The connection string for the database used by the confirmation system. This database stores pending and completed user confirmations for property matches. If not set, it defaults to a local SQLite database (`sqlite:///scrappy_confirmations.db`).
    -   Example (PostgreSQL): `DATABASE_URL="postgresql://user:password@host:port/dbname"`
    -   Example (SQLite): `DATABASE_URL="sqlite:///./data/persistent_confirmations.db"`
-   **`LOG_LEVEL`**: (Optional) Controls the logging level for the application. Defaults to `INFO`. Other common values include `DEBUG`, `WARNING`, `ERROR`.
    -   Example: `LOG_LEVEL=DEBUG`

## 3. Session Management

A `session_id` is crucial for interacting with the API. It's a unique identifier (e.g., a UUID) that groups all operations related to a specific scraping request.

-   **Providing a `session_id`**: When initiating a scrape job via the `POST /scrape` endpoint, you **must** provide a `session_id` in the request body. This allows you to track the job, retrieve its logs, and access any generated files.
-   **Role**: The `session_id` is used as a path parameter in endpoints like `/logs/{session_id}` and `/files/{session_id}` to fetch session-specific information. It's also used in the confirmation flow to link user responses back to the correct scraping context.

## 4. API Endpoints

Below is a detailed description of each API endpoint.

---

### Root

-   **Method:** `GET`
-   **Path:** `/`
-   **Purpose:** Provides basic API information and a list of available endpoints for discovery.
-   **Request:** None
-   **Response:**
    -   **Status Code:** `200 OK`
    -   **Body:**
        ```json
        {
            "name": "Scrappy API",
            "version": "v1.0.0", // Current API version
            "endpoints": {
                "POST /scrape": "Start scraping with provided parameters (owner names, locale, tax year).",
                "POST /confirm": "Submit confirmation for a potential property match.",
                "GET /files/{session_id}": "Get a list of PDF files generated during a session.",
                "GET /locales": "Get a list of supported locales for scraping.",
                "GET /logs/{session_id}": "Retrieve logs for a specific scraping session.",
                "GET /health": "Check the health status of the API."
            }
        }
        ```

---

### Health Check

-   **Method:** `GET`
-   **Path:** `/health`
-   **Purpose:** Returns the health status of the API. Useful for monitoring.
-   **Request:** None
-   **Response:**
    -   **Status Code:** `200 OK`
    -   **Body:**
        ```json
        {
            "status": "healthy",
            "version": "v1.0.0" // Current API version
        }
        ```

---

### Get Supported Locales

-   **Method:** `GET`
-   **Path:** `/locales`
-   **Purpose:** Retrieves a list of locales (e.g., counties, cities) supported by the scraper.
-   **Request:** None
-   **Response:**
    -   **Status Code:** `200 OK`
    -   **Body:** A dictionary mapping locale codes to human-readable names.
        ```json
        {
            "locales": {
                "davidson-tn": "Nashville/Davidson County, TN",
                "sumner-tn": "Sumner County, TN",
                "montgomery-tn": "Montgomery County, TN"
                // ... other supported locales
            }
        }
        ```

---

### Start Scraping Job

-   **Method:** `POST`
-   **Path:** `/scrape`
-   **Purpose:** Initiates a new property scraping job. The actual scraping is performed as a background task.
-   **Request:**
    -   **Body (JSON):**
        ```json
        {
            "session_id": "your-unique-session-id-123",
            "owners": "Doe John;Smith Jane Alice",
            "locale": "davidson-tn",
            "tax_year": "2023"
        }
        ```
        -   `session_id` (string, required): A unique identifier for this scraping session (e.g., UUID). Max length 36.
        -   `owners` (string, required): A semicolon-separated string of owner names to search for. Max length 1000.
        -   `locale` (string, required): The locale code (e.g., 'davidson-tn') to target. Must be one of the locales from `GET /locales`. Max length 50.
        -   `tax_year` (string, optional): The tax year for which to scrape data. Defaults to "2024". Must be 4 digits.
-   **Response:**
    -   **Status Code:** `200 OK` (Indicates the job was successfully initiated)
    -   **Body:**
        ```json
        {
            "status": "success",
            "message": "Scraping job successfully initiated.",
            "session_id": "your-unique-session-id-123",
            "data": {
                "owners": "Doe John;Smith Jane Alice",
                "locale": "davidson-tn",
                "tax_year": "2023"
            }
        }
        ```
    -   **Error Status Codes:**
        -   `422 Unprocessable Entity`: If the request body fails validation (e.g., missing fields, invalid locale). The response detail will contain more information.
        -   `500 Internal Server Error`: If an unexpected error occurs during job initiation.
            ```json
            {
                "detail": "An unexpected server error occurred while initiating the scrape request. Please check server logs for session ID 'your-unique-session-id-123' if provided, or contact support if the issue persists."
            }
            ```

---

### Submit Confirmation

-   **Method:** `POST`
-   **Path:** `/confirm`
-   **Purpose:** Submits a user's confirmation (yes/no) for a potential property match that requires verification. This is part of the interactive confirmation flow (see Section 6).
-   **Request:**
    -   **Body (JSON):**
        ```json
        {
            "session_id": "your-unique-session-id-123",
            "confirmation": "yes",
            "confirmation_id": "confirmation-specific-uuid-456"
        }
        ```
        -   `session_id` (string, required): The session ID associated with the confirmation. Max length 36.
        -   `confirmation` (string, required): User's response, must be either "yes" or "no".
        -   `confirmation_id` (string, optional): The specific ID of the confirmation being responded to. If `null` or omitted, the API attempts to find the latest pending confirmation for the given `session_id`. Max length 36.
-   **Response:**
    -   **Status Code:** `200 OK`
    -   **Body:**
        ```json
        {
            "status": "success",
            "data": {
                "session_id": "your-unique-session-id-123",
                "confirmation": "yes",
                "confirmation_id": "confirmation-specific-uuid-456"
            },
            "message": "Confirmation received successfully."
        }
        ```
    -   **Error Status Codes:**
        -   `404 Not Found`: If no pending confirmation matching the criteria is found.
            ```json
            {
                "detail": "No pending confirmation found for session your-unique-session-id-123 and confirmation ID 'confirmation-specific-uuid-456'. Please ensure the session is active and the confirmation ID is correct if provided."
            }
            ```
        -   `422 Unprocessable Entity`: If the request body fails validation.
        -   `500 Internal Server Error`: If an unexpected error occurs.
            ```json
            {
                "detail": "An unexpected error occurred while processing your confirmation. Please try again or contact support."
            }
            ```

---

### Get Session Logs

-   **Method:** `GET`
-   **Path:** `/logs/{session_id}`
-   **Purpose:** Retrieves logs for a specific scraping session. This is useful for monitoring progress and for the confirmation flow.
-   **Request:**
    -   **Path Parameters:**
        -   `session_id` (string, required): The ID of the scraping session.
    -   **Query Parameters:**
        -   `since` (string, optional): ISO 8601 formatted timestamp (e.g., `2023-10-26T10:00:00Z`). If provided, only logs generated after this time are returned.
        -   `limit` (integer, optional): Maximum number of log entries to return. Defaults to `100`.
-   **Response:**
    -   **Status Code:** `200 OK`
    -   **Body:**
        ```json
        {
            "status": "success",
            "session_id": "your-unique-session-id-123",
            "logs": [
                // Array of log entry strings or structured log objects,
                // depending on core.utils.session_logger implementation.
                // Example if logs are strings:
                "INFO: Starting background scraping for session your-unique-session-id-123",
                "INFO: Found 5 initial property results for session your-unique-session-id-123",
                "INFO: {\"status\": \"confirmation_required\", \"confirmation_id\": \"conf-uuid-1\", ...}"
            ],
            "count": 3 // Number of log entries returned
        }
        ```
    -   **Error Status Codes:**
        -   `500 Internal Server Error`: If an error occurs while retrieving logs.
            ```json
            {
                "detail": "An error occurred while retrieving logs for session your-unique-session-id-123."
            }
            ```

---

### Get Session Files

-   **Method:** `GET`
-   **Path:** `/files/{session_id}`
-   **Purpose:** Retrieves a paginated list of PDF files generated for a given session (e.g., tax bills). Note: PDF generation is a potential feature; the current API provides the endpoint, but actual PDF generation depends on the scraper implementation.
-   **Request:**
    -   **Path Parameters:**
        -   `session_id` (string, required): The ID of the scraping session.
    -   **Query Parameters:**
        -   `page` (integer, optional): The page number for pagination (1-indexed). Defaults to `1`.
        -   `per_page` (integer, optional): The number of files to list per page. Defaults to `50`.
-   **Response:**
    -   **Status Code:** `200 OK`
    -   **Body:**
        ```json
        {
            "session_id": "your-unique-session-id-123",
            "files": [
                "property_123_SMITH_JOHN.pdf",
                "property_456_DOE_JANE.pdf"
            ],
            "file_count": 2,
            "pagination": {
                "page": 1,
                "per_page": 50,
                "total": 2,
                "pages": 1,
                "has_next": false,
                "has_prev": false
            }
        }
        ```
        If no PDF folder exists or no files are found:
        ```json
        {
            "session_id": "your-unique-session-id-123",
            "files": [],
            "file_count": 0,
            "pagination": {
                "page": 1,
                "per_page": 50,
                "total": 0,
                "pages": 0,
                "has_next": false,
                "has_prev": false
            }
        }
        ```
    -   **Error Status Codes:**
        -   `500 Internal Server Error`: If an error occurs while retrieving the file list.
            ```json
            {
                "detail": "An error occurred while retrieving files for session your-unique-session-id-123."
            }
            ```

## 5. Scraping Workflow

A typical interaction with the Scrappy API follows these steps:

1.  **Initiate Scrape:** The client sends a `POST` request to `/scrape` with the `session_id`, owner names, locale, and tax year.
2.  **Background Processing:** The API validates the request, returns an immediate success response, and starts a background task to perform the actual scraping. This task involves:
    a.  Scraping initial property data (e.g., lists of properties matching owner names).
    b.  For each found property, scraping detailed information.
3.  **Monitor Logs (Optional):** The client can periodically send `GET` requests to `/logs/{session_id}` to monitor the progress of the scraping job and check for any messages, including confirmation requests.
4.  **Handle Confirmations (If Required):** If the logs indicate that a confirmation is required for a potential property match (see Section 6), the client uses the information from the log to send a `POST` request to `/confirm`. The scraping process for that specific property path might pause until confirmation is received or times out (timeout behavior is internal to the scraper's confirmation utility).
5.  **Retrieve Results/Files:** Once the scraping job is expected to be complete (or partially complete), the client can send `GET` requests to `/files/{session_id}` to retrieve a list of generated PDF files (if any). The primary data (property information) is currently processed in memory by the background task; a future enhancement might involve storing this data and providing an endpoint to retrieve it.

## 6. Confirmation Flow

When the scraper encounters a property record where the owner name is a partial match (but not an exact match) to the input name, it may require user confirmation. This flow is handled via the API as follows:

1.  **Signal for Confirmation:**
    When `core.utils.confirmation.ask_confirmation` is called in `external_mode` (which is set to `true` by `process_scraping` in `app.py`), it does not prompt via CLI. Instead, it prints a JSON object to its standard output. This output is captured as part of the session logs.
    The client application should monitor the logs retrieved from `GET /logs/{session_id}` for JSON objects matching this structure:

    ```json
    {
        "status": "confirmation_required",
        "confirmation_id": "unique-confirmation-uuid",
        "owner": "INPUT_OWNER_NAME_SEARCHED",
        "match": "MATCHED_OWNER_NAME_FOUND",
        "address": "123 Main St, Anytown, USA",
        "session_id": "your-unique-session-id-123"
    }
    ```
    -   `status`: Always "confirmation_required".
    -   `confirmation_id`: A unique ID for this specific confirmation request. This **must** be used when submitting the confirmation.
    -   `owner`: The original owner name the client searched for.
    -   `match`: The potential matching owner name found by the scraper.
    -   `address`: The address of the property associated with the `match`.
    -   `session_id`: The session ID for this scraping job.

2.  **Submit Confirmation:**
    Upon identifying a "confirmation_required" message in the logs, the client application (or a human operator reviewing the logs) should decide if the `match` is correct for the given `owner` and `address`.
    The client then sends a `POST` request to the `/confirm` endpoint with the following body:

    ```json
    {
        "session_id": "your-unique-session-id-123", // Must match the session_id from the log
        "confirmation": "yes", // or "no"
        "confirmation_id": "unique-confirmation-uuid" // Must match the confirmation_id from the log
    }
    ```
    -   `confirmation`:
        -   `"yes"`: Confirms that the `match` is the correct property. The scraper will then proceed with this property.
        -   `"no"`: Rejects the match. The scraper will likely discard this potential property and continue.

3.  **Scraper Continues:** The `ask_confirmation` function on the server side (within the scraping task) polls the database for the response associated with the `confirmation_id`. Once the client submits the confirmation via the `/confirm` endpoint, the database record is updated, and the `ask_confirmation` function returns the decision (`True` for "yes", `False` for "no") to the scraper, allowing it to proceed. If no confirmation is received within a timeout period (e.g., 5 minutes, as configured in `core.utils.confirmation.py`), it will default to `False`.
```
