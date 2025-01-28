from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import os
import asyncio
import sys
import io
import json
from locales import SUPPORTED_LOCALES
from scrapers.property_scraper import scrape_property_data
from main import get_session_folders, main as scrappy_main

VERSION = "v0.09"
from typing import List
import uvicorn

app = FastAPI(
    title="Scrappy API",
    description="API for property tax data scraping"
)

@app.get("/")
async def root():
    return {
        "endpoints": {
            "POST /scrape": "Start scraping with provided parameters",
            "POST /confirm": "Confirm property match",
            "GET /files/{session_id}": "Get list of PDFs for a session",
            "GET /locales": "Get list of supported locales"
        }
    }

@app.get("/locales")
async def get_locales():
    return {
        "locales": {
            locale: data["name"] 
            for locale, data in SUPPORTED_LOCALES.items()
        }
    }

class ScrapeRequest(BaseModel):
    session_id: str
    owners: str
    locale: str
    tax_year: str = "2024"

class ConfirmationRequest(BaseModel):
    session_id: str
    confirmation: str

@app.post("/confirm")
async def confirm(request: ConfirmationRequest):
    os.environ["SCRAPPY_CONFIRMATION"] = request.confirmation
    return {
        "status": "success",
        "data": {
            "session_id": request.session_id,
            "confirmation": request.confirmation
        },
        "message": "Confirmation received"
    }


@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    try:
        print(f"Debug: [{VERSION}] Received scrape request")
        if not request:
            raise HTTPException(status_code=400, detail=f"[{VERSION}] Request body is required")
        
        print(f"Debug: [{VERSION}] Validating request: {request.dict()}")
        if not request.session_id or not request.owners or not request.locale:
            raise HTTPException(
                status_code=400, 
                detail=f"[{VERSION}] All fields (session_id, owners, locale) are required"
            )
        
        if request.locale not in SUPPORTED_LOCALES:
            available_locales = ", ".join(f"{loc} ({data['name']})" for loc, data in SUPPORTED_LOCALES.items())
            raise HTTPException(
                status_code=400, 
                detail=f"[{VERSION}] Unsupported locale. Available locales: {available_locales}"
            )
            
        print(f"Debug: [{VERSION}] Setting up session folders")
        session_folder, pdf_folder = get_session_folders(request.session_id)
        
        print(f"Debug: [{VERSION}] Setting environment variables")
        os.environ["SCRAPPY_SESSION_ID"] = request.session_id
        os.environ["SCRAPPY_EXTERNAL_CONFIRMATION"] = "true"
        os.environ["SCRAPPY_OWNERS"] = request.owners
        os.environ["SCRAPPY_LOCALE"] = request.locale
        os.environ["TAX_YEAR"] = request.tax_year

        print(f"Debug: [{VERSION}] Starting scraping process")
        input_names = [name.strip() for name in request.owners.split(";") if name.strip()]

        # Create a queue for output
        output_queue = asyncio.Queue()
        
        async def capture_output():
            old_stdout = sys.stdout
            output_capture = io.StringIO()
            sys.stdout = output_capture
            try:
                while True:
                    output = output_capture.getvalue()
                    if output:
                        print(f"Debug: [{VERSION}] Raw output: {output}", file=sys.__stdout__)  # Print to real stdout
                        await output_queue.put(output)
                        output_capture.truncate(0)  # Clear the buffer
                        output_capture.seek(0)  # Reset position
                    await asyncio.sleep(0.1)
            finally:
                sys.stdout = old_stdout

        async def monitor_output():
            while True:
                try:
                    output = await asyncio.wait_for(output_queue.get(), timeout=0.5)
                    print(f"Debug: [{VERSION}] Raw output: {output}", file=sys.__stdout__)
                    
                    # Look specifically for confirmation JSON
                    if "confirmation_required" in output:
                        try:
                            # Find the last JSON object in the output (after headers)
                            last_json_start = output.rfind("{")
                            last_json_end = output.rfind("}") + 1
                            if last_json_start != -1 and last_json_end > last_json_start:
                                json_str = output[last_json_start:last_json_end]
                                print(f"Debug: [{VERSION}] Found potential confirmation JSON: {json_str}", file=sys.__stdout__)
                                data = json.loads(json_str)
                                if data.get("status") == "confirmation_required":
                                    print(f"Debug: [{VERSION}] Confirmation request validated", file=sys.__stdout__)
                                    return data
                        except json.JSONDecodeError as je:
                            print(f"Debug: [{VERSION}] JSON parse error: {str(je)}", file=sys.__stdout__)
                            continue
                except asyncio.TimeoutError:
                    continue
        try:
            print(f"Debug: [{VERSION}] Starting tasks")
            loop = asyncio.get_event_loop()
            
            # Start output capture
            capture_task = asyncio.create_task(capture_output())
            monitor_task = asyncio.create_task(monitor_output())
            
            # Start scraping with explicit payload logging
            print(f"Debug: [{VERSION}] About to start scraping with input_names: {input_names}")
            scrape_task = loop.run_in_executor(
                None, 
                lambda: scrape_property_data(input_names, locale=request.locale, tax_year=request.tax_year)
            )

            # Wait for either confirmation or completion
            done, pending = await asyncio.wait(
                [monitor_task, asyncio.wrap_future(scrape_task)],
                timeout=15.0,
                return_when=asyncio.FIRST_COMPLETED
            )

            # Cancel output capture
            capture_task.cancel()
            
            if not done:
                print(f"Debug: [{VERSION}] No task completed within timeout")
                for task in pending:
                    task.cancel()
                raise HTTPException(
                    status_code=408,
                    detail=f"[{VERSION}] Operation timed out after 15 seconds"
                )

            # Check which task completed
            for task in done:
                if task == monitor_task:
                    result = await task
                    if result and result.get("status") == "confirmation_required":
                        return result
                elif task == scrape_task:
                    property_data = await task
                    return {
                        "status": "success",
                        "session_id": request.session_id,
                        "data": property_data if property_data else []
                    }

        except Exception as e:
            print(f"Debug: [{VERSION}] Scraping error: {str(e)}")
            raise HTTPException(status_code=500, detail=f"[{VERSION}] Scraping error: {str(e)}")

    except Exception as e:
        print(f"Debug: [{VERSION}] Request handling error: {str(e)}")
        if isinstance(e, HTTPException):
            raise e
        raise HTTPException(status_code=500, detail=f"[{VERSION}] Server error: {str(e)}")

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)