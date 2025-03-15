#!/usr/bin/env python
"""
Script to run both API and web services for Scrappy
"""
import os
import sys
import subprocess
import signal
import argparse
import threading
import webbrowser
import time
from pathlib import Path

# Import configuration
from config import API_PORT, API_HOST, WEB_PORT, WEB_HOST

# Commands to start services
API_COMMAND = ["uvicorn", "app:app", "--host", API_HOST, "--port", str(API_PORT)]
WEB_COMMAND = ["flask", "--app", "wsgi", "run", "--host", WEB_HOST, "--port", str(WEB_PORT)]

# Add debug flags in development mode
if os.environ.get("ENV", "development") == "development":
    API_COMMAND.extend(["--reload"])
    os.environ["FLASK_DEBUG"] = "1"

processes = []
stop_event = threading.Event()

def start_service(command, name):
    """Start a service process"""
    try:
        print(f"Starting {name} service...")
        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            universal_newlines=True,
            bufsize=1,
        )
        processes.append(process)
        
        # Start a thread to read and print output
        def print_output():
            for line in process.stdout:
                if stop_event.is_set():
                    break
                print(f"[{name}] {line.strip()}")
        
        thread = threading.Thread(target=print_output, daemon=True)
        thread.start()
        
        return process
    except Exception as e:
        print(f"Error starting {name} service: {e}")
        return None

def open_browser(delay=2):
    """Open web browser after a delay"""
    def _open_browser():
        time.sleep(delay)
        url = f"http://localhost:{WEB_PORT}"
        print(f"Opening browser at {url}")
        webbrowser.open(url)
    
    browser_thread = threading.Thread(target=_open_browser, daemon=True)
    browser_thread.start()

def signal_handler(sig, frame):
    """Handle interrupt signal"""
    print("\nShutting down services...")
    stop_event.set()
    
    for process in processes:
        try:
            process.terminate()
            # Wait a bit for graceful shutdown
            process.wait(timeout=5)
        except subprocess.TimeoutExpired:
            process.kill()
        except Exception as e:
            print(f"Error terminating process: {e}")
    
    print("All services stopped.")
    sys.exit(0)

def main():
    """Main entry point"""
    parser = argparse.ArgumentParser(description="Run Scrappy API and Web Application")
    parser.add_argument("--no-browser", action="store_true", help="Don't open browser automatically")
    parser.add_argument("--api-only", action="store_true", help="Run only the API service")
    parser.add_argument("--web-only", action="store_true", help="Run only the web service")
    args = parser.parse_args()
    
    # Register signal handler for graceful shutdown
    signal.signal(signal.SIGINT, signal_handler)
    signal.signal(signal.SIGTERM, signal_handler)
    
    # Start services
    if not args.web_only:
        api_process = start_service(API_COMMAND, "API")
        # Wait a bit for API to start before starting web app
        time.sleep(2)
    
    if not args.api_only:
        web_process = start_service(WEB_COMMAND, "WEB")
        
        # Open browser if requested
        if not args.no_browser:
            open_browser()
    
    # Keep the main thread alive
    try:
        while True:
            # Check if all processes are still alive
            for i, process in enumerate(processes[:]):
                if process.poll() is not None:
                    print(f"Process exited with code {process.returncode}")
                    processes.remove(process)
            
            if not processes:
                print("All processes have exited. Shutting down.")
                break
            
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(signal.SIGINT, None)

if __name__ == "__main__":
    main()
