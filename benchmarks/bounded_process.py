"""Bound captured Docker-CLI output while it is produced, not after allocation."""
import subprocess
import threading


def run_bounded(command,data,timeout=15,limit=1048576):
    process=subprocess.Popen(command,stdin=subprocess.PIPE,stdout=subprocess.PIPE,stderr=subprocess.PIPE)
    buffers={'stdout':bytearray(),'stderr':bytearray()};lock=threading.Lock()
    flags={'output_limited':False,'timed_out':False}
    def kill():
        try:process.kill()
        except OSError:pass
    def read(stream,name):
        while True:
            chunk=stream.read1(4096)
            if not chunk:break
            with lock:
                available=max(0,limit-sum(len(value) for value in buffers.values()))
                buffers[name].extend(chunk[:available])
                exceeded=len(chunk)>available
                if exceeded:flags['output_limited']=True
            if exceeded:kill()
    def write():
        try:process.stdin.write(data);process.stdin.flush()
        except (OSError,ValueError):pass
        finally:
            try:process.stdin.close()
            except (OSError,ValueError):pass
    threads=[threading.Thread(target=read,args=(process.stdout,'stdout'),daemon=True),
             threading.Thread(target=read,args=(process.stderr,'stderr'),daemon=True),
             threading.Thread(target=write,daemon=True)]
    for thread in threads:thread.start()
    try:process.wait(timeout=timeout)
    except subprocess.TimeoutExpired:
        flags['timed_out']=True;kill();process.wait(timeout=5)
    for thread in threads:thread.join(timeout=2)
    if any(thread.is_alive() for thread in threads):
        raise ValueError('Subprocess pipes did not close after termination')
    process.stdout.close();process.stderr.close()
    return {'returncode':process.returncode,'stdout':bytes(buffers['stdout']),
            'stderr':bytes(buffers['stderr']),**flags}
