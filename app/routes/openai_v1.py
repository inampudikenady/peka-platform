import time

from fastapi import APIRouter

from app.config import APP_NAME
from app.models import ChatCompletionRequest
from app.rag_engine import run_peka_question

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
    """
    OpenAI-compatible endpoint for Open WebUI integration.

    Open WebUI may send:
        "stream": true

    PEKA currently ignores streaming requests and returns
    a standard non-streamed response for compatibility.
    """

    user_messages = [m.content for m in req.messages if m.role == "user"]

    if not user_messages:
        return {
            "error": {
                "message": "No user message found.",
                "type": "invalid_request_error",
            }
        }

    question = user_messages[-1]

    answer, sources = run_peka_question(question)

    if sources:
        source_text = "\n\nSources:\n" + "\n".join(
            [f"- {src['file_name']}: {src['file_path']}" for src in sources]
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
