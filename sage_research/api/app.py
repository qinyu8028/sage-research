import json

import logging

from contextlib import asynccontextmanager
from fastapi import FastAPI, Request
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
    app.state.clarifier = Clarifier(llm=orchestrator.llm_client)
    app.state.library_manager = orchestrator.create_library_manager()
    yield
    orchestrator.close()


app = FastAPI(lifespan=lifespan)


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
                        "sub_questions": [sq.question for sq in output["sub_questions"]]
                    }

                elif node_name == "research_node":
                    event_type = "research"
                    question, note = output["pending_review_pairs"][0]
                    data = {
                        "question": question,
                        "preview": note[:PREVIEW_LENGTH] + "...",
                    }

                elif node_name == "review_node":
                    event_type = "review"
                    data = {
                        "round": output["refine_round"],
                        "review_summary": output["review_summary"],
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
