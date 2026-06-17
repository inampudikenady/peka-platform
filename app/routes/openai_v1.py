import time

from fastapi import APIRouter

from app.config import APP_NAME
from app.models import ChatCompletionRequest
from app.rag_engine import run_peka_question
from app.correlation.context_builder import enrich_question_with_operational_context
from app.routing.source_router import route_sources


router = APIRouter()


@router.get("/v1/models")
def list_models():
    return {
        "object": "list",
        "data": [
            {
                "id": "peka-rag",
                "object": "model",
                "created": int(time.time()),
                "owned_by": APP_NAME,
            }
        ],
    }


@router.post("/v1/chat/completions")
def chat_completions(req: ChatCompletionRequest):
    user_messages = [
        m.content for m in req.messages if m.role == "user"
    ]

    if not user_messages:
        return {
            "error": {
                "message": "No user message found.",
                "type": "invalid_request_error",
            }
        }

    question = user_messages[-1]
    route = route_sources(question)
    sources_enabled = route["sources"]

    enriched_question = enrich_question_with_operational_context(question)

    skip_retrieval = not sources_enabled.get("docs")

    answer, sources = run_peka_question(
        enriched_question,
        skip_retrieval=skip_retrieval,
    )

    # Show wiki sources only when the question is documentation/procedure oriented.
    if sources_enabled.get("docs") and sources:
        source_text = "\n\nSources:\n" + "\n".join(
            [
                f"- {src['file_name']}: {src['file_path']}"
                for src in sources
            ]
        )
        final_answer = answer + source_text
    else:
        final_answer = answer

    return {
        "id": f"chatcmpl-peka-{int(time.time())}",
        "object": "chat.completion",
        "created": int(time.time()),
        "model": req.model or "peka-rag",
        "choices": [
            {
                "index": 0,
                "message": {
                    "role": "assistant",
                    "content": final_answer,
                },
                "finish_reason": "stop",
            }
        ],
        "usage": {
            "prompt_tokens": 0,
            "completion_tokens": 0,
            "total_tokens": 0,
        },
    }
