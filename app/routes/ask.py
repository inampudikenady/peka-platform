from fastapi import APIRouter

from app.models import AskRequest, AskResponse
from app.rag_engine import run_peka_question
from app.correlation.context_builder import enrich_question_with_operational_context
from app.routing.source_router import route_sources


router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    route = route_sources(req.question)
    intent = route["intent"]
    sources = route["sources"]

    enriched_question = enrich_question_with_operational_context(req.question)

    # Operational questions already have enriched source context.
    # Do not retrieve documents unless docs are explicitly needed.
    skip_retrieval = not sources.get("docs")

    answer, rag_sources = run_peka_question(
        enriched_question,
        skip_retrieval=skip_retrieval,
    )

    return {
        "question": req.question,
        "answer": answer,
        "sources": rag_sources if sources.get("docs") else [],
    }
