"""Publish a new candidate atomically without clobbering an existing path."""
import os
from pathlib import Path
import tempfile

from .diagnostics import PactError
from .schema import MAX_SOURCE_BYTES, require


def publish_new(path, data):
    path = Path(path)
    require(len(data) <= MAX_SOURCE_BYTES, 'SOURCE_LIMIT', 'Candidate source exceeds 1 MiB.')
    path.parent.mkdir(parents=True, exist_ok=True)
    descriptor, temporary = tempfile.mkstemp(prefix='.pact-', dir=path.parent)
    try:
        with os.fdopen(descriptor, 'wb') as stream:
            stream.write(data)
            stream.flush()
            os.fsync(stream.fileno())
        try:
            os.link(temporary, path)
        except FileExistsError:
            raise PactError('OUTPUT_EXISTS', 'Candidate output already exists; no file was overwritten.') from None
    finally:
        os.unlink(temporary)
