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
    settings,
)
from app.routes.ask import router as ask_router
from app.routes.openai_v1 import router as openai_v1_router
from app.routes.cmdb import router as cmdb_router
from app.routes import settings as settings_route




def print_startup_banner():
    print("\n====================================")
    print("PEKA Startup")
    print("====================================")
    print(f"Customer Profile : {settings['customer_profile']}")
    print(f"Ticket Provider  : {settings['ticket_provider']}")
    print(f"CMDB Provider    : {settings['cmdb_provider']}")
    print(f"Monitoring       : {settings['monitoring_provider']}")
    print(f"Logs             : {settings['log_provider']}")
    print("====================================\n")


print_startup_banner()


app = FastAPI(title=f"{APP_NAME} - {APP_FULL_NAME}")

app.include_router(ask_router)
app.include_router(openai_v1_router)
app.include_router(cmdb_router)
app.include_router(settings_route.router)


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
        "customer_profile": settings["customer_profile"],
        "ticket_provider": settings["ticket_provider"],
        "cmdb_provider": settings["cmdb_provider"],
        "monitoring_provider": settings["monitoring_provider"],
        "log_provider": settings["log_provider"],
        "portal": "http://localhost:3001",
        "openai_compatible_base_url": "/v1",
    }


@app.get("/health")
def health():
    return {
        "status": "healthy",
        "customer_profile": settings["customer_profile"],
        "ticket_provider": settings["ticket_provider"],
        "cmdb_provider": settings["cmdb_provider"],
        "monitoring_provider": settings["monitoring_provider"],
        "log_provider": settings["log_provider"],
    }
