import time

from fastapi import APIRouter

from app.config import APP_NAME
from app.models import ChatCompletionRequest
from app.rag_engine import run_peka_question
from app.correlation.context_builder import enrich_question_with_operational_context
from app.routing.source_router import route_sources
from app.sources.azure.azure_response import build_azure_response


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

    if sources_enabled.get("azure"):
        answer = build_azure_response(question)
        sources = []
        final_answer = answer
    else:
        enriched_question = enrich_question_with_operational_context(question)

        skip_retrieval = not sources_enabled.get("docs")

        answer, sources = run_peka_question(
            enriched_question,
            skip_retrieval=skip_retrieval,
        )

    # For documentation/procedure questions, append sources from API metadata.
    # The model should not generate its own Sources section.
    if not sources_enabled.get("azure"):
        if sources_enabled.get("docs") and sources:
            answer = strip_model_generated_sources(answer)

            source_text = "\n\nSources:\n" + "\n".join(
                [
                    f"- {src['file_name']}: {src['file_path']}"
                    for src in dedupe_sources(sources)
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

def strip_model_generated_sources(answer: str) -> str:
    markers = [
        "\nSources\n",
        "\nSources:\n",
        "\n## Sources\n",
        "\n## Sources:\n",
    ]

    for marker in markers:
        if marker in answer:
            return answer.split(marker, 1)[0].rstrip()

    return answer.rstrip()


def dedupe_sources(sources: list[dict]) -> list[dict]:
    seen = set()
    unique_sources = []

    for src in sources:
        key = (
            src.get("file_name", ""),
            src.get("file_path", ""),
        )

        if key in seen:
            continue

        seen.add(key)
        unique_sources.append(src)

    return unique_sources

