from llama_index.core import VectorStoreIndex
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.core import StorageContext
from qdrant_client import QdrantClient

COLLECTION_NAME = "unixdocs"

embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-base-en-v1.5"
)

client = QdrantClient(host="localhost", port=6333)

vector_store = QdrantVectorStore(
    client=client,
    collection_name=COLLECTION_NAME
)

storage_context = StorageContext.from_defaults(
    vector_store=vector_store
)

index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store,
    embed_model=embed_model,
    storage_context=storage_context
)

retriever = index.as_retriever(similarity_top_k=5)

query = "RHEL filesystem expansion using lvextend resize2fs xfs_growfs"

nodes = retriever.retrieve(query)

print(f"\nQuery: {query}\n")
print("=" * 80)

for i, node in enumerate(nodes, start=1):
    print(f"\nRESULT {i}")
    print("-" * 80)
    print("Score:", node.score)
    print("Source:", node.metadata.get("file_path"))
    print()
    print(node.text[:1200])
    print("=" * 80)
