from pygls.server import LanguageServer
import os
from lsprotocol import types
import logging
import urllib.parse
import requests
from lsprotocol.types import Diagnostic, Range, Position, DiagnosticSeverity

server = LanguageServer("example-server", "v0.1")

target = "example_lsp.log"
logging.basicConfig(
    filename=target, level=logging.DEBUG,
    format="%(asctime)s %(levelname)s %(message)s"
)

URL_STATIC_ANALYZER = "http://0.0.0.0:8085/analyze"


@server.feature(types.TEXT_DOCUMENT_DID_SAVE)
def on_save(ls: LanguageServer, params: types.DidSaveTextDocumentParams):
    URI = params.text_document.uri
    filepath = urllib.parse.urlparse(URI).path
    filename = os.path.basename(filepath)

    logging.info(f"HERES YOUR FILEPATH {filepath}")
    with open(f"{filepath}", "rb") as f:
        logging.info("PREPARE FILE TRANSMISION")
        files = {"nb_file": (filename, f, "application/octet-stream")}
        logging.info("SEND FILE TO THE SERVER")
        raw_diagnostics = requests.post(URL_STATIC_ANALYZER, files=files)
        logging.info("RECIEVED DIAGNOSTICS... SEND BACK TO JUPYTERLAB")

    logging.info(raw_diagnostics.json().get("diagnostics"))
    logging.info(f"Status:\n {raw_diagnostics.status_code}")
    logging.info(f"Response body:\n{raw_diagnostics.text}")
    raw_diagnostics = raw_diagnostics.json()["diagnostics"]
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
    ls.publish_diagnostics(URI, lsp_diags)


@server.feature(types.TEXT_DOCUMENT_COMPLETION)
def completions(ls: LanguageServer, params: types.CompletionParams):
    items = []
    doc = ls.workspace.get_document(params.text_document.uri)
    line = doc.lines[params.position.line].strip()
    if line.endswith("hello."):
        items = [
            types.CompletionItem(label="world"),
            types.CompletionItem(label="friend"),
        ]
    return types.CompletionList(is_incomplete=False, items=items)


def main():
    server.start_io()


if __name__ == "__main__":
    main()
