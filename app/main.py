import os
from typing import List

from dotenv import load_dotenv
from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.prompts import PromptTemplate
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient


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
FINAL_TOP_K = int(os.getenv("PEKA_FINAL_TOP_K", "2"))
LLM_TIMEOUT = float(os.getenv("PEKA_LLM_TIMEOUT", "1800"))

app = FastAPI(title=f"{APP_NAME} - {APP_FULL_NAME}")


class AskRequest(BaseModel):
    question: str


class AskResponse(BaseModel):
    question: str
    answer: str
    sources: List[dict]


print(f"Loading embedding model: {EMBED_MODEL_NAME}")
embed_model = HuggingFaceEmbedding(model_name=EMBED_MODEL_NAME)

print(f"Connecting to Qdrant: {QDRANT_HOST}:{QDRANT_PORT}, collection={COLLECTION_NAME}")
qdrant_client = QdrantClient(host=QDRANT_HOST, port=QDRANT_PORT)

vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=COLLECTION_NAME,
)

storage_context = StorageContext.from_defaults(vector_store=vector_store)

print(f"Connecting to Ollama model: {LLM_MODEL}")
llm = Ollama(
    model=LLM_MODEL,
    request_timeout=LLM_TIMEOUT,
    temperature=0,
)

index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store,
    embed_model=embed_model,
    storage_context=storage_context,
)

retriever = index.as_retriever(similarity_top_k=RETRIEVAL_TOP_K)

qa_prompt = PromptTemplate(
    """
You are PEKA, a private enterprise operational knowledge assistant.

The indexed knowledge base currently contains: {dataset_name}

Use ONLY the context below.
Do not use outside knowledge.
Do not invent commands, systems, incidents, or relationships.
If the context does not contain the answer, say:
"I could not find this in the indexed enterprise knowledge base."

Return ONLY:
1. Short answer
2. Essential commands or key points
3. Source filenames

Keep response under 200 words.

Context:
---------------------
{context_str}
---------------------

Question:
{query_str}

Answer:
"""
)


def rerank_nodes(question: str, nodes, final_k: int = FINAL_TOP_K):
    """Simple POC reranker.

    This combines vector score with lightweight keyword boosts/penalties.
    It is intentionally transparent and easy to replace later with proper
    hybrid search, metadata filters, or a reranker model.
    """
    q = question.lower()

    boost_terms = []
    penalty_terms = []

    if any(x in q for x in ["rhel", "redhat", "red hat", "linux"]):
        boost_terms += ["rhel", "redhat", "red hat", "linux"]
        penalty_terms += ["hpux", "hp-ux", "aix", "vios", "hmc"]

    if any(x in q for x in ["filesystem", "file system", "fs", "mount"]):
        boost_terms += ["filesystem", "file system", "fs", "lvm", "lvextend", "resize2fs", "xfs_growfs"]

    if "sap" in q:
        boost_terms += ["sap"]

    if any(x in q for x in ["vmware", "vcenter", "powercli", "vsphere"]):
        boost_terms += ["vmware", "vcenter", "powercli", "vsphere"]

    if any(x in q for x in ["oracle", "rac", "database", "db"]):
        boost_terms += ["oracle", "rac", "db", "database"]

    if any(x in q for x in ["incident", "ticket", "change", "cmdb", "servicenow"]):
        boost_terms += ["incident", "ticket", "change", "cmdb", "servicenow"]

    scored = []

    for node in nodes:
        file_path = node.metadata.get("file_path", "") or ""
        filename = file_path.split("/")[-1].lower()
        text = node.text.lower()

        score = float(node.score or 0)

        for term in boost_terms:
            if term in filename:
                score += 0.08
            if term in text:
                score += 0.02

        for term in penalty_terms:
            if term in filename:
                score -= 0.15
            if term in text:
                score -= 0.03

        scored.append((score, node))

    scored.sort(key=lambda x: x[0], reverse=True)
    return [node for score, node in scored[:final_k]]


def source_filename(file_path: str) -> str:
    return file_path.split("/")[-1] if file_path else "unknown"


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": f"{APP_NAME} - {APP_FULL_NAME}",
        "dataset": DATASET_NAME,
        "collection": COLLECTION_NAME,
        "model": LLM_MODEL,
        "embedding_model": EMBED_MODEL_NAME,
        "retrieval": f"top{RETRIEVAL_TOP_K}_rerank_to_top{FINAL_TOP_K}",
        "ui": "/ui",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/ask", response_model=AskResponse)
