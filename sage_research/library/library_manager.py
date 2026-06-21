import json
import os
import re
import shutil
from datetime import datetime

from .converter import convert_to_markdown
from ..tools import PaperReaderTool
from ..mcp import MCPTool
from ..rag import Pipeline
from ..api.schemas import IngestResult


class LibraryManager:
    def __init__(
        self,
        data_dir,
        paper_tool: PaperReaderTool,
        pdfmux_tool: MCPTool,
        pipeline: Pipeline
    ):
        self.paper_tool = paper_tool
        self.pdfmux_tool = pdfmux_tool
        self.pipeline = pipeline
        self.data_dir = data_dir
        self.originals_dir = os.path.join(data_dir, "originals")
        self.converted_dir = os.path.join(data_dir, "converted")
        self.index_path = os.path.join(data_dir, "index.json")

        os.makedirs(self.originals_dir, exist_ok=True)
        os.makedirs(self.converted_dir, exist_ok=True)

    def ingest(
        self, src: str, custom_title: str = None, overwrite: bool = True
    ) -> IngestResult:

        entries = self.list_docs()

        arxiv_match = re.match(r"^\d{4}\.\d{4,5}", src)
        if arxiv_match:
            for entry in entries:
                if entry.get("arxiv_id") == arxiv_match.group():
                    return IngestResult(
                        title=src,
                        status="skipped"
                    )

        metadata = convert_to_markdown(
            src=src,
            output_dir=self.converted_dir,
            paper_tool=self.paper_tool,
            pdfmux_tool=self.pdfmux_tool,
            custom_title=custom_title,
        )

        # dedup
        existing = None
        for entry in entries:
            if entry["title"] == metadata.title:
                existing = entry
                break

        if existing:
            if not overwrite:
                return IngestResult(
                    title=metadata.title,
                    status="skipped"
                )
            else:
                self._remove_files(existing)
                entries.remove(existing)
                status = "overwritten"
        else:
            status = "created"

        if arxiv_match:
            pdf_src = os.path.join(self.paper_tool.download_dir, f"{src}.pdf")
            if os.path.exists(pdf_src):
                shutil.copy(pdf_src, self.originals_dir)
        else:
            shutil.copy(src, self.originals_dir)

        self.pipeline.add_document(metadata.output_path, save=False)

        if arxiv_match:
            original_path = os.path.join(self.originals_dir, f"{src}.pdf")
        else:
            original_path = os.path.join(self.originals_dir, os.path.basename(src))

        index_entry_dict = {
            "title": metadata.title,
            "arxiv_id": metadata.arxiv_id,
            "original_path": original_path,
            "converted_path": metadata.output_path,
            "source_type": metadata.source_type,
            "added_at": datetime.now().isoformat()
        }
        entries.append(index_entry_dict)

        self._save_index(entries)
        self.pipeline.save()

        return IngestResult(
            title=metadata.title,
            status=status
        )

    def list_docs(self) -> list[dict]:
        if not os.path.exists(self.index_path):
            return []
        with open(self.index_path, "r", encoding="utf-8") as f:
            return json.load(f)

    def delete_doc(self, title: str):
        entries = self.list_docs()

        for entry in entries:
            if entry["title"] == title:
                existing = entry
                self._remove_files(existing)
                entries.remove(existing)

        self._save_index(entries)
        self.pipeline.save()

    def _save_index(self, entries: list[dict]):
        with open(self.index_path, "w", encoding="utf-8") as f:
            json.dump(entries, f, ensure_ascii=False, indent=2)
    
    def _remove_files(self, entry: dict):
        """清理 vector store + 磁盘文件，不 save, 需要额外调用save"""
        self.pipeline.vector_store.remove_by_filepath(entry["converted_path"])
        if os.path.exists(entry["converted_path"]):
            os.remove(entry["converted_path"])
        orig = entry.get("original_path")
        if orig and os.path.exists(orig):
            os.remove(orig)
