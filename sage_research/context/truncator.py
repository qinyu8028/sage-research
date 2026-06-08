from .token_counter import TokenCounter


class Truncator:
    def __init__(self, token_counter: TokenCounter, max_tokens: int = 1500) -> None:
        self.token_counter = token_counter
        self.max_tokens = max_tokens

    TRUNCATION_WARNING = (
        "\n\n[输出已截断: 原始{original} tokens, 保留{kept} tokens. "
        "信息可能不完整, 请基于已有内容判断是否需要进一步操作]"
    )

    def truncate(self, tool_result: str) -> str:
        original_tokens = self.token_counter.count(tool_result)

        if original_tokens <= self.max_tokens:
            return tool_result

        truncation_warning = self.TRUNCATION_WARNING.format(original=original_tokens, kept=self.max_tokens - 30)
        tool_result = self.token_counter.trim(text=tool_result, n=self.max_tokens - 30)

        return tool_result + truncation_warning