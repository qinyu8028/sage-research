import logging
import re

from ..base import TestAgent
from .token_counter import TokenCounter
from ..base import Message
from .compact_prompts import SUMMARY_PROMPT, HISTORY_COMPRESS_SYSTEM, HISTORY_COMPRESS_BATCH_USER

logger = logging.getLogger(__name__)

_TOOL_DELIMITER_RE = re.compile(r'===TOOL \d+===')



class HistoryCompactor:
    def __init__(
        self,
        llm_client: TestAgent,
        token_counter: TokenCounter,
    ) -> None:
        self.llm_client = llm_client
        self.token_counter = token_counter

    def summarize_all(self, history: list[Message]):
        original_count = len(history)
        logger.info("[HistoryCompactor:summarize_all] triggered: %d messages", original_count)

        messages_to_summary = "".join([f"[{msg.role}]: {msg.content}\n" for msg in history])[:100000]
        messages = [
            {"role": "system", "content": SUMMARY_PROMPT},
            {"role": "user", "content": "Conversation history:\n\n" + messages_to_summary}
        ]
        response = self.llm_client.invoke(messages=messages, tag="history:summarize_all")

        history[:] = [Message(role="user", content="[Compacted]\n\n" + response.content)]
        logger.info("[HistoryCompactor:summarize_all] done: %d messages -> 1 summary (%d chars)", original_count, len(history[0].content))

    def compress_old_rounds(self, history: list[Message], sub_question: str, keep_recent: int = 1):
        round_starts = [i for i, msg in enumerate(history) if msg.role == "assistant" and msg.tool_calls]
        if len(round_starts) <= keep_recent:
            return
        cutoff = round_starts[-keep_recent]

        tool_call_mapping = {}
        for msg in history:
            if msg.role == "assistant" and msg.tool_calls:
                for tc in msg.tool_calls:
                    tool_call_mapping[tc["id"]] = (
                        tc["function"]["name"],
                        tc["function"]["arguments"],
                    )

        to_compress: list[tuple[int, Message, str, str]] = []
        for i, msg in enumerate(history):
            if msg.role != "tool" or i >= cutoff:
                continue
            if msg.content.startswith("[Compressed]") or len(msg.content) < 500:
                continue
            tool_name, tool_args = tool_call_mapping.get(msg.tool_call_id, ("unknown", "{}"))
            to_compress.append((i, msg, tool_name, tool_args))

        if not to_compress:
            return

        logger.info(
            "[HistoryCompactor:compress_old_rounds] %d rounds, cutoff=%d, batch compressing %d messages",
            len(round_starts), cutoff, len(to_compress),
        )

        tool_blocks = []
        for idx, (_, msg, tool_name, tool_args) in enumerate(to_compress, 1):
            tool_blocks.append(f"===TOOL {idx}===\nTool: {tool_name} | Args: {tool_args}\n{msg.content}")

        response = self.llm_client.invoke(
            messages=[
                {"role": "system", "content": HISTORY_COMPRESS_SYSTEM},
                {"role": "user", "content": HISTORY_COMPRESS_BATCH_USER.format(
                    sub_question=sub_question,
                    tool_blocks="\n\n".join(tool_blocks),
                )},
            ],
            tag="history:compress",
        )

        parts = self._parse_batch_response(response.content, len(to_compress))
        for idx, (_, msg, tool_name, tool_args) in enumerate(to_compress):
            header = f"[Compressed] Tool: {tool_name} | Args: {tool_args}"
            original_len = len(msg.content)
            msg.content = f"{header}\n{parts[idx]}"
            logger.info(
                "[HistoryCompactor:compress_old_rounds] compressed: %s, %d -> %d chars",
                tool_name, original_len, len(msg.content),
            )

        logger.info("[HistoryCompactor:compress_old_rounds] done: %d messages in 1 call", len(to_compress))

    @staticmethod
    def _parse_batch_response(content: str, expected_count: int) -> list[str]:
        segments = _TOOL_DELIMITER_RE.split(content)
        parts = [seg.strip() for seg in segments[1:] if seg.strip()]

        if not parts and expected_count == 1:
            parts = [content.strip()]

        while len(parts) < expected_count:
            parts.append("1. Compression output missing for this tool result.")

        return parts[:expected_count]
