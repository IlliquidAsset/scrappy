
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import os
import asyncio
from typing import List
import uvicorn
from main import main as scrappy_main

app = FastAPI()

class ScrapeRequest(BaseModel):
    session_id: str
    owners: str
    locale: str
    tax_year: str = "2024"

class ConfirmationRequest(BaseModel):
    session_id: str
    confirmation: str

@app.post("/scrape")
async def scrape(request: ScrapeRequest):
    os.environ["SCRAPPY_SESSION_ID"] = request.session_id
    os.environ["SCRAPPY_EXTERNAL_CONFIRMATION"] = "true"
    os.environ["SCRAPPY_OWNERS"] = request.owners
    
    try:
        # Run scrappy_main asynchronously
        await asyncio.to_event_loop().run_in_executor(None, scrappy_main)
        return {"status": "success", "session_id": request.session_id}
    except Exception as e:
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

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8080)
