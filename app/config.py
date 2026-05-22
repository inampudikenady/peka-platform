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
