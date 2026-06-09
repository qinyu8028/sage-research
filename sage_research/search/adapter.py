"""
搜索mcp fallback 逻辑，统一两种search mcp的格式。
封装为一种工具，对外均展现为 search。
llm 不会看到代码层面的切换。
"""

import json
from typing import Any, Literal

from .result import SearchResult
from ..mcp.tool_adapter import MCPTool


TimeRange = Literal["day", "week", "month", "year"]
RELATIVE_KEYWORDS = {"day", "week", "month", "year"}


def _parse_time_filter(
    time_filter: str,
) -> tuple[TimeRange | None, tuple[str, str] | None]:
    value = time_filter.strip()
    if value in RELATIVE_KEYWORDS:
        return value, None
    if "to" in value:
        parts = value.split("to", 1)
        return None, (parts[0].strip(), parts[1].strip())
    return None, None


class BraveAdapter:
    def __init__(self, tool: MCPTool) -> None:
        self.tool = tool

    def search(
        self,
        query: str,
        count: int = 5,
        time_filter: str | None = None,
    ) -> list[SearchResult]:

        time_mapping = {
            "day": "pd",
            "week": "pw",
            "month": "pm",
            "year": "py",
        }
        parameters = {
            "query": query,
            "count": count,
            "extra_snippets": True,
            "result_filter": ["web"],
            "text_decorations": False,
        }
        if time_filter:
            time_range, date = _parse_time_filter(time_filter)
            if time_range:
                parameters["freshness"] = time_mapping[time_range]
            elif date:
                parameters["freshness"] = f"{date[0]}to{date[1]}"

        result_text = self.tool.run_tool(parameters)

        # process the result text
        texts = result_text.split("\n")
        search_results = []
        for text in texts:
            if not text.strip():
                continue
            data: dict[str, Any] = json.loads(text)
            url = data["url"]
            title = data["title"]
            description = data["description"]
            extra_snippets = data.get("extra_snippets", [])

            parts = [description] + extra_snippets
            content = "\n".join(parts)

            search_result = SearchResult(
                title=title,
                url=url,
                content=content,
                source="Brave",
            )
            search_results.append(search_result)

        return search_results


class TavilyAdapter:
    def __init__(self, tool: MCPTool) -> None:
        self.tool = tool

    def search(
        self,
        query: str,
        count: int = 5,
        time_filter: str | None = None,
    ) -> list[SearchResult]:

        parameters = {
            "query": query,
            "max_results": count,
        }
        if time_filter:
            time_range, date = _parse_time_filter(time_filter)
            if time_range:
                parameters["time_range"] = time_range
            elif date:
                parameters["start_date"] = date[0]
                parameters["end_date"] = date[1]

        result_text = self.tool.run_tool(parameters)

        # process the result text
        texts = result_text.split("\nTitle: ")
        search_results = []
        for text in texts:
            if "URL: " not in text:
                continue
            title, text = text.split("\nURL: ")
            url, content = text.split("\nContent: ", 1)

            search_result = SearchResult(
                title=title.strip(),
                url=url.strip(),
                content=content.strip(),
                source="Tavily",
            )
            search_results.append(search_result)

        return search_results
