"""Session-based logging for enriching the UI debug pane"""
import json
import logging
import time
from datetime import datetime
from threading import Lock
import os
from collections import defaultdict, deque
from colorama import Fore, Style, init

# Initialize colorama
init(autoreset=True)

# Set up logger
logger = logging.getLogger(__name__)

# Color mapping for log levels
COLOR_MAP = {
    "debug": Fore.BLUE,
    "info": Fore.WHITE,
    "success": Fore.GREEN,
    "warning": Fore.YELLOW,
    "error": Fore.RED,
}

# Store logs per session
# Using deque with maxlen to prevent memory issues
SESSION_LOGS = defaultdict(lambda: deque(maxlen=500))
SESSION_LOCK = Lock()

def log_to_session(session_id, message, level="info", metadata=None):
    """
    Log a message to a specific session's log buffer and console

    Args:
        session_id (str): Unique session identifier
        message (str): Log message
        level (str): Log level (debug, info, success, warning, error)
        metadata (dict, optional): Additional data to include with the log

    Returns:
        dict: The created log entry
    """
    if level not in COLOR_MAP:
        level = "info"

    # Create log entry
    log_entry = {
        "timestamp": datetime.utcnow().isoformat(),
        "message": message,
        "level": level
    }

    if metadata:
        log_entry["metadata"] = metadata

    # Store in session logs
    with SESSION_LOCK:
        SESSION_LOGS[session_id].append(log_entry)

    # Print to console with appropriate color
    console_output = f"[{log_entry['timestamp']}] [{session_id[:8]}] [{level.upper()}] {message}"
    print(f"{COLOR_MAP[level]}{console_output}{Style.RESET_ALL}")

    # Also log to standard logger for file logging if configured
    log_method = getattr(logger, level if level != "success" else "info")
    log_method(f"[{session_id[:8]}] {message}")

    return log_entry

def get_session_logs(session_id, since=None, limit=100):
    """
    Retrieve logs for a specific session, optionally filtering by timestamp

    Args:
        session_id (str): Unique session identifier
        since (str, optional): ISO timestamp to filter logs after
        limit (int, optional): Maximum number of logs to return

    Returns:
        list: Session log entries
    """
    with SESSION_LOCK:
        if session_id not in SESSION_LOGS:
            return []

        logs = list(SESSION_LOGS[session_id])

    # Filter by timestamp if provided
    if since:
        try:
            since_dt = datetime.fromisoformat(since)
            logs = [log for log in logs if datetime.fromisoformat(log["timestamp"]) > since_dt]
        except (ValueError, TypeError):
            pass

    # Return most recent logs up to limit
    return logs[-limit:]

def clear_session_logs(session_id):
    """
    Clear logs for a specific session

    Args:
        session_id (str): Unique session identifier
    """
    with SESSION_LOCK:
        if session_id in SESSION_LOGS:
            SESSION_LOGS[session_id].clear()

def log_scraping_to_session(session_id, locale, tax_year, message, level="info"):
    """
    Log a scraping event to both console and session logs

    Args:
        session_id (str): Unique session identifier
        locale (str): Locale being scraped
        tax_year (str): Tax year being searched
        message (str): Log message
        level (str): Log level
    """
    metadata = {
        "locale": locale,
        "tax_year": tax_year
    }

    log_to_session(
        session_id=session_id,
        message=message,
        level=level,
        metadata=metadata
    )

    # Also log to console in formatted style
    print(Fore.CYAN + Style.BRIGHT + "\n=== Scraping Log ===")
    print(Fore.MAGENTA + f"Locale: {locale.upper()} | Tax Year: {tax_year}")
    print(COLOR_MAP[level] + Style.BRIGHT + f"Message: {message}")
    print(Fore.CYAN + Style.BRIGHT + "====================\n")

def format_property_summary_for_session(session_id, property_data, excel_file_path, error_log_path):
    """
    Format property summary and log to session

    Args:
        session_id (str): Unique session identifier
        property_data (list): List of property data dictionaries
        excel_file_path (str): Path to the generated Excel file
        error_log_path (str): Path to the error log file
    """
    # Log summary to session
    log_to_session(
        session_id=session_id,
        message=f"Scraping completed - Found {len(property_data)} properties",
        level="success",
        metadata={
            "property_count": len(property_data),
            "excel_path": excel_file_path,
            "error_log_path": error_log_path
        }
    )

    # Log each property briefly
    for index, prop in enumerate(property_data[:5], start=1):
        log_to_session(
            session_id=session_id,
            message=f"Property {index}: {prop.get('Matched Name', 'Unknown')} - {prop.get('Address', 'Unknown Address')}",
            level="info"
        )

    if len(property_data) > 5:
        log_to_session(
            session_id=session_id,
            message=f"...and {len(property_data) - 5} more properties",
            level="info"
        )

    # Log errors
    errors = [item for item in property_data if "Error" in item]
    if errors:
        for error in errors[:3]:
            log_to_session(
                session_id=session_id,
                message=f"Error: {error.get('Error', 'Unknown error')}",
                level="error"
            )

        if len(errors) > 3:
            log_to_session(
                session_id=session_id,
                message=f"...and {len(errors) - 3} more errors. See log file for details.",
                level="warning"
            )

    # Console summary as well
    print("\n" + "=" * 40 + "\nSummary Report\n" + "=" * 40)
    print(f"Excel file saved to: {Fore.GREEN}{excel_file_path}{Style.RESET_ALL}")
    print(f"Error log saved to: {Fore.YELLOW}{error_log_path}{Style.RESET_ALL}")
    print(f"Property count: {Fore.GREEN}{len(property_data)}{Style.RESET_ALL}")
    print("=" * 40)
