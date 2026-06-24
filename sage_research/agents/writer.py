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
        temperature: float = 0,
    ):
        super().__init__(name, llm, context_builder, system_prompt)
        self.temperature = temperature

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
            temperature=self.temperature,
            tag="writer",
        )

        report = self._resequence_citations(writer_response.content)

        writer_msg = Message(content=report, role="assistant")
        self._history.append(writer_msg)

        return report

    def _resequence_citations(self, report: str) -> str:
        """LLM 输出后处理：按正文首次出现顺序重编号，确保从 [1] 开始连续递增。"""
        sources_re = re.compile(r'^#{0,3}\s*Sources\s*:?\s*$', re.MULTILINE)
        cite_re = re.compile(r'\[(\d+)\]')

        header = sources_re.search(report)
        if not header:
            return report

        body = report[:header.start()]
        sources_text = report[header.end():]

        old_to_new: dict[int, int] = {}
        for m in cite_re.finditer(body):
            n = int(m.group(1))
            if n not in old_to_new:
                old_to_new[n] = len(old_to_new) + 1

        if not old_to_new:
            return report

        if list(old_to_new.keys()) == list(range(1, len(old_to_new) + 1)):
            return report

        logger.info("[Writer] resequence: %s → [1..%d]", list(old_to_new.keys()), len(old_to_new))

        new_body = cite_re.sub(
            lambda m: f'[{old_to_new[int(m.group(1))]}]'
            if int(m.group(1)) in old_to_new else m.group(0),
            body,
        )

        new_sources: dict[int, str] = {}
        for line in sources_text.strip().split('\n'):
            line = line.strip()
            if not line:
                continue
            sm = cite_re.match(line)
            if sm:
                old_num = int(sm.group(1))
                if old_num in old_to_new:
                    new_num = old_to_new[old_num]
                    new_sources[new_num] = f'[{new_num}]' + line[sm.end():]

        new_body = self._sort_adjacent_citations(new_body)

        sorted_lines = [new_sources[k] for k in sorted(new_sources)]
        return new_body.rstrip() + '\n\n' + header.group() + '\n' + '\n'.join(sorted_lines) + '\n'

    @staticmethod
    def _sort_adjacent_citations(text: str) -> str:
        """连续引用按数字升序排列：[4][2] → [2][4]"""
        group_re = re.compile(r'(\[\d+\])(?:\[\d+\])+')

        def _sort_group(m: re.Match) -> str:
            nums = sorted(int(n) for n in re.findall(r'\[(\d+)\]', m.group()))
            return ''.join(f'[{n}]' for n in nums)

        return group_re.sub(_sort_group, text)

    @staticmethod
    def _normalize_url(url: str) -> str:
        m = _ARXIV_ID_RE.search(url)
        if m:
            return f"https://arxiv.org/abs/{m.group(1)}"
        return url

    def _renumber_citations(self, notes: list[str]) -> list[str]:
        """URL 去重 + 全局统一编号。有 URL 的按 URL 去重，无 URL 的按文本去重。"""
        sources_header_re = re.compile(r'^#{0,3}\s*Sources\s*:?\s*$', re.MULTILINE)
        citation_re = re.compile(r'\[(\d+)\]')
        url_re = re.compile(r'(https?://\S+)')

        key_to_num: dict[str, int] = {}
        global_sources: dict[int, str] = {}
        note_maps: list[dict[int, int]] = []

        for note in notes:
            header_match = sources_header_re.search(note)
            local_map: dict[int, int] = {}

            if header_match:
                for line in note[header_match.end():].split('\n'):
                    line = line.strip()
                    num_match = citation_re.match(line)
                    if not num_match:
                        continue

                    old_num = int(num_match.group(1))
                    content = line.split(']', 1)[1].strip()
                    url_match = url_re.search(line)

                    if url_match:
                        dedup_key = self._normalize_url(url_match.group(1).rstrip('.,;)'))
                    else:
                        dedup_key = content.lower().strip()

                    if dedup_key not in key_to_num:
                        gnum = len(key_to_num) + 1
                        key_to_num[dedup_key] = gnum
                        global_sources[gnum] = content

                    local_map[old_num] = key_to_num[dedup_key]

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
            "[Writer] citations: %d notes, %d unique sources (from %d total references)",
            len(notes), len(key_to_num),
            sum(len(m) for m in note_maps),
        )

        return result