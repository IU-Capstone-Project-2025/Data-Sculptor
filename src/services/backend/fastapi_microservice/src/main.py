from fastapi import FastAPI
from fastapi.responses import FileResponse
from pydantic import BaseModel


class Code(BaseModel):
	code: str

app = FastAPI()

@app.get("/")
async def root():
	return {"Hello": "World!"}


@app.post("/mdAnswer")
async def mdAnswer(code: Code):
	file_path = "generated_file.md"
	content = f"""Hello World! Your code: {code.code}
	"""

	with open(file_path, "w") as f:
		f.write(content)

	# return FileResponse(
	# 	path=file_path,
	# 	media_type="text/markdown",
	# 	filename="generated_file.md"
	# )
	return {"content": content}
