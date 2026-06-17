from fastapi import APIRouter

from app.models import AskRequest, AskResponse
from app.rag_engine import run_peka_question
from app.correlation.context_builder import enrich_question_with_operational_context
from app.routing.intent_detector import detect_intent, extract_identifier


router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    intent = detect_intent(req.question)
    identifier = extract_identifier(req.question)

    enriched_question = enrich_question_with_operational_context(req.question)

    if identifier and intent in ["health", "logs", "history", "cmdb"]:
        answer, _sources = run_peka_question(
            enriched_question,
            skip_retrieval=True,
        )

        return {
            "question": req.question,
            "answer": answer,
            "sources": [],
        }

    answer, sources = run_peka_question(enriched_question)

    return {
        "question": req.question,
        "answer": answer,
        "sources": sources,
    }