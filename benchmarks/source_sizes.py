import json
from pathlib import Path
from pact.compact import loads


def main():
    root = Path(__file__).resolve().parents[1]
    rows = []
    for name in ('hello', 'alien-harvest'):
        doc = json.loads((root/f'examples/{name}.pact.json').read_text(encoding='utf-8'))
        source = (root/f'examples/{name}.pact').read_text(encoding='utf-8')
        if loads(source) != doc:
            raise ValueError(f'{name}: source representations differ')
        before = len(json.dumps(doc,ensure_ascii=False,separators=(',',':')).encode('utf-8'))
        after = len(source.encode('utf-8'))
        rows.append({'example':name,'minified_json_bytes':before,'compact_bytes':after,
                     'byte_reduction_percent':round(100*(1-after/before),2)})
    print(json.dumps({'metric':'utf8_bytes_not_tokens','results':rows},indent=2))


if __name__ == '__main__':
    main()
