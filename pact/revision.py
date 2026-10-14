"""Canonical semantic content identity shared by inspection and transactions."""

import hashlib
import json


def revision(document):
    """Hash JSON contents with sorted keys and every array's order preserved.

    Callers validate the document for their supported profile. This digest is
    content identity, without author authentication or editing authority.
    """
    canonical = json.dumps(document, sort_keys=True, separators=(',', ':'),
                           ensure_ascii=False).encode('utf-8')
    return hashlib.sha256(canonical).hexdigest()
