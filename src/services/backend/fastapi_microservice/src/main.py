from fastapi import FastAPI, UploadFile
from fastapi.responses import HTMLResponse


app = FastAPI()

@app.get("/")
async def root():
	return {"Hello": "World!"}


# Example page for uploading file
# Redirects to '/answer' then
@app.get("/upload_file_page", response_class=HTMLResponse)
async def upload():
	html_content = f"""
<html>
	<head>
		<title>upload_example</title>
	</head>
	<body>
		<form action="/answer" method="post" enctype="multipart/form-data">
			<input type="file" name="file">
			<button type="submit">Upload</button>
		</form>
	</body>
</html>
"""
	return html_content


@app.post("/answer")
async def answer(file: UploadFile):
	# TODO: add file validation - only text file is acceptable and file size should not be large

	content = await file.read()
	text = content.decode("utf-8")

	ans = text[:100] # get llm answer from somewhere

	return {"result": ans, "meta": len(text)}
