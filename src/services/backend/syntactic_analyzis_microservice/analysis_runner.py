import subprocess, json
from typing import List, Dict

def run_all_linters(py_path: str) -> List[Dict]:
    diagnostics: List[Dict] = []

    linters = {
        "pylint": [
            "pylint", "--output-format=json", py_path
        ],
        "ml_smell_detector": [
            "ml_smell_detector", "--output=json", py_path
        ],
    }

    for name, cmd in linters.items():
        print(f"--- RUNNING {name}: {' '.join(cmd)} ---")
        proc = subprocess.run(cmd, capture_output=True, text=True)
        out, err = proc.stdout.strip(), proc.stderr.strip()
        print(f"[{name}] exit={proc.returncode}")
        print(f"[{name}] stdout:\n{out or '<empty>'}")
        print(f"[{name}] stderr:\n{err or '<empty>'}")

        try:
            data = json.loads(out) if out else []
        except json.JSONDecodeError as e:
            print(f"[{name}] JSON parse error: {e}")
            data = []

        diagnostics += data

    return diagnostics
