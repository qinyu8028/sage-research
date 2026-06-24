import json
import logging
import os
import shutil
import tempfile

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request, UploadFile
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import StreamingResponse

from sage_research.agents import Clarifier
from sage_research.base import LLMClient, setup_logging
from sage_research.config import Config
from sage_research.library.library_manager import LibraryManager
from sage_research.orchestrator import Orchestrator
from .schemas import (
    ClarifyRequest,
    ClarifyResult,
    RefineRequest,
    RefineResult,
    ResearchRequest,
    SaveReportRequest,
    IngestRequest,
    IngestResult,
)

logger = logging.getLogger(__name__)

PREVIEW_LENGTH = 150


@asynccontextmanager
async def lifespan(app: FastAPI):
    setup_logging(enable_display=False)
    orchestrator = Orchestrator(Config())
    app.state.orchestrator = orchestrator
    app.state.clarifier = Clarifier(llm=orchestrator.llm_client, creative_temperature=orchestrator.config.llm.research_temperature)
    app.state.library_manager = orchestrator.create_library_manager()
    yield
    orchestrator.close()


app = FastAPI(lifespan=lifespan)
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])


@app.post("/api/clarify")
def clarify(body: ClarifyRequest, request: Request) -> ClarifyResult:
    clarifier: Clarifier = request.app.state.clarifier
    result = clarifier.analyze(body.query)
    return result


@app.post("/api/clarify/refine")
def refine(body: RefineRequest, request: Request) -> RefineResult:
    clarifier: Clarifier = request.app.state.clarifier
    result = clarifier.refine(raw_query=body.query, user_response=body.response)
    return RefineResult(brief=result)


@app.post("/api/research")
def research(body: ResearchRequest, request: Request):
    orchestrator: Orchestrator = request.app.state.orchestrator
    events = orchestrator.run_research(body.brief)

    return StreamingResponse(
        format_sse_events(events=events, llm_client=orchestrator.llm_client),
        media_type="text/event-stream",
    )


@app.get("/api/library")
def list_docs(request: Request):
    library_manager: LibraryManager = request.app.state.library_manager
    result = library_manager.list_docs()
    return result


@app.post("/api/library/save-report")
def save_report(body: SaveReportRequest, request: Request) -> IngestResult:
    library_manager: LibraryManager = request.app.state.library_manager
    safe_name = body.title.replace("/", "_").replace("\\", "_")
    tmp_dir = tempfile.mkdtemp(dir=library_manager.data_dir)
    src = os.path.join(tmp_dir, f"{safe_name}.md")
    try:
        with open(src, "w", encoding="utf-8") as f:
            f.write(body.content)
        result = library_manager.ingest(
            src=src, custom_title=body.title, overwrite=True,
            save_original=False,
        )
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return result


@app.post("/api/library/upload")
def upload_file(file: UploadFile, request: Request) -> IngestResult:
    library_manager: LibraryManager = request.app.state.library_manager
    filename = file.filename or "upload.pdf"
    safe_name = filename.replace("/", "_").replace("\\", "_")
    tmp_dir = tempfile.mkdtemp(dir=library_manager.data_dir)
    src = os.path.join(tmp_dir, safe_name)
    try:
        with open(src, "wb") as f:
            f.write(file.file.read())
        result = library_manager.ingest(src=src, overwrite=True)
    finally:
        shutil.rmtree(tmp_dir, ignore_errors=True)
    return result


@app.post("/api/library/ingest")
def ingest(body: IngestRequest, request: Request) -> IngestResult:
    library_manager: LibraryManager = request.app.state.library_manager
    result = library_manager.ingest(
        src=body.src,
        custom_title=body.custom_title,
        overwrite=body.overwrite,
    )
    return result


@app.delete("/api/library/{title}")
def delete_doc(title: str, request: Request):
    library_manager: LibraryManager = request.app.state.library_manager
    library_manager.delete_doc(title)
    return {"message": f"deleted: {title}"}


def format_sse_events(events, llm_client: LLMClient):
    try:
        for event in events:
            for node_name, output in event.items():
                if node_name == "plan_node":
                    event_type = "plan"
                    data = {
                        "sub_questions": [
                            {"label": sq.label, "question": sq.question}
                            for sq in output["sub_questions"]
                        ]
                    }

                elif node_name == "research_node":
                    event_type = "research"
                    question, note = output["pending_review_pairs"][0]
                    data = {
                        "question": question,
                        "preview": note[:PREVIEW_LENGTH] + "...",
                        "tool_call_counts": output.get("tool_call_counts", {}),
                    }

                elif node_name == "review_node":
                    event_type = "review"
                    data = {
                        "round": output["refine_round"],
                        "review_summary": [
                            {
                                "question": r["question"],
                                "verdict": r["verdict"],
                                "failed": r["failed"],
                                "evidence": r.get("evidence", {}),
                            }
                            for r in output["review_summary"]
                        ],
                        "missing_dimensions": output.get("missing_dimensions", ""),
                    }

                elif node_name == "write_node":
                    event_type = "write"
                    data = {"report": output["final_report"]}

                else:
                    continue

                yield f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"

        stats_data = {
            "total_calls": llm_client.total_calls,
            "prompt_tokens": llm_client.total_prompt_tokens,
            "completion_tokens": llm_client.total_completion_tokens,
            "total_tokens": llm_client.total_prompt_tokens
            + llm_client.total_completion_tokens,
        }
        yield f"event: stats\ndata: {json.dumps(stats_data, ensure_ascii=False)}\n\n"

    except Exception as e:
        # error event
        yield f"event: error\ndata: {json.dumps({'message': str(e)})}\n\n"
