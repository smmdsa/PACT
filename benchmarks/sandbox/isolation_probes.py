"""Authored finite attack probes. Execute only in the configured Docker worker."""
import errno
import json
import os
from pathlib import Path
import resource
import signal
import socket
import subprocess
import sys
import time


def filesystem(request):
    errors={}
    for name,path in [('root','/opt/pact-write-denied'),('host',request['host_sentinel'])]:
        try:
            if name=='host':Path(path).read_bytes()
            else:Path(path).write_bytes(b'probe')
        except OSError as error:errors[name]=error.errno
    script=Path('/tmp/execution-probe');script.write_text('#!/bin/sh\nexit 0\n');script.chmod(0o700)
    try:subprocess.run([str(script)],check=True)
    except OSError as error:errors['noexec']=error.errno
    interpreted=subprocess.run(['/bin/sh',str(script)],check=False).returncode==0
    return {'denied':errors.get('root') in (errno.EROFS,errno.EACCES) and errors.get('host')==errno.ENOENT
                    and errors.get('noexec')==errno.EACCES,'errno':errors,'interpreted_control':interpreted}


def network(_):
    with socket.socket() as server,socket.socket() as client:
        server.bind(('127.0.0.1',0));server.listen(1);client.settimeout(2);client.connect(server.getsockname())
        accepted,_=server.accept()
        with accepted:
            client.sendall(b'control');loopback=accepted.recv(7,socket.MSG_WAITALL)==b'control'
    with socket.socket() as external:
        external.settimeout(2);error=external.connect_ex(('192.0.2.1',80))
    return {'denied':error in (errno.ENETUNREACH,errno.EHOSTUNREACH),'errno':error,
            'loopback_control':loopback,'interfaces':sorted(os.listdir('/sys/class/net'))}


def file_size(_):
    signal.signal(signal.SIGXFSZ,signal.SIG_IGN)
    count=0;error=None
    with open('/tmp/file-limit','wb',buffering=0) as stream:
        try:
            for _ in range(8):count+=stream.write(b'x'*262144)
        except OSError as failure:error=failure.errno
    size=os.stat('/tmp/file-limit').st_size
    return {'denied':error==errno.EFBIG and size==1048576,'errno':error,'bytes':size,'written':count}


def temporary_space(_):
    count=0;error=None
    try:
        for index in range(40):
            with open('/tmp/fill-'+str(index),'wb',buffering=0) as stream:
                for _ in range(16):count+=stream.write(b'x'*65536)
    except OSError as failure:error=failure.errno
    return {'denied':error==errno.ENOSPC and 0<count<=16777216,'errno':error,'written':count}


def processes(_):
    children=[];error=None
    try:
        for _ in range(64):
            try:pid=os.fork()
            except OSError as failure:error=failure.errno;break
            if pid==0:
                time.sleep(60);os._exit(0)
            children.append(pid)
    finally:
        for pid in children:os.kill(pid,signal.SIGKILL)
        for pid in children:os.waitpid(pid,0)
    return {'denied':error==errno.EAGAIN and 0<len(children)<32,'errno':error,'children':len(children)}


def cpu(_):
    pid=os.fork()
    if pid==0:
        while True:pass
    _,status,usage=os.wait4(pid,0)
    seconds=usage.ru_utime+usage.ru_stime
    stopped=os.WIFSIGNALED(status) and os.WTERMSIG(status)==signal.SIGKILL
    return {'denied':stopped and 9<=seconds<=12,'cpu_seconds':seconds,'wait_status':status,
            'limits':list(resource.getrlimit(resource.RLIMIT_CPU))}


def memory(_):
    chunks=[]
    for _ in range(64):chunks.append(bytearray(8*1024*1024))
    return {'denied':False,'allocated':sum(map(len,chunks))}


def output(_):
    while True:os.write(1,b'x'*4096)


def wall_time(_):time.sleep(60);return {'denied':False}


PROBES={'filesystem':filesystem,'network':network,'file_size':file_size,'temporary_space':temporary_space,
        'processes':processes,'cpu':cpu,'memory':memory,'output':output,'wall_time':wall_time}


def main():
    request=json.loads(sys.stdin.buffer.read(4097));name=request['probe']
    if name not in PROBES:raise ValueError('Unknown authored probe')
    print(json.dumps({'probe':name,'stage':'started'}),flush=True)
    result=PROBES[name](request)
    print(json.dumps({'probe':name,'stage':'finished',**result}),flush=True)


if __name__=='__main__':main()
