import tiktoken

from ..base import Message

class TokenCounter:
    def __init__(self) -> None:
        try:
            self.encoding = tiktoken.get_encoding("o200k_base")
        except Exception:
            self.encoding = None

    def count(self, input_content: str | list[Message]) -> int:
        if not self.encoding:
            if isinstance(input_content, str):
                return len(input_content) // 2

            elif isinstance(input_content, list):
                return len("".join(msg.content or "" for msg in input_content)) // 2
        
        else:
            if isinstance(input_content, str):
                token_ids = self.encoding.encode(input_content)

            elif isinstance(input_content, list):
                token_ids = self.encoding.encode("".join(msg.content or "" for msg in input_content))

            return len(token_ids)

    def trim(self, text: str, n: int) -> str:
        if not self.encoding:
            return text[:n*2]
        
        else:
            token_ids = self.encoding.encode(text)
            token_ids = token_ids[:n]
            trimmed_text = self.encoding.decode(token_ids)

            return trimmed_text