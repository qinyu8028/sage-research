import logging, re

from ..base import AgentBase, llm_client, Message
from ..context import ContextBuilder
from .prompts import WRITER_SYSTEM_PROMPT, WRITER_USER_PROMPT

logger = logging.getLogger(__name__)


_ARXIV_ID_RE = re.compile(r'arxiv\.org/(?:abs|html|pdf)/(\d{4}\.\d{4,5})')


class Writer(AgentBase):
    """研究流水线的最终阶段，将多条研究笔记合成为一篇结构化的 Markdown 报告。"""

    def __init__(
        self, 
        llm: llm_client, 
        context_builder: ContextBuilder, 
        name: str = "writer",
        system_prompt: str = WRITER_SYSTEM_PROMPT,
    ):
        super().__init__(name, llm, context_builder, system_prompt)

    def run(self, research_brief: str, notes: list[str]) -> str:
        """接收研究简报和已审查通过的研究笔记，单次 LLM 调用生成最终报告。"""

        clean_notes = self._renumber_citations(notes=notes)

        findings = "\n\n".join(
            f"<note>\n{note}\n</note>" for note in clean_notes
        )
        prompt = WRITER_USER_PROMPT.format(
            research_brief=research_brief,
            findings=findings
        )
        user_msg = Message(content=prompt, role="user")
        self._history.append(user_msg)
        messages = self._build_messages(self.system_prompt)

        writer_response = self.llm.invoke(
            messages=messages,
            max_tokens=16384,
            tag="writer",
        )

        writer_msg = Message(content=writer_response.content, role="assistant")
        self._history.append(writer_msg)

        return writer_response.content

    @staticmethod
    def _normalize_url(url: str) -> str:
        m = _ARXIV_ID_RE.search(url)
        if m:
            return f"https://arxiv.org/abs/{m.group(1)}"
        return url

    def _renumber_citations(self, notes: list[str]) -> list[str]:
        """URL 去重 + 全局统一编号。"""
        sources_header_re = re.compile(r'^#{0,3}\s*Sources\s*:?\s*$', re.MULTILINE)
        citation_re = re.compile(r'\[(\d+)\]')
        url_re = re.compile(r'(https?://\S+)')

        url_to_num: dict[str, int] = {}
        global_sources: dict[int, str] = {}
        note_maps: list[dict[int, int]] = []

        for note in notes:
            header_match = sources_header_re.search(note)
            local_map: dict[int, int] = {}

            if header_match:
                for line in note[header_match.end():].split('\n'):
                    line = line.strip()
                    num_match = citation_re.match(line)
                    url_match = url_re.search(line)
                    if num_match and url_match:
                        old_num = int(num_match.group(1))
                        url = url_match.group(1).rstrip('.,;)')
                        norm = self._normalize_url(url)

                        if norm not in url_to_num:
                            gnum = len(url_to_num) + 1
                            url_to_num[norm] = gnum
                            global_sources[gnum] = line.split(']', 1)[1].strip()

                        local_map[old_num] = url_to_num[norm]

            note_maps.append(local_map)

        result = []
        for i, note in enumerate(notes):
            mapping = note_maps[i]

            header_match = sources_header_re.search(note)
            body = note[:header_match.start()].rstrip() if header_match else note

            if mapping:
                body = citation_re.sub(
                    lambda m, mp=mapping: f'[{mp.get(int(m.group(1)), int(m.group(1)))}]',
                    body,
                )

            result.append(body)

        if global_sources:
            lines = [f"[{n}] {global_sources[n]}" for n in sorted(global_sources)]
            result[-1] += "\n\nSources:\n" + "\n".join(lines)

        logger.info(
            "[Writer] citations: %d notes, %d unique URLs (from %d total references)",
            len(notes), len(url_to_num),
            sum(len(m) for m in note_maps),
        )

        return result