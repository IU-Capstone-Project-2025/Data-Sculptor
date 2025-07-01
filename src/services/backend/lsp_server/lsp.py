import threading
from time import thread_time, time
from pygls.server import LanguageServer
import os
import logging
import urllib.parse
***REMOVED***quests
from lsprotocol import types
from lsprotocol.types import Diagnostic, Range, Position, DiagnosticSeverity
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler
import RT_linter as rt
real_time_analyzer = rt.RealTimeAnalysis()
server = LanguageServer("example-server", "v0.1")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        RotatingFileHandler("/logs/lsp.log", maxBytes=3 * 1024 * 1024, backupCount=1),
        logging.StreamHandler(),
    ],
)

realtime_diagnostics_cache: dict[str, list[Diagnostic]] = {}
deep_syntatic_diagnostic_cache: dict[str, list[Diagnostic]] = {}

load_dotenv()
URL_STATIC_ANALYZER = os.getenv("URL_STATIC_ANALYZER")
URL_LSP_SERVER = os.getenv("URL_LSP_SERVER")
DEBOUNCE_TIME_MS = 400 #TODO: add to .env

def _convert_to_lsp_diagnostics_deep(raw_diagnostics: list[dict]) -> list[Diagnostic]:
    lsp_diags: list[Diagnostic] = []
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
            end_line = start_line
            end_char = start_char + 1

        lsp_diags.append(
            Diagnostic(
                range=Range(
                    start=Position(line=max(0, start_line), character=max(0, start_char)),
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
    uri = params.text_document.uri
    filepath = urllib.parse.unquote(urllib.parse.urlparse(uri).path)
    filename = os.path.basename(filepath)

    logging.info("Static analysis for %s", filepath)
    with open(filepath, "rb") as f:
        files = {"code_file": (filename, f, "application/octet-stream")}
        resp = requests.post(f"{URL_STATIC_ANALYZER}/analyze", files=files)

    raw_diags = resp.json().get("diagnostics", [])
    diagnostics = _convert_to_lsp_diagnostics_deep(raw_diags)
    if diagnostics is not None:
        deep_syntatic_diagnostic_cache[uri] = diagnostics

    combined = diagnostics + realtime_diagnostics_cache.get(uri, [])
    ls.publish_diagnostics(uri, combined)
#

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
    global timer
    if timer is not None:
        timer.cancel()
    timer = threading.Timer(DEBOUNCE_TIME_MS/1000, real_time_analysis, args= (ls, params))
    timer.start()
    # real_time_analysis(ls,params)

def real_time_analysis(ls: LanguageServer, params):
    realtime_diagnostics_cache.clear()
    uri = params.text_document.uri
    filepath = urllib.parse.unquote(urllib.parse.urlparse(uri).path)
    filename = os.path.basename(filepath)

    logging.info("Real-time analysis for %s", filepath)
    
    with open(filepath, "r") as f:
        code = f.read()
        # resp = requests.post(f"{URL_LSP_SERVER}/analyze", files=files)
    # TODO: конвертация в чистый diagnostics в МОДУЛЕ!
    # diagnostics = _convert_to_lsp_diagnostics(resp.json().get("diagnostics", []))
    diagnostics = real_time_analyzer.analyze(code,uri) + deep_syntatic_diagnostic_cache.get(uri,[])
    if diagnostics is not None:
        realtime_diagnostics_cache[uri] = diagnostics

    ls.publish_diagnostics(uri, diagnostics)


@server.feature(types.TEXT_DOCUMENT_COMPLETION)
def on_completion(ls: LanguageServer, params: types.CompletionParams):
    return types.CompletionList(is_incomplete=False, items=[])


def main():
    server.start_io()


if __name__ == "__main__":
    main()



