from fastapi import APIRouter

from app.models import AskRequest, AskResponse
from app.rag_engine import run_peka_question


router = APIRouter()


@router.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    answer, sources = run_peka_question(req.question)

    return {
        "question": req.question,
        "answer": answer,
        "sources": sources,
    }
