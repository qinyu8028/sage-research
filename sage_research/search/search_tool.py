from typing import Any
from sage_research.mcp.tool_adapter import MCPTool
from sage_research.tools import BaseTool, ToolParameter
from .adapter import BraveAdapter, TavilyAdapter


class SearchTool(BaseTool):
    def __init__(
        self,
        brave_tool: MCPTool,
        tavily_tool: MCPTool,
    ):
        super().__init__(
            name="search",
            description=(
                "Search the web for current information on any topic.\n"
                "\n"
                "When to use: need up-to-date information, fact verification, "
                "or gathering sources for a research topic.\n"
                "When NOT to use: the answer is already available in conversation "
                "context or previously retrieved documents.\n"
                "\n"
                "Returns: a list of search results, each containing title, URL, "
                "and content snippet."
            ),
            parameters=[
                ToolParameter(
                    name="query",
                    type="string",
                    description=(
                        "The search query string. Use specific keywords for better results. "
                        'Example: "transformer self-attention mechanism 2017" '
                        'rather than "transformer".'
                    ),
                ),
                ToolParameter(
                    name="count",
                    type="integer",
                    description="Number of results to return. Range: 1-20. Default: 5.",
                    required=False,
                    default=5,
                ),
                ToolParameter(
                    name="time_filter",
                    type="string",
                    description=(
                        "Filter results by time. Either a relative keyword: "
                        '"day", "week", "month", "year", '
                        'or an absolute date range in "YYYY-MM-DDtoYYYY-MM-DD" format. '
                        'Example: "week" or "2025-01-01to2025-06-01".'
                    ),
                    required=False,
                ),
            ],
        )
        self.brave_adapter = BraveAdapter(brave_tool)
        self.tavily_adapter = TavilyAdapter(tavily_tool)

    @staticmethod
    def _format_results(result_list: list) -> str:
        return "\n\n".join(f"[{i}] {result}" for i, result in enumerate(result_list, 1))

    def run_tool(self, parameters: dict[str, Any]) -> str:
        query = parameters.get("query")
        if not query:
            return "Error: missing required parameter 'query'. Provide a search query string."
        count = parameters.get("count")
        time_filter = parameters.get("time_filter")

        kwargs = {"query": query}
        if count is not None:
            kwargs["count"] = count
        if time_filter is not None:
            kwargs["time_filter"] = time_filter

        brave_error = False
        tavily_error = False

        try:
            result_list = self.brave_adapter.search(**kwargs)
            if result_list:
                print(f"  [SearchTool] Brave 返回 {len(result_list)} 条结果")
                return self._format_results(result_list)
            print(f"  [SearchTool] Brave 返回空结果，尝试 Tavily")
        except Exception as e:
            brave_error = True
            print(f"  [SearchTool] Brave 异常: {e}，fallback 到 Tavily")

        try:
            result_list = self.tavily_adapter.search(**kwargs)
            if result_list:
                print(f"  [SearchTool] Tavily 返回 {len(result_list)} 条结果")
                return self._format_results(result_list)
            print(f"  [SearchTool] Tavily 返回空结果")
        except Exception as e:
            tavily_error = True
            print(f"  [SearchTool] Tavily 异常: {e}")

        if brave_error and tavily_error:
            print(f"  [SearchTool] 所有搜索源不可用")
            return (
                "Error: all search services are currently unavailable. "
                "Continue working with the information you already have."
            )
        print(f"  [SearchTool] 所有搜索源均无结果，query: {query}")
        return (
            f"No results found for query '{query}'. "
            "Try rephrasing with different or broader keywords."
        )
