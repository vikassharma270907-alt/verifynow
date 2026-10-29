"""Typed errors shared across services and routers."""


class UpstreamError(Exception):
    """An upstream dependency failed. `safe_message` is safe to show to users."""

    def __init__(self, status: int, safe_message: str):
        super().__init__(safe_message)
        self.status = status
        self.safe_message = safe_message
