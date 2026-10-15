import argparse
import hashlib
import json
import os
import sys
import tempfile
from pathlib import Path

from .diagnostics import PactError
from .graph import analyze, load_document
from .schema import MAX_SOURCE_BYTES, require
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
    root = Parser(description="PACT toolchain with compact frontend 0.2/0.3/0.4")
    commands = root.add_subparsers(dest="command", required=True)
    replay = commands.add_parser('replay')
    replay.add_argument('source', type=Path)
    replay.add_argument('--record', type=Path, required=True)
    replay.add_argument('--engine', choices=['reference','wasm','compare'], default='reference')
    patch = commands.add_parser('patch')
    patch.add_argument('source', type=Path)
    patch.add_argument('--patch', type=Path, required=True)
    patch.add_argument('-o', '--output', type=Path)
    patch.add_argument('--to', choices=['compact', 'compact-data', 'compact-inline', 'compact-agent', 'json'], default='compact')
    patch.add_argument('--dry-run', action='store_true')
    patch.add_argument('--expected-source-sha256', help='Require exact source bytes (64 lowercase hex).')
    for name in ('inspect', 'symbols'):
        command = commands.add_parser(name)
        command.add_argument('source', type=Path)
        if name == 'inspect':
            command.add_argument('--function', required=True)
    locate = commands.add_parser('locate')
    locate.add_argument('source', type=Path)
    locate.add_argument('--function')
    locate.add_argument('--node')
    convert = commands.add_parser('convert')
    convert.add_argument('source', type=Path)
    convert.add_argument('-o', '--output', type=Path, required=True)
    convert.add_argument('--to', choices=['compact', 'compact-data', 'compact-inline', 'compact-agent', 'json'], required=True)
    migrate = commands.add_parser('migrate')
    migrate.add_argument('source', type=Path)
    migrate.add_argument('-o', '--output', type=Path, required=True)
    migrate.add_argument('--to', choices=['pact.module/0.2.0', 'pact.module/0.3.0', 'pact.module/0.4.0', 'pact.module/0.5.0', 'pact.module/0.6.0'], default='pact.module/0.2.0')
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
    # Stable UTF-8/LF JSON wire format, independent of Windows text-mode defaults.
    for stream in (sys.stdout, sys.stderr):
        if hasattr(stream, 'reconfigure'):
            stream.reconfigure(encoding='utf-8', newline='\n')
    try:
        args = parser().parse_args(argv)
        if args.command == 'replay':
            from .replay import replay_file
            report = replay_file(args.source, args.record, engine=args.engine)
            print(json.dumps(report,ensure_ascii=False,sort_keys=True))
            return 0 if report['status'] in ('completed','matched') else 2
        if args.command == 'locate':
            from .source_locations import locate_file
            print(json.dumps(locate_file(args.source, args.function, args.node), ensure_ascii=False, sort_keys=True))
            return 0
        document = load_document(args.source, validate_source=args.command != 'migrate',
                                 migrate_to=args.to if args.command == 'migrate' else None)
        if args.command == 'patch':
            from .compact import dumps
            from .module_build import build_module
            from .revision import revision
            from .transaction_io import publish_new
            from .transactions import apply_patch
            require(args.dry_run or args.output is not None, 'PATCH_OUTPUT_REQUIRED', 'Specify a new output path or --dry-run.')
            require(args.to != 'json' or args.output is None or args.output.suffix != '.pact',
                    'PATCH_OUTPUT_FORMAT', 'JSON candidates cannot use the .pact suffix; use .json.')
            if not args.dry_run:
                require(args.output.resolve() != args.source.resolve(), 'PATCH_IN_PLACE', 'In-place publication is unsupported; specify a new candidate path.')
            source_hash = hashlib.sha256(args.source.read_bytes()).hexdigest()
            if args.expected_source_sha256 is not None:
                require(len(args.expected_source_sha256) == 64 and
                        all(char in '0123456789abcdef' for char in args.expected_source_sha256),
                        'PATCH_INVALID', 'Expected a 64-character lowercase source SHA256.')
                require(source_hash == args.expected_source_sha256, 'PATCH_SOURCE_STALE',
                        'Source bytes differ from the expected source SHA256.')
            patch = load_document(args.patch)
            candidate = apply_patch(document, patch)
            _, manifest = build_module(candidate)
            source = (dumps(candidate, compressed=args.to in ('compact-data', 'compact-inline', 'compact-agent'),
                            inline=args.to == 'compact-inline', literals=args.to == 'compact-agent')
                      if args.to != 'json' else json.dumps(candidate, ensure_ascii=False, indent=2) + '\n')
            data = source.encode('utf-8')
            require(len(data) <= MAX_SOURCE_BYTES, 'SOURCE_LIMIT', 'Candidate source exceeds 1 MiB.')
            receipt = {'format': 'pact.patch-receipt/0.1.0',
                       'status': 'validated' if args.dry_run else 'patched',
                       'expected_revision_sha256': patch['expected_revision_sha256'],
                       'source_sha256': source_hash,
                       'expected_source_sha256': args.expected_source_sha256,
                       'result_revision_sha256': revision(candidate),
                       'evidence': manifest['evidence'],
                       'changes': [{key:value for key,value in operation.items() if key not in ('node','test')}
                                   for operation in patch['operations']],
                       'output': None if args.dry_run else str(args.output)}
            if not args.dry_run:
                if args.expected_source_sha256 is not None:
                    require(hashlib.sha256(args.source.read_bytes()).hexdigest() == args.expected_source_sha256,
                            'PATCH_SOURCE_STALE', 'Source bytes changed before candidate publication.')
                publish_new(args.output, data)
            print(json.dumps(receipt, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
            return 0
        if args.command in ('inspect', 'symbols'):
            from .inspection import inspect_function, symbols
            response = inspect_function(document, args.function) if args.command == 'inspect' else symbols(document)
            print(json.dumps(response, ensure_ascii=False, sort_keys=True, separators=(',', ':')))
            return 0
        if args.command == 'convert':
            from .compact import dumps, validate_document
            validate_document(document)
            source = (dumps(document, compressed=args.to in ('compact-data', 'compact-inline', 'compact-agent'),
                            inline=args.to == 'compact-inline', literals=args.to == 'compact-agent')
                      if args.to != 'json' else json.dumps(document, ensure_ascii=False, indent=2) + '\n')
            atomic_write(args.output, source.encode('utf-8'))
            print(json.dumps({'status': 'converted', 'to': args.to, 'output': str(args.output)}))
            return 0
        if args.command == 'migrate':
            from .compact import dumps
            migrated = document
            source = dumps(migrated) if args.output.suffix == '.pact' else json.dumps(migrated, ensure_ascii=False, indent=2) + '\n'
            atomic_write(args.output, source.encode('utf-8'))
            print(json.dumps({'status': 'migrated', 'to': migrated['format'], 'output': str(args.output)}))
            return 0
        from .module import FORMATS
        if isinstance(document, dict) and document.get('format') in FORMATS:
            from .module import analyze_module
            from .module_build import build_module
            if args.command == 'check':
                plan = analyze_module(document)
                response = {'status':'accepted','format':plan['format'],'layout':plan['layout'],'function_types':plan['function_types'],'work':plan['work']}
                if 'declared_export_tests' in plan:
                    response['declared_export_tests'] = plan['declared_export_tests']
                if 'unit_contracts' in plan:
                    response['unit_contracts'] = plan['unit_contracts']
                print(json.dumps(response, sort_keys=True))
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
