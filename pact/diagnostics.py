class PactError(ValueError):
    """A machine-readable rejection of a PACT artifact."""

    def __init__(self, code, message, node=None, fix=None):
        self.diagnostic = {"status": "rejected", "code": code, "message": message}
        if node is not None:
            self.diagnostic["node"] = node
        if fix is not None:
            self.diagnostic["fix"] = fix
        super().__init__(message)
