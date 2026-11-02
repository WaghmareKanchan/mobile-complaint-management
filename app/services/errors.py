class FlowError(Exception):
    def __init__(self, status_code, code, message, extra=None):
        self.status_code, self.code, self.message, self.extra = status_code, code, message, extra or {}