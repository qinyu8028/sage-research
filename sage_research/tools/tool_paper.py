import logging
import os
import shutil
import tempfile
from typing import Any

from .base_tool import BaseTool, ToolParameter, ToolCallError
from ..mcp.tool_adapter import MCPTool

logger = logging.getLogger(__name__)


class PaperReaderTool(BaseTool):
    """combine mcptools: download_arxiv + read_arxiv_paper"""

    def __init__(self, download_tool: MCPTool, read_tool: MCPTool):
        super().__init__(
            name="read_arxiv_paper",
            description=(
                "Download and read the full text of an arXiv paper.\n"
                "\n"
                "When to use: you have an arXiv paper ID (e.g. '2106.09685') and need "
                "the full paper content — not just the abstract or a web page snippet.\n"
                "When NOT to use: you only need the abstract or metadata (use search_arxiv instead), "
                "or the paper is not on arXiv.\n"
                "\n"
                "Returns: the complete paper text extracted from PDF (abstract through conclusion, "
                "including tables and references). Typically 30K-80K characters."
            ),
            parameters=[
                ToolParameter(
                    name="paper_id",
                    type="string",
                    description="arXiv paper ID, e.g. '2106.09685' or '2106.09685v2'.",
                ),
            ],
        )
        self._download_tool = download_tool
        self._read_tool = read_tool
        self._download_dir = os.path.join(tempfile.gettempdir(), "sage_arxiv_papers")

    def run_tool(self, parameters: dict[str, Any]) -> str:
        paper_id = parameters.get("paper_id", "").strip()
        if not paper_id:
            return "Error: missing required parameter 'paper_id'."

        os.makedirs(self._download_dir, exist_ok=True)

        pdf_path = os.path.join(self._download_dir, f"{paper_id}.pdf")
        if os.path.exists(pdf_path):
            logger.info("[PaperReader] cache hit: %s", paper_id)
        else:
            self._download_tool.run_tool({"paper_id": paper_id, "save_path": self._download_dir})
            logger.info("[PaperReader] downloaded: %s", paper_id)

        content = self._read_tool.run_tool({"paper_id": paper_id, "save_path": self._download_dir})
        logger.info("[PaperReader] read: %s, %d chars", paper_id, len(content))
        return content

    def cleanup(self):
        if os.path.exists(self._download_dir):
            shutil.rmtree(self._download_dir)
            logger.info("[PaperReader] cleaned up: %s", self._download_dir)
