from pathlib import Path
from llama_index.core import VectorStoreIndex, SimpleDirectoryReader
from llama_index.core.node_parser import SentenceSplitter
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext
from qdrant_client import QdrantClient

# Wiki location
WIKI_PATH = "/data/wiki-raw/compose_files/unixdocs/config/dokuwiki/data/pages/unix"

# Qdrant settings
COLLECTION_NAME = "unixdocs"

print("Loading documents...")

documents = SimpleDirectoryReader(
    WIKI_PATH,
    recursive=True,
    required_exts=[".txt"]
).load_data()

print(f"Loaded {len(documents)} documents")

# Chunking
splitter = SentenceSplitter(
    chunk_size=800,
    chunk_overlap=100
)

# Embedding model
embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-base-en-v1.5"
)

# Qdrant connection
client = QdrantClient(
    host="localhost",
    port=6333
)

vector_store = QdrantVectorStore(
    client=client,
    collection_name=COLLECTION_NAME
)

storage_context = StorageContext.from_defaults(
    vector_store=vector_store
)

print("Creating index...")

index = VectorStoreIndex.from_documents(
    documents,
    transformations=[splitter],
    embed_model=embed_model,
    storage_context=storage_context,
    show_progress=True
)

print("Done.")
print(f"Collection: {COLLECTION_NAME}")
