from fastapi import FastAPI, UploadFile, File, HTTPException
from fastapi.responses import FileResponse
from pydantic import BaseModel

import httpx
import os

from settings import settings

app = FastAPI()

@app.post("/getMdFeedback")
async def get_md_feedback(
	file: UploadFile = File(...),
) -> FileResponse:
	"""
	Sends .ipynb for processing and returns .md result
	"""
	try:
		content: bytes = await file.read()

		files = {"file": (file.filename, content, "application/x-ipynb+json")}

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
				files=files,
			)
  
		response.raise_for_status()
  
		response_json = response.json()
	
		file_path = "generated_file.md"
		with open(file_path, "w") as f:
			f.write(response_json.get("feedback",""))

		return FileResponse(
			path=file_path,
			media_type="text/markdown",
			filename="generated_file.md",
		)
	except httpx.TimeoutException as e:
		raise HTTPException(status_code=408, detail="Sorry, but your request timed out. Please try again later.")
	except Exception as e:
		raise HTTPException(status_code=500, detail=str(e))
