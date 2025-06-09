from fastapi import FastAPI, UploadFile, File
from fastapi.responses import FileResponse
from pydantic import BaseModel


class Code(BaseModel):
	code: str

app = FastAPI()

@app.get("/")
async def root():
	return {"Hello": "World!"}


@app.post("/mdAnswer")
async def mdAnswer(file: UploadFile = File(...)):
	content = await file.read()
	content_str = content.decode()
	
	file_path = "generated_file.md"
	with open(file_path, "w") as f:
		f.write("Hello World! Here is your code:")
		f.write(content_str)

	return FileResponse(
		path=file_path,
		media_type="text/markdown",
		filename="generated_file.md"
	)
