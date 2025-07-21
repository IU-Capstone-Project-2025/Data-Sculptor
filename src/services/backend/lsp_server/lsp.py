import threading
from time import thread_time, time
from pygls.server import LanguageServer
import os
import logging
import urllib.parse
import requests
from lsprotocol import types
from lsprotocol.types import Diagnostic, Range, Position, DiagnosticSeverity
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

server = LanguageServer("example-server", "v0.1")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        RotatingFileHandler("lsp.log", maxBytes=3 * 1024 * 1024, backupCount=1),
        logging.StreamHandler(),
    ],
)

realtime_diagnostics_cache: dict[str, list[Diagnostic]] = {}
deep_syntatic_diagnostic_cache: dict[str, list[Diagnostic]] = {}

load_dotenv()
URL_STATIC_ANALYZER = os.getenv("URL_STATIC_ANALYZER")
URL_LSP_SERVER = os.getenv("URL_LSP_SERVER")
DEBOUNCE_TIME_MS = 400  # TODO: add to .env


def _convert_to_lsp_diagnostics_deep(raw_diagnostics: list[dict], file_content: str = None) -> list[Diagnostic]:
    lsp_diags: list[Diagnostic] = []
    lines = file_content.split('\n') if file_content else []
    
    for d in raw_diagnostics:
        start_line = int(d.get("line", 0))
        start_char = int(d.get("column") or 0)
        
        if "endLine" in d and "endColumn" in d:
            end_line = int(d["endLine"])
            end_char = int(d["endColumn"])
        elif "range" in d:
            end_line = int(d["range"]["end"]["line"])
            end_char = int(d["range"]["end"]["character"])
        else:
            # Better range calculation for syntactic analysis
            end_line = start_line
            end_char = start_char + 1
            
            # Try to find a better end position by analyzing the line content
            if lines and start_line < len(lines):
                line = lines[start_line]
                message = d.get("message", "").lower()
                
                # Look for identifiers, strings, or other tokens starting at start_char
                if start_char < len(line):
                    # Method 1: Find word boundary (for variable names, function names, etc.)
                    end_pos = start_char
                    while end_pos < len(line) and (line[end_pos].isalnum() or line[end_pos] in '_'):
                        end_pos += 1
                    
                    # Method 2: For string literals, find closing quote
                    if line[start_char] in ['"', "'"]:
                        quote = line[start_char]
                        end_pos = start_char + 1
                        while end_pos < len(line) and line[end_pos] != quote:
                            if line[end_pos] == '\\':  # Skip escaped characters
                                end_pos += 1
                            end_pos += 1
                        if end_pos < len(line):  # Include the closing quote
                            end_pos += 1
                    
                    # Method 3: For specific error types, use contextual hints
                    elif "import" in message or "undefined" in message:
                        # For import or undefined variable errors, mark the whole identifier
                        end_pos = start_char
                        while end_pos < len(line) and (line[end_pos].isalnum() or line[end_pos] in '_.'):
                            end_pos += 1
                    
                    elif "function" in message or "method" in message:
                        # For function/method errors, mark until parenthesis or end of identifier
                        end_pos = start_char
                        while end_pos < len(line) and line[end_pos] not in '(\s':
                            end_pos += 1
                    
                    # Ensure we mark at least one character and don't go beyond line
                    end_char = max(start_char + 1, min(end_pos, len(line)))

        lsp_diags.append(
            Diagnostic(
                range=Range(
                    start=Position(
                        line=max(0, start_line), character=max(0, start_char)
                    ),
                    end=Position(line=max(0, end_line), character=max(0, end_char)),
                ),
                severity=DiagnosticSeverity(d.get("severity", 2)),
                code=d.get("message-id"),
                source=d.get("tool", "deep-syntatic-analysis"),
                message=d.get("message", ""),
            )
        )
    return lsp_diags


@server.feature(types.TEXT_DOCUMENT_DID_SAVE)
def on_save(ls: LanguageServer, params: types.DidSaveTextDocumentParams):
    logging.info("On save triggered")
    uri = params.text_document.uri
    filepath = urllib.parse.unquote(urllib.parse.urlparse(uri).path)
    filename = os.path.basename(filepath)

    logging.info("Static analysis for %s", filepath)
    
    # Read file content for better range calculation
    file_content = ""
    try:
        with open(filepath, "r", encoding="utf-8") as f:
            file_content = f.read()
    except Exception as e:
        logging.warning(f"Could not read file content for range calculation: {e}")
    
    with open(filepath, "rb") as f:
        files = {"code_file": (filename, f, "application/octet-stream")}
        resp = requests.post(f"{URL_STATIC_ANALYZER}/analyze", files=files)

    raw_diags = resp.json().get("diagnostics", [])
    diagnostics = _convert_to_lsp_diagnostics_deep(raw_diags, file_content)
    deep_syntatic_diagnostic_cache[uri] = diagnostics

    combined = diagnostics + realtime_diagnostics_cache.get(uri, [])
    ls.publish_diagnostics(uri, combined)


@server.feature(types.TEXT_DOCUMENT_DID_CLOSE)
def teardown(ls: LanguageServer, params):
    uri = params.text_document.uri
    realtime_diagnostics_cache.pop(uri, None)
    deep_syntatic_diagnostic_cache.pop(uri, None)
    logging.info(f"Cache cleared for {uri}")


timer = None


@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def real_time_analysis_debounce(ls: LanguageServer, params):
    logging.info("On open triggered")
    global timer
    if timer is not None:
        timer.cancel()
    timer = threading.Timer(
        DEBOUNCE_TIME_MS / 1000, real_time_analysis, args=(ls, params)
    )
    timer.start()
    # real_time_analysis(ls,params)



def _convert_to_lsp_diagnostics(raw_diagnostics: list[dict]) -> list[Diagnostic]:
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
        return lsp_diags

def real_time_analysis(ls: LanguageServer, params):
    uri = params.text_document.uri
    filepath = urllib.parse.unquote(urllib.parse.urlparse(uri).path)
    filename = os.path.basename(filepath)

    logging.info("Real-time analysis for %s", filepath)


    with open(filepath, "rb") as f:
        files = {"file": (filename, f, "application/octet-stream")}
        raw_diagnostics = requests.post(f"{URL_LSP_SERVER}/analyze", files=files).json().get("diagnostics", [])
        diagnostics = _convert_to_lsp_diagnostics(raw_diagnostics)
    realtime_diagnostics_cache[uri] = diagnostics

    diagnostics = diagnostics + deep_syntatic_diagnostic_cache.get(uri, [])

    ls.publish_diagnostics(uri, diagnostics)


@server.feature(types.TEXT_DOCUMENT_COMPLETION)
def on_completion(ls: LanguageServer, params: types.CompletionParams):
    return types.CompletionList(is_incomplete=False, items=[])


def main():
    server.start_io()


if __name__ == "__main__":
    main()
