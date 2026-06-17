import os
from dotenv import load_dotenv

load_dotenv()

APP_NAME = os.getenv("PEKA_APP_NAME", "PEKA")
APP_FULL_NAME = os.getenv("PEKA_APP_FULL_NAME", "Private Enterprise Knowledge Assistant")
DATASET_NAME = os.getenv("PEKA_DATASET_NAME", "Demo Enterprise Knowledge Base")
COLLECTION_NAME = os.getenv("PEKA_COLLECTION", "unixdocs")
EMBED_MODEL_NAME = os.getenv("PEKA_EMBED_MODEL", "BAAI/bge-base-en-v1.5")
LLM_MODEL = os.getenv("PEKA_MODEL", "qwen2.5:3b")
QDRANT_HOST = os.getenv("PEKA_QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("PEKA_QDRANT_PORT", "6333"))

RETRIEVAL_TOP_K = int(os.getenv("PEKA_RETRIEVAL_TOP_K", "8"))
FINAL_TOP_K = int(os.getenv("PEKA_FINAL_TOP_K", "5"))
LLM_TIMEOUT = float(os.getenv("PEKA_LLM_TIMEOUT", "1800"))
MAX_COMPRESSED_LINES_PER_SOURCE = int(os.getenv("PEKA_MAX_COMPRESSED_LINES_PER_SOURCE", "28"))

SECRET_KEYS = [
    "PASSWORD",
    "TOKEN",
    "SECRET",
    "CLIENT_SECRET",
]


def _get(name: str, default: str = "") -> str:
    return os.getenv(name, default)


def _mask(name: str, value: str) -> str:
    if not value:
        return ""

    if any(secret in name.upper() for secret in SECRET_KEYS):
        if len(value) <= 4:
            return "****"
        return "****" + value[-4:]

    return value


def get_settings(mask_secrets: bool = True) -> dict:
    settings = {
        "company": _get("COMPANY", "Local Demo"),
        "customer_profile": _get("CUSTOMER_PROFILE", "local"),

        "auth_provider": _get("AUTH_PROVIDER", "local"),
        "cmdb_provider": _get("CMDB_PROVIDER", "auto"),
        "ticket_provider": _get("TICKET_PROVIDER", "zammad"),
        "monitoring_provider": _get("MONITORING_PROVIDER", "docker_prometheus"),
        "log_provider": _get("LOG_PROVIDER", "loki"),

        "peka_collection": COLLECTION_NAME,
        "peka_data_dir": _get("PEKA_DATA_DIR", "./data"),
        "peka_cmdb_file": _get("PEKA_CMDB_FILE", "./data/cmdb/tuple_cmdb.csv"),
        "peka_wiki_path": _get("PEKA_WIKI_PATH", "./data/docs"),

        "qdrant_host": QDRANT_HOST,
        "qdrant_port": str(QDRANT_PORT),

        "model": LLM_MODEL,
        "embed_model": EMBED_MODEL_NAME,

        "prometheus_url": _get("PROMETHEUS_URL", "http://localhost:9090"),
        "loki_url": _get("LOKI_URL", "http://localhost:3100"),

        "zammad_url": _get("ZAMMAD_URL", ""),
        "zammad_token": _get("ZAMMAD_TOKEN", ""),

        "servicenow_instance": _get("SERVICENOW_INSTANCE", ""),
        "servicenow_user": _get("SERVICENOW_USER", ""),
        "servicenow_password": _get("SERVICENOW_PASSWORD", ""),

        "azure_subscription_id": _get("AZURE_SUBSCRIPTION_ID", ""),
        "azure_tenant_id": _get("AZURE_TENANT_ID", ""),
        "azure_client_id": _get("AZURE_CLIENT_ID", ""),
        "azure_client_secret": _get("AZURE_CLIENT_SECRET", ""),

        "vcenter_server": _get("VCENTER_SERVER", ""),
        "vcenter_user": _get("VCENTER_USER", ""),
        "vcenter_password": _get("VCENTER_PASSWORD", ""),

        "solarwinds_url": _get("SOLARWINDS_URL", ""),
        "solarwinds_user": _get("SOLARWINDS_USER", ""),
        "solarwinds_password": _get("SOLARWINDS_PASSWORD", ""),
    }

    if mask_secrets:
        return {k: _mask(k, str(v)) for k, v in settings.items()}

    return settings


def validate_settings() -> dict:
    settings = get_settings(mask_secrets=False)

    checks = {
        "cmdb_file_exists": os.path.exists(settings["peka_cmdb_file"]),
        "data_dir_exists": os.path.exists(settings["peka_data_dir"]),
        "wiki_path_exists": os.path.exists(settings["peka_wiki_path"]),
    }

    return {
        "settings": get_settings(mask_secrets=True),
        "checks": checks,
    }
