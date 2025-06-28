from pygls.server import LanguageServer
import os
import logging
import urllib.parse
***REMOVED***quests
from lsprotocol import types
from lsprotocol.types import Diagnostic, Range, Position, DiagnosticSeverity
from dotenv import load_dotenv
from logging.handlers import RotatingFileHandler

server = LanguageServer("example-server", "v0.1")

logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        RotatingFileHandler("lsp.log", maxBytes=10 * 1024 * 1024, backupCount=1),
        logging.StreamHandler(),
    ],
)

realtime_diagnostics_cache: dict[str, list[Diagnostic]] = {}
deep_syntatic_diagnostic_cache: dict[str, list[Diagnostic]] = {}

load_dotenv()
URL_STATIC_ANALYZER = os.getenv("URL_STATIC_ANALYZER")
URL_LSP_SERVER = os.getenv("URL_LSP_SERVER")


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


def _convert_to_lsp_diagnostics(raw_diagnostics: list[dict]) -> list[Diagnostic]:
    lsp_diags: list[Diagnostic] = []
    for d in raw_diagnostics:
        start = d["range"]["start"]
        end = d["range"]["end"]
        lsp_diags.append(
            Diagnostic(
                range=Range(
                    start=Position(line=max(0, start["line"]), character=max(0, start["character"])),
                    end=Position(line=max(0, end["line"]),   character=max(0, end["character"])),
                ),
                severity=DiagnosticSeverity(d["severity"]),
                code=d.get("code"),
                source=d.get("source"),
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
    deep_syntatic_diagnostic_cache[uri] = diagnostics

    combined = diagnostics + realtime_diagnostics_cache.get(uri, [])
    ls.publish_diagnostics(uri, combined)




@server.feature(types.TEXT_DOCUMENT_DID_CLOSE)
def teardown():
    realtime_diagnostics_cache.clear()
    deep_syntatic_diagnostic_cache.clear()

        
@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def real_time_analysis(ls: LanguageServer, params):
    realtime_diagnostics_cache.clear()
    uri = params.text_document.uri
    filepath = urllib.parse.unquote(urllib.parse.urlparse(uri).path)
    filename = os.path.basename(filepath)

    logging.info("Real-time analysis for %s", filepath)
    with open(filepath, "rb") as f:
        files = {"file": (filename, f, "application/octet-stream")}
        resp = requests.post(f"{URL_LSP_SERVER}/analyze", files=files)

    diagnostics = _convert_to_lsp_diagnostics(resp.json().get("diagnostics", []))
    realtime_diagnostics_cache[uri] = diagnostics

    ls.publish_diagnostics(uri, diagnostics)


@server.feature(types.TEXT_DOCUMENT_COMPLETION)
def on_completion(ls: LanguageServer, params: types.CompletionParams):
    return types.CompletionList(is_incomplete=False, items=[])


def main():
    server.start_io()


if __name__ == "__main__":
    main()
