from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

import httpx
import os

from settings import settings

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],           # Allowed origins
    allow_credentials=True,          # Allow cookies, auth headers
    allow_methods=["*"],             # Allow all HTTP methods (including OPTIONS)
    allow_headers=["*"],             # Allow all headers
)

@app.post("/getMdFeedback")
async def get_md_feedback(
	file: UploadFile = File(...),
) -> FileResponse:
	"""
	Sends .ipynb for processing and returns .md result
	"""
	try:
		content: bytes = await file.read()

		# files = {"file": (file.filename, content, "application/x-ipynb+json")}

		async with httpx.AsyncClient(
			timeout=httpx.Timeout(
				connect=10.0,
				read=300.0,
				write=300.0,
				pool=None,
			)
		) as client:
			response = await client.post(
				url=f"{settings.feedback_service_url}/api/v1/feedback",
				json={
					"current_code": str(content),
					"cell_code_offset": 0,
					"use_deep_analysis": False,
				}
			)
  
		response.raise_for_status()
  
		return response.json()
	except httpx.TimeoutException as e:
		raise HTTPException(status_code=408, detail="Sorry, but your request timed out. Please try again later.")
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
