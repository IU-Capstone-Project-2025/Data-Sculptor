from logging.handlers import RotatingFileHandler

import tempfile
import os
import subprocess
import json
from fastapi.middleware.cors import CORSMiddleware
from fastapi import FastAPI, File, Form, Request, UploadFile
from fastapi.responses import JSONResponse
from lsprotocol.types import Diagnostic, Range, Position, DiagnosticSeverity
import logging
from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        RotatingFileHandler("RT.log", maxBytes=3 * 1024 * 1024, backupCount=1),
        logging.StreamHandler(),
    ],
)


class RealTimeAnalysis:
    """
    A real-time Python code analysis service that uses Python Language Server Protocol (LSP)
    to provide code diagnostics and analysis. This class manages a pool of pylsp processes
    to feed code to it and recieve lsp feedback. 
    WARNING: The mechanism with pylsp processes pool is temporary,
    since it has problems with perfomance in high load cases (RT just start freezing).
    TODO: setup CORS (line 308)
    
    Attributes:
        current_lsp_id (int): Current index for round-robin LSP process selection
        NUMBER_OF_PYLSP_PROCESSES (int): Number of pylsp processes to maintain in the pool
        message_id (int): Incrementing ID for LSP messages
        pylsp_pool (list): List of active pylsp subprocess.Popen objects
    """

    current_lsp_id = 0
    NUMBER_OF_PYLSP_PROCESSES = 3
    message_id = 0
    pylsp_pool = []

    def __init__(self):
        """
        Initialize the RealTimeAnalysis service by starting the pylsp processes pool.
        """
        self.start_pylsp()

    def _next_pylsp_process(self):
        """
        Get the next pylsp process from the pool using round-robin selection.
        
        Returns:
            subprocess.Popen: The next pylsp process to use for analysis
        """
        temp = self.current_lsp_id
        self.current_lsp_id = (self.current_lsp_id + 1) % self.NUMBER_OF_PYLSP_PROCESSES
        return self.pylsp_pool[temp]

    def _next_message_id(self):
        """
        Generate the next unique message ID for LSP communication.
        
        Returns:
            int: Unique message ID
        """
        temp = self.message_id
        self.message_id += 1
        return temp

    def _send_message(self, message: dict, process: subprocess.Popen):
        """
        Send a JSON-RPC message to a pylsp process using LSP protocol format.
        
        Args:
            message (dict): The JSON-RPC message to send
            process (subprocess.Popen): The target pylsp process
        """
        body = json.dumps(message)
        body_encoded = body.encode("utf-8")
        head = f"Content-Length: {len(body_encoded)}\r\n\r\n"
        head_encoded = head.encode("utf-8")
        logging.info(f"Sending message to {process.pid}")
        try:
            process.stdin.write(head_encoded)
            process.stdin.write(body_encoded)
            process.stdin.flush()
        except Exception as e:
            logging.error(f"Failed to send message {e}")
            # TODO: start lsp?
            self.start_pylsp()

    def _send_init_requests(self):
        """
        Send initialization requests to all pylsp processes in the pool.
        This includes both 'initialize' and 'initialized' messages required by LSP.
        """
        first_init_message = {
            "jsonrpc": "2.0",
            "id": self._next_message_id(),
            "method": "initialize",
            "params": {"processId": os.getpid(), "rootUri": None, "capabilities": {}},
        }
        second_init_message = {"jsonrpc": "2.0", "method": "initialized", "params": {}}
        for proc in self.pylsp_pool:
            self._send_message(first_init_message, proc)
            self._send_message(second_init_message, proc)

    def _create_pylsp_processes(self):
        """
        Create the configured number of pylsp subprocess instances and add them to the pool.
        Each process is started with stdin/stdout pipes for LSP communication.
        """
        for i in range(0, self.NUMBER_OF_PYLSP_PROCESSES):
            proc = subprocess.Popen(
                ["pylsp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )
            logging.info(f"Created process {proc.pid}")
            self.pylsp_pool.append(proc)

    def start_pylsp(self):
        """
        Initialize the pylsp process pool by clearing existing state,
        creating new processes, and sending initialization requests.
        """
        self._clear_variables()
        self._create_pylsp_processes()
        self._send_init_requests()
        # TODO: read_loop

    def _clear_variables(self):
        """
        Reset all instance variables to their initial state.
        Used when restarting the pylsp pool.
        """
        self.pylsp_pool.clear()
        self.message_id = 0
        self.current_lsp_id = 0

    def _send_analyse_request(self, code: str, uri: str):
        """
        Send code analysis request to a pylsp process and return diagnostics.
        
        Args:
            code (str): Python code to analyze
            uri (str): File URI for the code (used by LSP for context)
            
        Returns:
            list: List of diagnostic messages from pylsp
        """
        did_open_request = {
            "jsonrpc": "2.0",
            "method": "textDocument/didOpen",
            "params": {
                "textDocument": {
                    "uri": uri,
                    "languageId": "python",
                    "version": 1,
                    "text": code,
                }
            },
        }
        did_save_request = {
            "jsonrpc": "2.0",
            "method": "textDocument/didSave",
            "params": {
                "textDocument": {
                    "uri": uri,
                    "languageId": "python",
                    "version": 1,
                    "text": code,
                }
            },
        }
        process = self._next_pylsp_process()
        
        # WARNING: onSave and DidOpen return same diagnostics
        # but alone works only didOpen
        logging.info(f"Sending request on open")
        self._send_message(did_open_request, process)
        did_open_response = self._read_pylsp_response(process)

        return did_open_response

    def _read_pylsp_response(self, process: subprocess.Popen):
        """
        Read and parse responses from pylsp process until diagnostics are received.
        
        Args:
            process (subprocess.Popen): The pylsp process to read from
            
        Returns:
            list: List of diagnostic objects from the LSP response
        """
        while True:
            content_length = self._read_content_length(process)
            if content_length == 0:
                continue  # Skip empty lines
            body = process.stdout.read(content_length).decode("utf-8")
            logging.info(f"Read body:\n{body}")
            try:
                msg = json.loads(body)
            except Exception as e:
                logging.info(f"Error during reading lsp response: \n {e}")
                continue

            # If this is a diagnostic notification - return it
            if msg.get("method") == "textDocument/publishDiagnostics":
                diagnostics = msg["params"].get("diagnostics", [])
                return diagnostics
            # If this is just a response to a request - skip it
            # Can add handling for other messages if needed

    def _read_content_length(self, process: subprocess.Popen):
        """
        Read the Content-Length header from pylsp output and return the message length.
        
        Args:
            process (subprocess.Popen): The pylsp process to read from
            
        Returns:
            int: Length of the next message body in bytes
            
        Raises:
            RuntimeError: If the pylsp process closes stdout unexpectedly
        """
        while True:
            line = process.stdout.readline()
            logging.info(f"Read line: {line}")
            if not line:
                raise RuntimeError("pylsp process closed stdout")
            line = line.decode("utf-8").strip()
            if not line:
                # Empty line - end of headers
                continue
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                    # Skip all headers, look for empty line separator
                    while True:
                        next_line = process.stdout.readline()
                        if not next_line or next_line == b"\r\n" or next_line == b"\n":
                            break
                    return content_length
                except Exception as e:
                    logging.info(f"Error parsing content length: {e}")
                    continue

    def _read_body(self, content_length: int, process: subprocess.Popen):
        """
        Read and parse the message body from pylsp output.
        
        Args:
            content_length (int): Length of the message body to read
            process (subprocess.Popen): The pylsp process to read from
            
        Returns:
            list: List of diagnostic objects
            
        Raises:
            RuntimeError: If there's an error fetching diagnostics from LSP
        """
        if content_length > 0:
            body = process.stdout.read(content_length).decode("utf-8")
            logging.info(f"Read \n{body}")

            try:
                msg = json.loads(body)
            except Exception as e:
                logging.info(f"Error during reading lsp response: \n {e}")
                return []
        try:
            diagnostics = msg["params"].get("diagnostics", [])
            return diagnostics
        except Exception as e:
            logging.info(f"Error during fetching diagnostics from lsp:\n{e}")
            raise RuntimeError(f"Error during fetching diagnostics from lsp: {e}")

    def analyze(self, code_to_analyze: str, uri: str):
        """
        Analyze Python code and return diagnostics (errors, warnings, etc.).
        
        Args:
            code_to_analyze (str): The Python code to analyze
            uri (str): File URI for the code being analyzed
            
        Returns:
            list: List of diagnostic objects containing analysis results
            
        Raises:
            RuntimeError: If there's an error during code analysis
        """
        if not code_to_analyze:
            return []
        try:
            raw_diagnostics = self._send_analyse_request(code_to_analyze, uri)
            return raw_diagnostics

        except Exception as e:
            logging.info(f"Error during sending code for analyzing:\n{e}")
            raise RuntimeError(f"Error during sending code for analyzing: {e}")


app = FastAPI()
rt = RealTimeAnalysis()
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

@app.post("/analyze")
async def analyze(file: UploadFile = File(...)):
    """
    FastAPI endpoint for analyzing uploaded Python files.
    
    Args:
        file (UploadFile): The Python file to analyze
        
    Returns:
        dict: JSON response containing diagnostics from code analysis
    """
    content = file.file.read().decode('utf-8')
    temp_filepath = None
    try:
        with tempfile.NamedTemporaryFile(delete=False, mode='w', encoding='utf-8', suffix='.py') as temp:
            temp.write(content)
            temp_filepath = temp.name
        uri = f"file://{temp_filepath}"
        raw_diagnostics = rt.analyze(content, uri)
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
    return {
        "diagnostics": raw_diagnostics
    }


