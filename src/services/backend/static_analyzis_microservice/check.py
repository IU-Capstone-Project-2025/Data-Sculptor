import requests

url = "http://127.0.0.1:8000/analyze"
with open("test.ipynb", "rb") as f:
    files = {"nb_file": ("test.ipynb", f, "application/octet-stream")}
    resp = requests.post(url, files=files)

print("Status:", resp.status_code)
print("Response body:")
print(resp.text)   # <— this will show you exactly what the server sent
try:
    print("Parsed JSON:", resp.json())
except ValueError:
    print("No valid JSON could be decoded.")
