# lsp.py
# Минимальный LSP-клиент, публикующий диагностику
# ---------------------------------------------------------------------

import logging
import os
import urllib.parse

import requests
from lsprotocol import types
from lsprotocol.types import Diagnostic, DiagnosticSeverity, Position, Range
from pygls.server import LanguageServer

SERVER_URL = "http://localhost:8085"
LOG_FILE = "example_lsp.log"

logging.basicConfig(filename=LOG_FILE, level=logging.DEBUG, format="%(asctime)s %(levelname)s %(message)s")

ls_server = LanguageServer("deep-static-analysis-client", "1.0")


def _convert(diags):
    """RAW-dict → LSP Diagnostic objects."""
    res = []
    for d in diags:
        rng = d["range"]
        res.append(
            Diagnostic(
                range=Range(
                    start=Position(**rng["start"]),
                    end=Position(**rng["end"]),
                ),
                severity=DiagnosticSeverity(d["severity"]),
                code=d.get("code"),
                source=d.get("source"),
                message=d.get("message"),
            )
        )
    return res


@ls_server.feature(types.TEXT_DOCUMENT_DID_SAVE)
def on_save(ls: LanguageServer, params: types.DidSaveTextDocumentParams):
    uri = params.text_document.uri
    path = urllib.parse.unquote(urllib.parse.urlparse(uri).path)
    logging.info("Saved file: %s", path)

    with open(path, "rb") as fh:
        files = {"nb_file": (os.path.basename(path), fh, "application/octet-stream")}
        resp = requests.post(f"{SERVER_URL}/analyze", files=files, timeout=60)

    if resp.ok:
        diags = _convert(resp.json()["diagnostics"])
        ls.publish_diagnostics(uri, diags)
    else:
        logging.error("Analyzer returned %s: %s", resp.status_code, resp.text)


def main():
    ls_server.start_io()


if __name__ == "__main__":
    main()
