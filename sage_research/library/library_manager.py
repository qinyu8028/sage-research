import json
import os
import re
import shutil
from datetime import datetime

from .converter import convert_to_markdown, get_conversion_metadata
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
        self, src: str, custom_title: str | None = None, overwrite: bool = True,
        save_original: bool = True,
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

        pending_metadata = get_conversion_metadata(
            src=src,
            output_dir=self.converted_dir,
            custom_title=custom_title,
        )

        existing = None
        for entry in entries:
            if entry["title"] == pending_metadata.title:
                existing = entry
                break

        if existing and not overwrite:
            return IngestResult(
                title=pending_metadata.title,
                status="skipped"
            )

        metadata = convert_to_markdown(
            src=src,
            output_dir=self.converted_dir,
            paper_tool=self.paper_tool,
            pdfmux_tool=self.pdfmux_tool,
            custom_title=custom_title,
        )

        if existing:
            self._remove_files(existing, keep_converted_path=metadata.output_path)
            entries.remove(existing)
            status = "overwritten"
        else:
            status = "created"

        if save_original:
            if arxiv_match:
                pdf_src = os.path.join(self.paper_tool.download_dir, f"{src}.pdf")
                if os.path.exists(pdf_src):
                    shutil.copy(pdf_src, self.originals_dir)
            else:
                shutil.copy(src, self.originals_dir)

        self.pipeline.add_document(metadata.output_path, save=False)

        index_entry_dict = {
            "title": metadata.title,
            "arxiv_id": metadata.arxiv_id,
            "converted_path": metadata.output_path,
            "source_type": metadata.source_type,
            "added_at": datetime.now().isoformat()
        }
        if save_original:
            if arxiv_match:
                original_path = os.path.join(self.originals_dir, f"{src}.pdf")
            else:
                original_path = os.path.join(self.originals_dir, os.path.basename(src))
            index_entry_dict["original_path"] = original_path
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
    
    def _remove_files(self, entry: dict, keep_converted_path: str | None = None):
        """清理 vector store + 磁盘文件，不 save, 需要额外调用save"""
        converted_path = entry["converted_path"]
        self.pipeline.vector_store.remove_by_filepath(converted_path)
        should_keep_converted = (
            keep_converted_path is not None
            and os.path.abspath(converted_path) == os.path.abspath(keep_converted_path)
        )
        if not should_keep_converted and os.path.exists(converted_path):
            os.remove(converted_path)
        orig = entry.get("original_path")
        if orig and os.path.exists(orig):
            os.remove(orig)
