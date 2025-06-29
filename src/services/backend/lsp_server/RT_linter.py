from logging.handlers import RotatingFileHandler
import os
***REMOVED***
import sys
import subprocess
import threading
import json
import time
from lsprotocol.types import Diagnostic, Range, Position, DiagnosticSeverity
import asyncio
from turtle import st
from typing import Set, Optional
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor
from xmlrpc.client import TRANSPORT_ERROR
from fastapi import FastAPI, Request, UploadFile
from fastapi.responses import JSONResponse
from psutil import Process
import pylsp
import uvicorn
import urllib.parse
from fastapi.middleware.cors import CORSMiddleware
import asyncio
import socket
import logging

from pathlib import Path

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
      handlers=[
        RotatingFileHandler("RT.log", maxBytes=10 * 1024 * 1024, backupCount=1),
        logging.StreamHandler(),
    ],
)


class RealTimeAnalysis:

    current_lsp_id = 0

    NUMBER_OF_PYLSP_PROCESSES = 1

    message_id = 0
    pylsp_pool = []

    def __init__(self):
        self.start_pylsp()

    def _next_pylsp_process(self):
        temp = self.current_lsp_id
        self.current_lsp_id = (self.current_lsp_id + 1) % self.NUMBER_OF_PYLSP_PROCESSES
***REMOVED*** self.pylsp_pool[temp]

    def _next_message_id(self):
        temp = self.message_id
        self.message_id += 1
***REMOVED*** temp

    def _send_message(self, message: dict, process: subprocess.Popen):
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
            logging.error(f"Failed to send  message {e}")
            # TODO: start lsp?
            self.start_pylsp()

    def _send_init_requests(self):
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
        for i in range(0, self.NUMBER_OF_PYLSP_PROCESSES):
            proc = subprocess.Popen(
                ["pylsp"], stdin=subprocess.PIPE, stdout=subprocess.PIPE
            )
            logging.info(f"Created process {proc.pid}")
            self.pylsp_pool.append(proc)

    def start_pylsp(self):
        self._clear_variables()
        self._create_pylsp_processes()
        self._send_init_requests()
        # TODO: read_loop

    def _clear_variables(self):
        self.pylsp_pool.clear()
        self.message_id = 0
        self.current_lsp_id = 0

    # def on_shutdown():
    #     # TODO: kill all pyl processes
    #     global pylsp_proc, executor
    #     if pylsp_proc:
    #         pylsp_proc.terminate()
    #         pylsp_proc.wait()
    #     executor.shutdown(wait=True)

    def _send_analyse_request(self, code: str, uri: str):
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
        
        #WARNING: onSave and DidOpen return same diagnostics
        # but alone works only didOpen
        logging.info(f"Sending request on open")
        self._send_message(did_open_request, process)
        did_open_response = self._read_pylsp_response(process)

        logging.info(f"Sending request on save")
        self._send_message(did_save_request, process)
        did_save_response = self._read_pylsp_response(process)
        
        # unique_raw_diagnostics = {json.dumps(d, sort_keys=True): d for d in did_open_response}
***REMOVED*** did_open_response

    def _read_pylsp_response(self, process: subprocess.Popen):
        """
        Читает сообщения из stdout pylsp, пока не получит diagnostics.
        """
        while True:
            content_length = self._read_content_length(process)
            if content_length == 0:
                continue  # Пропускаем пустые строки
            body = process.stdout.read(content_length).decode("utf-8")
            print(f"Read body:\n{body}")
            try:
                msg = json.loads(body)
            except Exception as e:
                logging.info(f"Error during reading lsp response: \n {e}")
                continue

            # Если это уведомление о диагностике — возвращаем
            if msg.get("method") == "textDocument/publishDiagnostics":
                diagnostics = msg["params"].get("diagnostics", [])
        ***REMOVED*** diagnostics
            # Если это просто ответ на запрос — пропускаем
            # Можно добавить обработку других сообщений, если нужно

    def _read_content_length(self, process: subprocess.Popen):
        """
        Читает заголовок Content-Length и возвращает длину следующего сообщения.
        """
        while True:
            line = process.stdout.readline()
            print(f"Read line: {line}")
            if not line:
                raise RuntimeError("pylsp process closed stdout")
            line = line.decode("utf-8").strip()
            if not line:
                # Пустая строка — конец заголовков
                continue
            if line.lower().startswith("content-length:"):
                try:
                    content_length = int(line.split(":", 1)[1].strip())
                    # Пропускаем все заголовки, ищем пустую строку-разделитель
                    while True:
                        next_line = process.stdout.readline()
                        if not next_line or next_line == b"\r\n" or next_line == b"\n":
                            break
            ***REMOVED*** content_length
                except Exception as e:
                    logging.info(f"Error parsing content length: {e}")
                    continue

    def _read_body(self, content_length: int, process: subprocess.Popen):
        if content_length > 0:
            body = process.stdout.read(content_length).decode("utf-8")
            print(f"Read \n{body}")

            try:
                msg = json.loads(body)
            except Exception as e:
                logging.info(f"Error during reading lsp response: \n {e}")
        ***REMOVED*** []
        try:
            diagnostics = msg["params"].get("diagnostics", [])
    ***REMOVED*** diagnostics
        except Exception as e:
            logging.info(f"Error during fetching diagnostics from lsp:\n{e}")
    ***REMOVED*** []
***REMOVED*** []

    def analyze(self, code_to_analyze: str, uri: str):
        if not code_to_analyze:
    ***REMOVED*** []
        try:
            raw_diagnostics = self._send_analyse_request(code_to_analyze, uri)
    ***REMOVED*** self._convert_to_lsp_diagnostics(raw_diagnostics)

        except Exception as e:
            logging.info(f"Error during sending code for analyzing:\n{e}")
    ***REMOVED*** []

    def _convert_to_lsp_diagnostics(self,raw_diagnostics: list[dict]) -> list[Diagnostic]:
        lsp_diags: list[Diagnostic] = []
        for d in raw_diagnostics:
            start = d["range"]["start"]
            end = d["range"]["end"]
            lsp_diags.append(
                Diagnostic(
                    range=Range(
                        start=Position(
                            line=max(0, start["line"]),
                            character=max(0, start["character"]),
                        ),
                        end=Position(
                            line=max(0, end["line"]), character=max(0, end["character"])
                        ),
                    ),
                    severity=DiagnosticSeverity(d["severity"]),
                    code=d.get("code"),
                    source=d.get("source"),
                    message=d.get("message", ""),
                )
            )
***REMOVED*** lsp_diags

    def health_check():
        global pylsp_proc
        if pylsp_proc and pylsp_proc.poll() is None:
    ***REMOVED*** {"status": "healthy", "pylsp": "running"}
        else:
    ***REMOVED*** {"status": "unhealthy", "pylsp": "not running"}


if __name__ == "__main__":
    with open ("/home/aziz/Projects/Data-Sculptor/src/services/backend/lsp_server/test.txt",'r', encoding='utf-8')as f:
        
        code = f.read()

        rt = RealTimeAnalysis()
        fp = Path("/home/aziz/Projects/Data-Sculptor/src/services/backend/lsp_server/test.txt").resolve()
        print(rt.analyze(code, fp.as_uri()))

