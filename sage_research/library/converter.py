import re, os, shutil

from pydantic import BaseModel
from ..tools import PaperReaderTool
from ..mcp import MCPTool


class ConvertMetadata(BaseModel):
    output_path: str
    source_type: str
    arxiv_id: str | None = None
    title: str


def convert_to_markdown(
    src: str,
    output_dir: str,
    paper_tool: PaperReaderTool | None,
    pdfmux_tool: MCPTool | None,
    custom_title: str | None = None,
) -> ConvertMetadata:
    """将文献源转换为 markdown 文件并写入 output_dir。

    Args:
        src: 文献源，支持arXiv ID, 本地 .pdf, .md,.txt
        output_dir: 转换后 markdown 文件的输出目录
        paper_tool: arXiv 论文下载+读取工具
        pdfmux_tool: PDF 转换工具
        custom_title: 自定义标题，不提供则从文件名推断

    Returns:
        ConvertMetadata: output_path, source_type, arxiv_id, title
    """

    is_arxiv_id = re.match(r"^\d{4}\.\d{4,5}", src)
    if is_arxiv_id:
        source_type = "arxiv"
        title = custom_title or f"arXiv:{src}"
    else:
        ext = os.path.splitext(src)[-1].lower()
        title = custom_title or os.path.splitext(os.path.basename(src))[0]

        ext_to_type = {".pdf": "pdf", ".md": "markdown", ".markdown": "markdown", ".txt": "text"}
        source_type = ext_to_type.get(ext)

        if not source_type:
            raise ValueError(f"不支持的文件类型: {ext}")

    dest = os.path.join(output_dir, f"{title}.md")

    if source_type == "arxiv":
        text = paper_tool.run_tool({"paper_id": src})
        with open(dest, "w", encoding="utf-8") as f:
            f.write(text)
    elif source_type == "pdf":
        text = pdfmux_tool.run_tool({"file_path": src})
        with open(dest, "w", encoding="utf-8") as f:
            f.write(text)
    else:  # markdown / text
        shutil.copy(src, dest)

    return ConvertMetadata(
        output_path=dest,
        source_type=source_type,
        arxiv_id=src if source_type == "arxiv" else None,
        title=title,
    )