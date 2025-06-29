import os
import sys
import subprocess
import threading
import json
import time
import asyncio
from typing import Set, Optional
from concurrent.futures import ThreadPoolExecutor
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import JSONResponse
import uvicorn
import urllib.parse
from fastapi.middleware.cors import CORSMiddleware

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# --- Глобальные переменные ---
pylsp_proc = None
pylsp_lock = threading.Lock()
diagnostics_result = {}
diagnostics_event = threading.Event()
message_id = 1

# Переменные для управления асинхронными запросами
active_requests: Set[str] = set()
request_lock = asyncio.Lock()
executor = ThreadPoolExecutor(max_workers=3)
RATE_LIMIT_DELAY = 0.1  # Минимальный интервал между запросами
last_request_time = 0

def start_pylsp():
    diagnostics_result.clear()
    active_requests.clear()
    global pylsp_proc
    try:
        pylsp_proc = subprocess.Popen(
            ["pylsp"],
            stdin=subprocess.PIPE,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE
        )
        threading.Thread(target=read_loop, daemon=True).start()

        root_uri = f"file://{os.getcwd()}"
        send_request({
            "jsonrpc": "2.0",
            "id": next_msg_id(),
            "method": "initialize",
            "params": {
                "processId": os.getpid(),
                "rootUri": root_uri,
                "capabilities": {}
            }
        })
        send_request({
            "jsonrpc": "2.0",
            "method": "initialized",
            "params": {}
        })
    except Exception as e:
        print(f"Error starting pylsp: {e}")

def next_msg_id():
    global message_id
    message_id += 1
    return message_id

def send_request(message: dict):
    global pylsp_proc
    if pylsp_proc is None or pylsp_proc.poll() is not None:
        start_pylsp()
        return

    try:
        body = json.dumps(message)
        header = f"Content-Length: {len(body)}\r\n\r\n"
        pylsp_proc.stdin.write(header.encode("utf-8"))
        pylsp_proc.stdin.write(body.encode("utf-8"))
        pylsp_proc.stdin.flush()
    except Exception as e:
        print(f"Error sending request to pylsp: {e}")
        start_pylsp()

def read_loop():
    global pylsp_proc, diagnostics_result, diagnostics_event
    buffer = b""
    while True:
        try:
            if pylsp_proc is None or pylsp_proc.poll() is not None:
                break

            headers = {}
            while True:
                line = pylsp_proc.stdout.readline()
                if not line:
                    return
                line = line.decode("utf-8").strip()
                if not line:
                    break
                if ":" in line:
                    key, val = line.split(":", 1)
                    headers[key.strip()] = val.strip()

            length = int(headers.get("Content-Length", 0))
            if length > 0:
                body = pylsp_proc.stdout.read(length).decode("utf-8")
                try:
                    msg = json.loads(body)
                except Exception:
                    continue

                if msg.get("method") == "textDocument/publishDiagnostics":
                    uri = msg["params"]["uri"]
                    diagnostics_result[uri] = msg["params"].get("diagnostics", [])
                    diagnostics_event.set()
        except Exception as e:
            print(f"Error in read_loop: {e}")
            break

def _perform_analysis_sync(file_uri: str, content: str) -> list:
    global diagnostics_result, diagnostics_event

    with pylsp_lock:
        try:
            diagnostics_event.clear()

            send_request({
                "jsonrpc": "2.0",
                "method": "textDocument/didOpen",
                "params": {
                    "textDocument": {
                        "uri": file_uri,
                        "languageId": "python",
                        "version": 1,
                        "text": content
                    }
                }
            })

            send_request({
                "jsonrpc": "2.0",
                "method": "textDocument/didSave",
                "params": {
                    "textDocument": {"uri": file_uri}
                }
            })

            if diagnostics_event.wait(timeout=3):
                diags = diagnostics_result.get(file_uri, [])
            else:
                diags = []

            lines = content.splitlines()
            processed_diags = []

            for d in diags:
                if "range" in d:
                    start = d["range"]["start"]
                    line_no = start["line"]
                else:
                    line_no = d.get("line", 0)

                row_len = len(lines[line_no]) if 0 <= line_no < len(lines) else 1

                processed_d = {
                    "line": line_no,
                    "column": 0,
                    "endLine": line_no,
                    "endColumn": row_len,
                    "range": {
                        "start": {"line": line_no, "character": 0},
                        "end": {"line": line_no, "character": row_len}
                    },
                    "severity": d.get("severity", 2),
                    "message": d.get("message", ""),
                    "source": d.get("source", "pylsp"),
                    "code": d.get("code")
                }
                processed_diags.append(processed_d)

            return processed_diags

        except Exception as e:
            print(f"Error in analysis: {e}")
            return []

async def rate_limited_request():
    global last_request_time
    current_time = time.time()
    if current_time - last_request_time < RATE_LIMIT_DELAY:
        await asyncio.sleep(RATE_LIMIT_DELAY - (current_time - last_request_time))
    last_request_time = time.time()

async def process_analysis_request(file_uri: str, content: str) -> list:
    await rate_limited_request()

    async with request_lock:
        if file_uri in active_requests:
            while file_uri in active_requests:
                await asyncio.sleep(0.1)
            return diagnostics_result.get(file_uri, [])

        active_requests.add(file_uri)

    try:
        loop = asyncio.get_event_loop()
        result = await loop.run_in_executor(
            executor,
            _perform_analysis_sync,
            file_uri,
            content
        )
        return result
    finally:
        active_requests.discard(file_uri)

@app.on_event("startup")
def on_startup():
    start_pylsp()

@app.on_event("shutdown")
def on_shutdown():
    global pylsp_proc, executor
    if pylsp_proc:
        pylsp_proc.terminate()
        pylsp_proc.wait()
    executor.shutdown(wait=True)

@app.post("/analyze")
async def analyze(file: UploadFile):
    if not file:
        return JSONResponse(content={"error": "No file provided"}, status_code=400)

    try:
        content = await file.read()
        content = content.decode("utf-8")

        temp_dir = os.path.join(os.getcwd(), "temp_analysis")
        os.makedirs(temp_dir, exist_ok=True)
        temp_filepath = os.path.join(temp_dir, file.filename)

        with open(temp_filepath, "w", encoding="utf-8") as f:
            f.write(content)

        file_uri = f"file://{os.path.abspath(temp_filepath)}"
        diags = await process_analysis_request(file_uri, content)
        if not diags:
            start_pylsp()
        return {"diagnostics": diags}

    except Exception as e:
        return JSONResponse(
            content={"error": f"Analysis failed: {str(e)}"},
            status_code=500
        )
    finally:
        try:
            if 'temp_filepath' in locals():
                os.remove(temp_filepath)
        except:
            pass

@app.get("/health")
async def health_check():
    global pylsp_proc
    if pylsp_proc and pylsp_proc.poll() is None:
        return {"status": "healthy", "pylsp": "running"}
    else:
        return {"status": "unhealthy", "pylsp": "not running"}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8095)

