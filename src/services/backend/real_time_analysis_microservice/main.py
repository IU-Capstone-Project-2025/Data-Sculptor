import os
import sys
import subprocess
import threading
import json
import time
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import JSONResponse
import uvicorn
import urllib.parse

app = FastAPI()

# --- Глобальные переменные ---
pylsp_proc = None
pylsp_lock = threading.Lock()
diagnostics_result = {}
diagnostics_event = threading.Event()
message_id = 1

def start_pylsp():
    global pylsp_proc
    pylsp_proc = subprocess.Popen(
        ["pylsp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE, stderr=subprocess.PIPE
    )
    threading.Thread(target=read_loop, daemon=True).start()
    # Отправляем initialize
    root_uri = f"file://{os.getcwd()}"
    send_request({
        "jsonrpc": "2.0",
        "id": next_msg_id(),
        "method": "initialize",
        "params": {"processId": os.getpid(), "rootUri": root_uri, "capabilities": {}}
    })
    send_request({"jsonrpc": "2.0", "method": "initialized", "params": {}})

def next_msg_id():
    global message_id
    message_id += 1
    return message_id

def send_request(message: dict):
    global pylsp_proc
    body = json.dumps(message)
    header = f"Content-Length: {len(body)}\r\n\r\n"
    pylsp_proc.stdin.write(header.encode('utf-8'))
    pylsp_proc.stdin.write(body.encode('utf-8'))
    pylsp_proc.stdin.flush()

def read_loop():
    global pylsp_proc, diagnostics_result, diagnostics_event
    while True:
        headers = {}
        while True:
            line = pylsp_proc.stdout.readline()
            if not line:
                return
            line = line.decode('utf-8').strip()
            if not line:
                break
            key, val = line.split(":", 1)
            headers[key.strip()] = val.strip()
        length = int(headers.get("Content-Length", 0))
        body = pylsp_proc.stdout.read(length).decode('utf-8')
        try:
            msg = json.loads(body)
        except Exception:
            continue
        # Ловим diagnostics
        if msg.get("method") == "textDocument/publishDiagnostics":
            uri = msg["params"]["uri"]
            diagnostics_result[uri] = msg["params"]["diagnostics"]
            diagnostics_event.set()

@app.on_event("startup")
def on_startup():
    start_pylsp()
@app.post("/analyze")
async def analyze(file: UploadFile):
    if not file:
        return JSONResponse(content={"error": "No file provided"}, status_code=400)
    
    content = await file.read()
    content = content.decode('utf-8')
    
    # Create a file URI with the full path
    # Use a temporary file or a specific directory for analysis
    temp_dir = os.path.join(os.getcwd(), "temp_analysis")
    os.makedirs(temp_dir, exist_ok=True)
    
    temp_filepath = os.path.join(temp_dir, file.filename)
    with open(temp_filepath, 'w', encoding='utf-8') as f:
        f.write(content)
    
    # Create a proper file URI
    file_uri = f"file://{os.path.abspath(temp_filepath)}"
    
    # Синхронизируем доступ к pylsp
    with pylsp_lock:
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
            "params": {"textDocument": {"uri": file_uri}}
        })
        # Ждем diagnostics (максимум 4 секунды)
        diagnostics_event.wait(timeout=4)
        diags = diagnostics_result.get(file_uri, [])
        
        # Clean up the temporary file
        try:
            os.remove(temp_filepath)
        except:
            pass
            
    return {"diagnostics": diags}

if __name__ == "__main__":
    uvicorn.run(app, host="0.0.0.0", port=8095)

