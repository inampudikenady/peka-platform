from fastapi import APIRouter

from app.models import AskRequest, AskResponse
from app.rag_engine import run_peka_question
from app.tools.context_builder import enrich_question_with_operational_context


router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    enriched_question = enrich_question_with_operational_context(req.question)

    answer, sources = run_peka_question(enriched_question)

    return {
        "question": req.question,
        "answer": answer,
        "sources": sources,
    }
