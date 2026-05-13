from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.prompts import PromptTemplate
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.llms.ollama import Ollama
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

llm = Ollama(
    model="qwen2.5:3b",
    request_timeout=600.0
)

index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store,
    embed_model=embed_model,
    storage_context=storage_context
)

qa_prompt = PromptTemplate(
    """
You are an internal Unix/Linux runbook assistant.

Use ONLY the context below.
Do not use outside knowledge.
Do not invent commands.
If the context does not contain the answer, say:
"I could not find this in the indexed wiki documents."

Return the answer as:
1. Short summary
2. Step-by-step commands
3. Source files used

Context:
---------------------
{context_str}
---------------------

Question:
{query_str}

Answer:
"""
)

query_engine = index.as_query_engine(
    llm=llm,
    similarity_top_k=4,
    text_qa_template=qa_prompt,
    response_mode="compact"
)

print("\nAIWiki RAG Chat")
print("Type 'exit' to quit\n")

while True:
    query = input("Question: ")

    if query.lower() == "exit":
        break

    try:
        response = query_engine.query(query)

        print("\nAnswer:\n")
        print(response)

        print("\nSources:")
        for source_node in response.source_nodes:
            print("-", source_node.metadata.get("file_path"), "score:", round(source_node.score, 4))

        print("\n" + "=" * 80 + "\n")

    except Exception as e:
        print("\nERROR:\n")
        print(str(e))
        print("\n" + "=" * 80 + "\n")
