"""C compilation/execution helpers, called only by the in-container worker."""
import os
from pathlib import Path
import subprocess
import sys


def compile_command():
    return ['gcc','-std=c11','-O2','-Wall','-Wextra','-Werror',
            '/tmp/candidate.c','/tmp/driver.c','-o','/tmp/counter']


def render_driver(template,request):
    cases=request['cases'];reset=request['reset_args']
    if not isinstance(cases,list) or not 1<=len(cases)<=100:raise ValueError('Expected bounded cases')
    for args in [*cases,reset]:
        if (not isinstance(args,list) or len(args)!=2
                or any(type(value) is not int or not -2147483648<=value<=2147483647 for value in args)):
            raise ValueError('Expected pairs of i32 arguments')
    pair=lambda args:'{'+','.join(str(value) for value in args)+'}'
    return template.replace('@CASES@',','.join(map(pair,cases))).replace('@RESET@',pair(reset))


def execute_c(candidate,request,result):
    # Fixed trusted command, before any candidate native code is loaded.
    version=subprocess.check_output(['gcc','-dumpfullversion'],timeout=5).decode('ascii').strip()
    if not 1<=len(version)<=100:raise ValueError('Invalid compiler version')
    result['runtime']={'engine':'gcc','gcc':version}
    Path('/tmp/candidate.c').write_bytes(candidate)
    Path('/tmp/driver.c').write_text(render_driver(Path('/opt/c_driver.c').read_text(),request))
    # Stream compiler diagnostics to the outer bounded Docker capture; no nested log buffer.
    completed=subprocess.run(compile_command(),stdout=sys.stderr,stderr=sys.stderr,timeout=10)
    if completed.returncode:return
    with Path('/tmp/counter').open('rb') as stream:binary=stream.read(1048577)
    if len(binary)>1048576:raise ValueError('Compiled candidate exceeds 1 MiB')
    # /tmp remains noexec. Native execution is intentional and confined to Docker.
    descriptor=os.memfd_create('pact-counter',0)
    with os.fdopen(descriptor,'wb',closefd=False) as stream:stream.write(binary)
    os.fchmod(descriptor,0o700)
    os.execve(descriptor,[f'/proc/self/fd/{descriptor}','batch'],{})
