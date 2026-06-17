import os
from pathlib import Path

from dotenv import load_dotenv
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader, StorageContext
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

load_dotenv()

WIKI_PATH = os.getenv("PEKA_WIKI_PATH", "/data/wiki-raw/compose_files/unixdocs/config/dokuwiki/data/pages/unix")
COLLECTION_NAME = os.getenv("PEKA_COLLECTION", "unixdocs")
EMBED_MODEL_NAME = os.getenv("PEKA_EMBED_MODEL", "BAAI/bge-base-en-v1.5")
QDRANT_HOST = os.getenv("PEKA_QDRANT_HOST", "localhost")
QDRANT_PORT = int(os.getenv("PEKA_QDRANT_PORT", "6333"))
CHUNK_SIZE = int(os.getenv("PEKA_CHUNK_SIZE", "800"))
CHUNK_OVERLAP = int(os.getenv("PEKA_CHUNK_OVERLAP", "100"))

if not Path(WIKI_PATH).exists():
    raise SystemExit(f"Wiki path does not exist: {WIKI_PATH}")

print(f"Loading documents from: {WIKI_PATH}")
documents = SimpleDirectoryReader(
    WIKI_PATH,
    recursive=True,
    required_exts=[".txt"],
).load_data()

print(f"Loaded {len(documents)} documents")

splitter = SentenceSplitter(
    chunk_size=CHUNK_SIZE,
    chunk_overlap=CHUNK_OVERLAP,
)

print(f"Loading embedding model: {EMBED_MODEL_NAME}")
embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)

print(f"Connecting to Qdrant: {QDRANT_HOST}:{QDRANT_PORT}, collection={COLLECTION_NAME}")
client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

vector_store = QdrantVectorStore(
    client=client,
    collection_name=COLLECTION_NAME,
)

storage_context = StorageContext.from_defaults(vector_store=vector_store)

print("Creating index...")
VectorStoreIndex.from_documents(
    documents,
    transformations=[splitter],
    embed_model=embed_model,
    storage_context=storage_context,
    show_progress=True,
)

print("Done.")
print(f"Collection: {COLLECTION_NAME}")
