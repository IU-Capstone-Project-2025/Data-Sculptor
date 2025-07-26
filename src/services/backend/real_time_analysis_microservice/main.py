"""
Module for real-time Python code analysis using Language Server Protocol (LSP).
Provides diagnostics and analysis for Python code via FastAPI.
"""

import logging
import os
import subprocess
import json
import tempfile
from logging.handlers import RotatingFileHandler
from fastapi import FastAPI, File, UploadFile
from fastapi.middleware.cors import CORSMiddleware

# Logging configuration
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
    to feed code to it and receive LSP feedback.

    WARNING: The mechanism with pylsp processes pool is temporary,
    since it has problems with performance in high load cases (RT may freeze).

    Attributes:
        current_lsp_id (int): Current index for round-robin LSP process selection.
        NUMBER_OF_PYLSP_PROCESSES (int): Number of pylsp processes to maintain in the pool.
        message_id (int): Incrementing ID for LSP messages.
        pylsp_pool (list): List of active pylsp subprocess.Popen objects.
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
            subprocess.Popen: The next pylsp process to use for analysis.
        """
        temp = self.current_lsp_id
        self.current_lsp_id = (self.current_lsp_id + 1) % self.NUMBER_OF_PYLSP_PROCESSES
        return self.pylsp_pool[temp]

    def _next_message_id(self):
        """
        Generate the next unique message ID for LSP communication.

        Returns:
            int: Unique message ID.
        """
        temp = self.message_id
        self.message_id += 1
        return temp

    def _send_message(self, message: dict, process: subprocess.Popen):
        """
        Send a JSON-RPC message to a pylsp process using LSP protocol format.

        Args:
            message (dict): The JSON-RPC message to send.
            process (subprocess.Popen): The target pylsp process.
        """
        body = json.dumps(message)
        body_encoded = body.encode("utf-8")
        head = f"Content-Length: {len(body_encoded)}\r\n\r\n".encode("utf-8")
        logging.info("Sending message to process ID %d", process.pid)
        try:
            process.stdin.write(head)
            process.stdin.write(body_encoded)
            process.stdin.flush()
        except BrokenPipeError as e:
            logging.error("Failed to send message due to broken pipe: %s", e)
            self.start_pylsp()
        except OSError as e:
            logging.error("Failed to send message due to OS error: %s", e)
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
        for _ in range(self.NUMBER_OF_PYLSP_PROCESSES):
            with subprocess.Popen(
                ["pylsp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
            ) as proc:
                logging.info("Created process with ID %d", proc.pid)
                self.pylsp_pool.append(proc)

    def start_pylsp(self):
        """
        Initialize the pylsp process pool by clearing existing state,
        creating new processes, and sending initialization requests.
        """
        self._clear_variables()
        self._create_pylsp_processes()
        self._send_init_requests()

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
            code (str): Python code to analyze.
            uri (str): File URI for the code (used by LSP for context).

        Returns:
            list: List of diagnostic messages from pylsp.
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
        process = self._next_pylsp_process()
        logging.info("Sending request: didOpen")
        self._send_message(did_open_request, process)
        return self._read_pylsp_response(process)

    def _read_pylsp_response(self, process: subprocess.Popen):
        """
        Read and parse responses from pylsp process until diagnostics are received.

        Args:
            process (subprocess.Popen): The pylsp process to read from.

        Returns:
            list: List of diagnostic objects from the LSP response.
        """
        while True:
            content_length = self._read_content_length(process)
            if content_length == 0:
                continue  # Skip empty lines
            body = process.stdout.read(content_length).decode("utf-8")
            logging.info("Read body:\n%s", body)
            try:
                msg = json.loads(body)
            except json.JSONDecodeError as e:
                logging.error("Error during reading LSP response: %s", e)
                continue

            if msg.get("method") == "textDocument/publishDiagnostics":
                return msg["params"].get("diagnostics", [])

    def _read_content_length(self, process: subprocess.Popen):
        """
        Read the Content-Length header from pylsp output and return the message length.

        Args:
            process (subprocess.Popen): The pylsp process to read from.

        Returns:
            int: Length of the next message body in bytes.

        Raises:
            RuntimeError: If the pylsp process closes stdout unexpectedly.
        """
        while True:
            line = process.stdout.readline()
            if not line:
                raise RuntimeError("pylsp process closed stdout")
            line = line.decode("utf-8").strip()
            if line.lower().startswith("content-length:"):
                try:
                    return int(line.split(":", 1)[1].strip())
                except ValueError as e:
                    logging.error("Error parsing content length: %s", e)

    def analyze(self, code_to_analyze: str, uri: str):
        """
        Analyze Python code and return diagnostics (errors, warnings, etc.).

        Args:
            code_to_analyze (str): The Python code to analyze.
            uri (str): File URI for the code being analyzed.

        Returns:
            list: List of diagnostic objects containing analysis results.

        Raises:
            RuntimeError: If there's an error during code analysis.
        """
        if not code_to_analyze:
            return []
        try:
            return self._send_analyse_request(code_to_analyze, uri)
        except Exception as e:
            logging.error("Error during sending code for analyzing: %s", e)
            raise RuntimeError("Error during sending code for analyzing") from e


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
        file (UploadFile): The Python file to analyze.

    Returns:
        dict: JSON response containing diagnostics from code analysis.
    """
    content = file.file.read().decode("utf-8")
    temp_filepath = None
    try:
        with tempfile.NamedTemporaryFile\
            (delete=False, mode="w", encoding="utf-8", suffix=".py") as temp:
            temp.write(content)
            temp_filepath = temp.name
        uri = f"file://{temp_filepath}"
        diagnostics = rt.analyze(content, uri)
    finally:
        if temp_filepath and os.path.exists(temp_filepath):
            os.remove(temp_filepath)
    return {"diagnostics": diagnostics}
