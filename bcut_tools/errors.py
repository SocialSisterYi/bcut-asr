class APIError(Exception):
    "接口调用错误"

    def __init__(self, code, msg) -> None:
        self.code = code
        self.msg = msg
        super().__init__()

    def __str__(self) -> str:
        return f"{self.code}:{self.msg}"