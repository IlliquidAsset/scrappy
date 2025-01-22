
from fastapi import FastAPI, HTTPException, Body
from pydantic import BaseModel
import os
import asyncio
from locales import SUPPORTED_LOCALES
from typing import List
import uvicorn
from main import main as scrappy_main

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

class ScrapeRequest(BaseModel):
    session_id: str
    owners: str
    locale: str
    tax_year: str = "2024"

class ConfirmationRequest(BaseModel):
    session_id: str
    confirmation: str

@app.post("/scrape")
async def scrape(request: ScrapeRequest = Body(..., example={
    "session_id": "test1",
    "owners": "101 Hart ln",
    "locale": "davidson-tn",
    "tax_year": "2024"
})):
    try:
        if request.locale not in SUPPORTED_LOCALES:
            raise HTTPException(status_code=400, detail="Unsupported locale")
            
        os.environ["SCRAPPY_SESSION_ID"] = request.session_id
        os.environ["SCRAPPY_EXTERNAL_CONFIRMATION"] = "true"
        os.environ["SCRAPPY_OWNERS"] = request.owners
        os.environ["SCRAPPY_LOCALE"] = request.locale
        os.environ["TAX_YEAR"] = request.tax_year
        
        # Run scrappy_main asynchronously
        await asyncio.get_event_loop().run_in_executor(None, scrappy_main)
        return {"status": "success", "session_id": request.session_id}
    except Exception as e:
        if "EOF" in str(e):
            raise HTTPException(status_code=400, detail="Invalid request body format")
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/confirm")
async def confirm(request: ConfirmationRequest):
    os.environ["SCRAPPY_CONFIRMATION"] = request.confirmation
    return {"status": "success"}

@app.get("/files/{session_id}")
async def get_files(session_id: str):
    pdf_path = f"outputs/{session_id}/pdfs"
    if not os.path.exists(pdf_path):
        raise HTTPException(status_code=404, detail="Session not found")
    files = os.listdir(pdf_path)
    return {"files": files}

@app.get("/locales")
async def get_locales():
    from locales import SUPPORTED_LOCALES
    return {"locales": SUPPORTED_LOCALES}

if __name__ == "__main__":
    port = int(os.getenv('PORT', 8080))
    uvicorn.run(app, host="0.0.0.0", port=port)
