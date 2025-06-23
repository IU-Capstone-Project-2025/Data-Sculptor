from pygls.server import LanguageServer
import os
from lsprotocol import types
import logging
import urllib.parse
import requests
from lsprotocol.types import Diagnostic, Range, Position, DiagnosticSeverity
from dotenv import load_dotenv
server = LanguageServer("example-server", "v0.1")
from logging.handlers import RotatingFileHandler
target = "lsp.log"
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s",
    handlers=[
        RotatingFileHandler(target, maxBytes=10*1024*1024, backupCount=1),
        logging.StreamHandler()
    ]
)

load_dotenv()
URL_STATIC_ANALYZER = os.getenv("URL_STATIC_ANALYZER")
URL_LSP_SERVER = os.getenv("URL_LSP_SERVER")

@server.feature(types.TEXT_DOCUMENT_DID_SAVE)
def on_save(ls: LanguageServer, params: types.DidSaveTextDocumentParams):
    URI = params.text_document.uri
    filepath_URI = urllib.parse.urlparse(URI).path
    filepath = urllib.parse.unquote(filepath_URI)
    filename = os.path.basename(filepath)

    logging.info(f"HERES YOUR FILEPATH {filepath}")
    with open(f"{filepath}", "rb") as f:
        logging.info("PREPARE FILE TRANSMISION")
        files = {"code_file": (filename, f, "application/octet-stream")}
        logging.info("SEND FILE TO THE SERVER")
        raw_diagnostics = requests.post(f"{URL_STATIC_ANALYZER}/analyze", files=files)
        logging.info("RECIEVED DIAGNOSTICS... SEND BACK TO JUPYTERLAB")

    # logging.info(raw_diagnostics.json().get("diagnostics"))
    logging.info(f"Status:\n {raw_diagnostics.status_code}")
    logging.info(f"Response body:\n{raw_diagnostics.text}")
    raw_diagnostics = raw_diagnostics.json()["diagnostics"]
    diagnostics = _convert_to_lsp_diagnostics_deep(raw_diagnostics)
    logging.info(f"Publishing diagnostics...\n{diagnostics}")
    ls.publish_diagnostics(URI, diagnostics)


def _convert_to_lsp_diagnostics_deep(raw_diagnostics):
    lsp_diags = []
    for d in raw_diagnostics:
        start = d["line"]
        end = d["line"]
        start_char = None
        end_char = None
        if (d["column"] == None or d['column'] == 'null'):
            start_char = 0
        else:
            start_char = d["column"]

        # if (d["endColumn"] == None or d['endColumn'] == 'null'):
        #     end_char = 1
        # else:
        end_char = start_char + 2

        lsp_diags.append(Diagnostic(
            range=Range(
                start=Position(line=max(0, start) - 1,
                              character=start_char),
                end=Position(line=max(0, end) - 1, character=end_char)
            ),
            severity=DiagnosticSeverity(2),
            code=d.get("message-id"),
            source=d.get("tool", "deep-syntatic-analysis"),
            message=d.get("message", "")
        ))
    return lsp_diags


def _convert_to_lsp_diagnostics(raw_diagnostics):
    lsp_diags = []
    for d in raw_diagnostics:
        start = d["range"]["start"]
        end = d["range"]["end"]

        start_char = max(0, start["character"])
        end_char = max(0, end["character"])

        lsp_diags.append(Diagnostic(
            range=Range(
                start=Position(line=max(0, start["line"]),
                               character=start_char),
                end=Position(line=max(0, end["line"]), character=end_char)
            ),
            severity=DiagnosticSeverity(d["severity"]),
            code=d.get("code"),
            source=d.get("source"),
            message=d.get("message", "")
        ))
    return lsp_diags

@server.feature(types.TEXT_DOCUMENT_COMPLETION)
def on_completion(ls: LanguageServer, params: types.CompletionParams):
    # Implement your completion logic here
    items = []
    # Example: items.append(CompletionItem(label="example"))
    return types.CompletionList(is_incomplete=False, items=items)

@server.feature(types.TEXT_DOCUMENT_DID_OPEN)
@server.feature(types.TEXT_DOCUMENT_DID_CHANGE)
def real_time_analysis(ls: LanguageServer, params):
    logging.info("Starting real_time_analysis")
    
    uri = params.text_document.uri
    filepath_URI = urllib.parse.urlparse(uri).path
    filepath = urllib.parse.unquote(filepath_URI)
    filename = os.path.basename(filepath)
    
    logging.info(f"Requesting analysis for {uri}")
    
    # Read the file content
    with open(filepath, 'rb') as f:
        files = {"file": (filename, f, "application/octet-stream")}
        logging.info(f"Sending file to the server:")
        response = requests.post(f"{URL_LSP_SERVER}/analyze", files=files)
    logging.info(f"Received response!")
    diagnostics = _convert_to_lsp_diagnostics(response.json()["diagnostics"])
    logging.info(f"Publishing diagnostics...\n{diagnostics}")
    ls.publish_diagnostics(uri, diagnostics)


def main():
    server.start_io()


if __name__ == "__main__":
    main()
