from fastapi import FastAPI

from app.config import (
    APP_FULL_NAME,
    APP_NAME,
    COLLECTION_NAME,
    DATASET_NAME,
    EMBED_MODEL_NAME,
    FINAL_TOP_K,
    LLM_MODEL,
    RETRIEVAL_TOP_K,
)
from app.routes.ask import router as ask_router
from app.routes.openai_v1 import router as openai_v1_router
from app.routes.ui import router as ui_router


app = FastAPI(title=f"{APP_NAME} - {APP_FULL_NAME}")

app.include_router(ask_router)
app.include_router(openai_v1_router)
app.include_router(ui_router)


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": f"{APP_NAME} - {APP_FULL_NAME}",
        "dataset": DATASET_NAME,
        "collection": COLLECTION_NAME,
        "model": LLM_MODEL,
        "embedding_model": EMBED_MODEL_NAME,
        "retrieval": f"top{RETRIEVAL_TOP_K}_rerank_to_top{FINAL_TOP_K}_compressed",
        "ui": "/ui",
        "openai_compatible_base_url": "/v1",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}
