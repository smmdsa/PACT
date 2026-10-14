class PactError(ValueError):
    """A machine-readable rejection of a PACT artifact."""

    def __init__(self, code, message, node=None):
        self.diagnostic = {"status": "rejected", "code": code, "message": message}
        if node is not None:
            self.diagnostic["node"] = node
        super().__init__(message)
