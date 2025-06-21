import sys, json
***REMOVED***quests
from pathlib import Path

if len(sys.argv) != 2:
    print("Usage: python check.py <notebook.ipynb>")
    sys.exit(1)

nb = Path(sys.argv[1])
url = "http://localhost:8085/analyze"

with nb.open("rb") as f:
    resp = requests.post(url, files={"nb_file": (nb.name, f)}, timeout=60)

if resp.ok:
    print(json.dumps(resp.json(), indent=2))
else:
    print("Error:", resp.status_code, resp.text)