def ask(req: AskRequest):
    raw_nodes = retriever.retrieve(req.question)
    selected_nodes = rerank_nodes(req.question, raw_nodes, final_k=FINAL_TOP_K)

    context = "\n\n---\n\n".join(
        [
            f"Source: {node.metadata.get('file_path')}\n\n{node.text}"
            for node in selected_nodes
        ]
    )

    prompt = qa_prompt.format(
        dataset_name=DATASET_NAME,
        context_str=context,
        query_str=req.question,
    )

    response = llm.complete(prompt)

    sources = []
    for node in selected_nodes:
        path = node.metadata.get("file_path")
        sources.append({
            "file_path": path,
            "file_name": source_filename(path),
            "original_vector_score": node.score,
        })

    return {
        "question": req.question,
        "answer": str(response),
        "sources": sources,
    }


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return f"""
<!DOCTYPE html>
<html>
<head>
    <title>{APP_NAME} - {APP_FULL_NAME}</title>
    <style>
        body {{
            font-family: Arial, sans-serif;
            background: #f5f7fb;
            margin: 0;
            padding: 40px;
        }}
        .container {{
            max-width: 980px;
            margin: auto;
            background: white;
            padding: 30px;
            border-radius: 14px;
            box-shadow: 0 4px 18px rgba(0,0,0,0.08);
        }}
        h1 {{
            margin-top: 0;
            color: #1f2937;
            font-size: 40px;
        }}
        .subtitle {{
            font-size: 18px;
            color: #374151;
            margin-top: -14px;
            margin-bottom: 20px;
        }}
        .info-box {{
            background: #eef2ff;
            padding: 14px;
            border-radius: 8px;
            margin-top: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #2563eb;
            color: #1f2937;
            line-height: 1.45;
        }}
        textarea {{
            width: 100%;
            height: 95px;
            font-size: 16px;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #ccc;
            box-sizing: border-box;
        }}
        button {{
            margin-top: 12px;
            padding: 12px 22px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            background: #2563eb;
            color: white;
            cursor: pointer;
        }}
        button:disabled {{ background: #9ca3af; }}
        .answer {{
            margin-top: 25px;
            padding: 18px;
            background: #f9fafb;
            border-left: 4px solid #2563eb;
            white-space: pre-wrap;
            border-radius: 8px;
            line-height: 1.45;
        }}
        .sources {{
            margin-top: 20px;
            font-size: 14px;
            color: #374151;
        }}
        .source-item {{
            background: #eef2ff;
            padding: 8px;
            margin-top: 6px;
            border-radius: 6px;
            word-break: break-all;
        }}
        .examples {{ margin-top: 20px; color: #4b5563; }}
        .example {{ cursor: pointer; color: #2563eb; margin-bottom: 8px; }}
        .footer {{
            margin-top: 30px;
            font-size: 13px;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
            padding-top: 14px;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{APP_NAME}</h1>
        <div class="subtitle">{APP_FULL_NAME}</div>

        <div class="info-box">
            <b>Indexed Knowledge Sources</b><br><br>
            • {DATASET_NAME}<br>
            • Operational runbooks and procedures<br>
            • Infrastructure knowledge and troubleshooting notes<br>
            • Future integrations: CMDB, RVTools/vCenter, monitoring, and logs<br><br>
            Current environment: <b>POC</b><br>
            Model: <b>{LLM_MODEL}</b> | Collection: <b>{COLLECTION_NAME}</b>
        </div>

        <textarea id="question" placeholder="Ask enterprise infrastructure or operational questions..."></textarea>
        <br>
        <button id="askBtn" onclick="askQuestion()">Ask</button>

        <div class="examples">
            <b>Example questions:</b>
            <div class="example" onclick="setQuestion('What SAP failover procedures do we have?')">What SAP failover procedures do we have?</div>
            <div class="example" onclick="setQuestion('Show VMware related operational procedures.')">Show VMware related operational procedures.</div>
            <div class="example" onclick="setQuestion('What AIX migration procedures are documented?')">What AIX migration procedures are documented?</div>
            <div class="example" onclick="setQuestion('Show Oracle RAC migration related notes.')">Show Oracle RAC migration related notes.</div>
            <div class="example" onclick="setQuestion('How do we expand a filesystem in RHEL?')">How do we expand a filesystem in RHEL?</div>
        </div>

        <div id="output"></div>

        <div class="footer">
            PEKA POC stack: FastAPI, Qdrant, Ollama, local embeddings, and enterprise knowledge retrieval.
        </div>
    </div>

<script>
function setQuestion(q) {{
    document.getElementById("question").value = q;
}}

async function askQuestion() {{
    const question = document.getElementById("question").value;
    const output = document.getElementById("output");
    const btn = document.getElementById("askBtn");

    if (!question.trim()) {{
        alert("Enter a question first.");
        return;
    }}

    btn.disabled = true;
    btn.innerText = "Thinking...";
    output.innerHTML = "<div class='answer'>Processing... CPU-only POC responses may take 1-3 minutes.</div>";

    try {{
        const response = await fetch("/ask", {{
            method: "POST",
            headers: {{"Content-Type": "application/json"}},
            body: JSON.stringify({{question: question}})
        }});

        const data = await response.json();

        if (!response.ok) {{
            throw new Error(data.detail || "Request failed");
        }}

        let html = "<div class='answer'><b>Answer:</b>\\n\\n" + escapeHtml(data.answer) + "</div>";

        html += "<div class='sources'><b>Sources:</b>";
        data.sources.forEach(src => {{
            html += "<div class='source-item'><b>" + escapeHtml(src.file_name || "unknown") + "</b>" +
                    "<br>" + escapeHtml(src.file_path || "") +
                    "<br>Score: " + src.original_vector_score + "</div>";
        }});
        html += "</div>";

        output.innerHTML = html;

    }} catch (err) {{
        output.innerHTML = "<div class='answer'>Error: " + escapeHtml(err.toString()) + "</div>";
    }}

    btn.disabled = false;
    btn.innerText = "Ask";
}}

function escapeHtml(text) {{
    return String(text)
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}}
</script>
</body>
</html>
"""
