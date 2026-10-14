import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

from .diagnostics import PactError
from .graph import analyze, load_document
from .schema import require
from .wasm import compile_plan


class Parser(argparse.ArgumentParser):
    def error(self, message):
        raise PactError("CLI_INVALID", message)


def atomic_write(path, data):
    path.parent.mkdir(parents=True, exist_ok=True)
    handle, temporary = tempfile.mkstemp(prefix=".pact-", dir=path.parent)
    try:
        with os.fdopen(handle, "wb") as stream:
            stream.write(data)
        os.replace(temporary, path)
    finally:
        if os.path.exists(temporary):
            os.unlink(temporary)


def parser():
    root = Parser(description="PACT toolchain with compact frontend 0.2")
    commands = root.add_subparsers(dest="command", required=True)
    convert = commands.add_parser('convert')
    convert.add_argument('source', type=Path)
    convert.add_argument('-o', '--output', type=Path, required=True)
    convert.add_argument('--to', choices=['compact', 'json'], required=True)
    for command in ("check", "interpret", "build"):
        child = commands.add_parser(command)
        child.add_argument("source", type=Path)
        if command == "interpret":
            child.add_argument("--allow", action="append", choices=["stdout"], default=[])
        if command == "build":
            child.add_argument("-o", "--output", type=Path, required=True)
            child.add_argument("--html", type=Path)
    return root


def main(argv=None):
    try:
        args = parser().parse_args(argv)
        document = load_document(args.source)
        if args.command == 'convert':
            from .compact import dumps, validate_document
            validate_document(document)
            source = dumps(document) if args.to == 'compact' else json.dumps(document, ensure_ascii=False, indent=2) + '\n'
            atomic_write(args.output, source.encode('utf-8'))
            print(json.dumps({'status': 'converted', 'to': args.to, 'output': str(args.output)}))
            return 0
        if isinstance(document, dict) and document.get('format') == 'pact.module/0.1.0':
            from .module import analyze_module
            from .module_build import build_module
            if args.command == 'check':
                plan = analyze_module(document)
                print(json.dumps({'status':'accepted','format':plan['format'],'layout':plan['layout'],'function_types':plan['function_types'],'work':plan['work']},sort_keys=True))
                return 0
            require(args.command == 'build', 'CLI_INVALID', 'Use module build/tests for numeric execution.')
            require(args.output.suffix == '.wasm', 'CLI_INVALID', 'Output must end in .wasm.')
            binary,manifest=build_module(document)
            atomic_write(args.output,binary)
            atomic_write(args.output.with_suffix('.manifest.json'),(json.dumps(manifest,sort_keys=True,ensure_ascii=False,indent=2)+'\n').encode())
            if args.html:
                from .browser import game_html
                atomic_write(args.html,game_html(document,binary,manifest))
            print(json.dumps({'status':'built','bytes':len(binary),'wasm':str(args.output),'html':str(args.html) if args.html else None,'evidence':manifest['evidence']}))
            return 0
        plan = analyze(document)
        if args.command == "check":
            print(json.dumps({"status": "accepted", "plan": plan}, sort_keys=True, ensure_ascii=False, indent=2))
        elif args.command == "interpret":
            require(set(plan["capabilities"]) <= set(args.allow),
                    "CAPABILITY_DENIED", "Host has not granted stdout.")
            sys.stdout.buffer.write("".join(plan["emissions"]).encode("utf-8"))
        else:
            require(args.output.suffix == ".wasm", "CLI_INVALID", "Output path must end in .wasm.")
            binary = compile_plan(plan)
            manifest = {"format": "pact.artifact/0.0.1", "plan": plan,
                        "wasm_sha256": hashlib.sha256(binary).hexdigest()}
            manifest_path = args.output.with_suffix(".manifest.json")
            record = (json.dumps(manifest, sort_keys=True, ensure_ascii=False, indent=2) + "\n").encode("utf-8")
            atomic_write(args.output, binary)
            atomic_write(manifest_path, record)
            print(json.dumps({"status": "built", "wasm": str(args.output), "manifest": str(manifest_path),
                              "bytes": len(binary), "sha256": manifest["wasm_sha256"]}, sort_keys=True))
        return 0
    except PactError as error:
        print(json.dumps(error.diagnostic, ensure_ascii=False), file=sys.stderr)
        return 1
    except OSError as error:
        print(json.dumps({"status": "rejected", "code": "IO_ERROR", "message": str(error)}), file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())
