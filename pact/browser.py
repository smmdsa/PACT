import base64
import json
import re
from pathlib import Path


def game_html(document,binary,manifest):
    root=Path(__file__).resolve().parents[1]/'web'
    template=(root/'game.html').read_text(encoding='utf-8')
    runtime=(root/'controls.js').read_text(encoding='utf-8')+'\n'+(root/'runtime.js').read_text(encoding='utf-8')
    def encoded(value):return json.dumps(value,ensure_ascii=False,separators=(',',':')).replace('<','\\u003c')
    replacements={'__SOURCE__':encoded(document),'__MANIFEST__':encoded(manifest),'__WASM__':base64.b64encode(binary).decode(),'__RUNTIME__':runtime}
    return re.sub(r'__SOURCE__|__MANIFEST__|__WASM__|__RUNTIME__',lambda match:replacements[match.group()],template).encode('utf-8')
