import os

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
from app.routes.servicenow import router as servicenow_router
from app.routes.monitoring import router as monitoring_router
from app.routes.logs import router as logs_router
from app.routes.ops import router as ops_router
from app.routes.cmdb import router as cmdb_router
from app.routes import settings




def print_startup_banner():
    print("\n====================================")
    print("PEKA Startup")
    print("====================================")
    print(f"Customer Profile : {os.getenv('CUSTOMER_PROFILE', 'unknown')}")
    print(f"Ticket Provider  : {os.getenv('TICKET_PROVIDER', 'unknown')}")
    print(f"CMDB Provider    : {os.getenv('CMDB_PROVIDER', 'unknown')}")
    print(f"Monitoring       : {os.getenv('MONITORING_PROVIDER', 'unknown')}")
    print(f"Logs             : {os.getenv('LOG_PROVIDER', 'unknown')}")
    print("====================================\n")


print_startup_banner()


app = FastAPI(title=f"{APP_NAME} - {APP_FULL_NAME}")

app.include_router(ask_router)
app.include_router(openai_v1_router)
app.include_router(ui_router)
app.include_router(servicenow_router)
app.include_router(monitoring_router)
app.include_router(logs_router)
app.include_router(ops_router)
app.include_router(cmdb_router)
app.include_router(settings.router)


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
        "customer_profile": os.getenv("CUSTOMER_PROFILE", "unknown"),
        "ticket_provider": os.getenv("TICKET_PROVIDER", "unknown"),
        "cmdb_provider": os.getenv("CMDB_PROVIDER", "unknown"),
        "monitoring_provider": os.getenv("MONITORING_PROVIDER", "unknown"),
        "log_provider": os.getenv("LOG_PROVIDER", "unknown"),
        "ui": "/ui",
        "openai_compatible_base_url": "/v1",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "customer_profile": os.getenv("CUSTOMER_PROFILE", "unknown"),
        "ticket_provider": os.getenv("TICKET_PROVIDER", "unknown"),
        "cmdb_provider": os.getenv("CMDB_PROVIDER", "unknown"),
        "monitoring_provider": os.getenv("MONITORING_PROVIDER", "unknown"),
        "log_provider": os.getenv("LOG_PROVIDER", "unknown"),
    }