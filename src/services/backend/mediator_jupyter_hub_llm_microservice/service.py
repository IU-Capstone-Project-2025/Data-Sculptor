from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse

***REMOVED***quests
import os

from dotenv import load_dotenv
load_dotenv()

app = FastAPI()

@app.post("/getMdFeedback")
async def get_md_feedback(
	file: UploadFile = File(...),
) -> FileResponse:
	"""
	Sends .ipynb for processing and returns .md result
	"""
	try:
		content = await file.read()
		content_str = content.decode()

		files = {"file": (file.filename, content_str, "application/x-ipynb+json")}

		FEEDBACK_URL = os.getenv("LLM_BASE_URL")

		response = requests.post(
			url=f"{FEEDBACK_URL}/api/v1/feedback",
			files=files,
			data=data,
		)
	
		file_path = "generated_file.md"
		with open(file_path, "w") as f:
			f.write(response.feedback)

		return FileResponse(
			path=file_path,
			media_type="text/markdown",
			filename="generated_file.md",
		)
	except Exception as e:
		raise HTTPException(
			status_code=500,
			detail=f"Failed to get .md feedback (mediator service error): {e}",
		) from e

