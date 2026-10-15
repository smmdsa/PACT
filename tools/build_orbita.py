"""Build the authored PACT kernel and its dependency-free browser presentation."""
import base64
import json
from pathlib import Path
import shutil

from pact.graph import load_document
from pact.module_build import build_module


def build_orbita(root,output):
    binary,manifest=build_module(load_document(root/'examples/orbita.pact'))
    (output/'orbita.wasm').write_bytes(binary)
    (output/'orbita.manifest.json').write_text(json.dumps(manifest,ensure_ascii=False,indent=2),encoding='utf-8')
    artifact=json.dumps({'wasm':base64.b64encode(binary).decode(),'manifest':manifest},ensure_ascii=False).replace('<','\\u003c')
    template=(root/'web/orbita.html').read_text(encoding='utf-8')
    (output/'orbita.html').write_text(template.replace('__ORBITA_ARTIFACT__',artifact),encoding='utf-8')
    for name in ('orbita.css','orbita.js'):
        shutil.copyfile(root/'web'/name,output/name)
