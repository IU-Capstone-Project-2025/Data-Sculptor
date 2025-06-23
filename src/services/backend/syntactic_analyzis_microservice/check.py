import sys, json, requests
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: python check.py <file.py>")
    sys.exit(1)

py = Path(sys.argv[1])
url = "http://localhost:8085/analyze"

with py.open("rb") as f:
    files = {"code_file": (py.name, f, "text/x-python")}
    resp = requests.post(url, files=files, timeout=60)

print("Status:", resp.status_code)
print(json.dumps(resp.json(), indent=2, ensure_ascii=False))
