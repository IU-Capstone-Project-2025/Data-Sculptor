# pylsp_vulture.py

from pylsp import hookimpl
from vulture import Vulture

@hookimpl
def pylsp_lint(document):
    vulture = Vulture()
    vulture.scan(document.source, filename=document.path)

    diagnostics = []
    for item in vulture.get_unused_code():
        diagnostics.append({
            'source': 'vulture',
            'range': {
                'start': {'line': item.first_lineno -1 , 'character': 0},
                'end': {'line': item.first_lineno -1  , 'character': 20}
            },
            'message': f"Unused {item.typ}: '{item.name}' (confidence: {item.confidence}%)",
            'severity': 2
        })
    return diagnostics

