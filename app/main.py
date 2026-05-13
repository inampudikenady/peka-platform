from fastapi import FastAPI
from fastapi.responses import HTMLResponse
from pydantic import BaseModel

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.core.prompts import PromptTemplate
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.vector_stores.qdrant import QdrantVectorStore
from llama_index.llms.ollama import Ollama
from qdrant_client import QdrantClient


COLLECTION_NAME = "unixdocs"

app = FastAPI(title="CSI Global Services Operations Knowledge Assistant")


class AskRequest(BaseModel):
    question: str


print("Loading embedding model...")
embed_model = HuggingFaceEmbedding(
    model_name="BAAI/bge-base-en-v1.5"
)

print("Connecting to Qdrant...")
qdrant_client = QdrantClient(
    host="localhost",
    port=6333
)

vector_store = QdrantVectorStore(
    client=qdrant_client,
    collection_name=COLLECTION_NAME
)

storage_context = StorageContext.from_defaults(
    vector_store=vector_store
)

print("Connecting to Ollama...")
llm = Ollama(
    model="qwen2.5:3b",
    request_timeout=1800.0,
    temperature=0
)

index = VectorStoreIndex.from_vector_store(
    vector_store=vector_store,
    embed_model=embed_model,
    storage_context=storage_context
)

retriever = index.as_retriever(
    similarity_top_k=8
)

qa_prompt = PromptTemplate(
    """
You are an internal infrastructure operations knowledge assistant for CSI Global Services.

The indexed knowledge base currently contains operational DokuWiki documentation from the client Tenneco.

Use ONLY the context below.
Do not use outside knowledge.
Do not invent commands.
If the context does not contain the answer, say:
"I could not find this in the indexed Tenneco wiki documents."

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


def rerank_nodes(question: str, nodes, final_k: int = 2):
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

    if any(x in q for x in ["vmware", "vcenter", "powercli"]):
        boost_terms += ["vmware", "vcenter", "powercli"]

    if any(x in q for x in ["oracle", "rac", "database", "db"]):
        boost_terms += ["oracle", "rac", "db", "database"]

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


@app.get("/")
def root():
    return {
        "status": "ok",
        "service": "CSI Global Services Operations Knowledge Assistant",
        "client_dataset": "Tenneco DokuWiki",
        "collection": COLLECTION_NAME,
        "model": "qwen2.5:3b",
        "retrieval": "top8_rerank_to_top2",
        "ui": "/ui",
    }


@app.get("/health")
def health():
    return {"status": "healthy"}


@app.post("/ask")
def ask(req: AskRequest):
    raw_nodes = retriever.retrieve(req.question)
    selected_nodes = rerank_nodes(req.question, raw_nodes, final_k=2)

    context = "\n\n---\n\n".join(
        [
            f"Source: {node.metadata.get('file_path')}\n\n{node.text}"
            for node in selected_nodes
        ]
    )

    prompt = qa_prompt.format(
        context_str=context,
        query_str=req.question
    )

    response = llm.complete(prompt)

    sources = []
    for node in selected_nodes:
        sources.append({
            "file_path": node.metadata.get("file_path"),
            "original_vector_score": node.score,
        })

    return {
        "question": req.question,
        "answer": str(response),
        "sources": sources,
    }


@app.get("/ui", response_class=HTMLResponse)
def ui():
    return """
<!DOCTYPE html>
<html>
<head>
    <title>CSI Global Services - Operations Knowledge Assistant</title>
    <style>
        body {
            font-family: Arial, sans-serif;
            background: #f5f7fb;
            margin: 0;
            padding: 40px;
        }
        .container {
            max-width: 950px;
            margin: auto;
            background: white;
            padding: 30px;
            border-radius: 14px;
            box-shadow: 0 4px 18px rgba(0,0,0,0.08);
        }
        h1 {
            margin-top: 0;
            color: #1f2937;
            font-size: 36px;
        }
        .subtitle {
            font-size: 18px;
            color: #374151;
            margin-top: -12px;
            margin-bottom: 20px;
        }
        .info-box {
            background: #eef2ff;
            padding: 14px;
            border-radius: 8px;
            margin-top: 20px;
            margin-bottom: 20px;
            border-left: 4px solid #2563eb;
            color: #1f2937;
            line-height: 1.45;
        }
        textarea {
            width: 100%;
            height: 95px;
            font-size: 16px;
            padding: 12px;
            border-radius: 8px;
            border: 1px solid #ccc;
            box-sizing: border-box;
        }
        button {
            margin-top: 12px;
            padding: 12px 22px;
            font-size: 16px;
            border: none;
            border-radius: 8px;
            background: #2563eb;
            color: white;
            cursor: pointer;
        }
        button:disabled {
            background: #9ca3af;
        }
        .answer {
            margin-top: 25px;
            padding: 18px;
            background: #f9fafb;
            border-left: 4px solid #2563eb;
            white-space: pre-wrap;
            border-radius: 8px;
            line-height: 1.45;
        }
        .sources {
            margin-top: 20px;
            font-size: 14px;
            color: #374151;
        }
        .source-item {
            background: #eef2ff;
            padding: 8px;
            margin-top: 6px;
            border-radius: 6px;
            word-break: break-all;
        }
        .examples {
            margin-top: 20px;
            color: #4b5563;
        }
        .example {
            cursor: pointer;
            color: #2563eb;
            margin-bottom: 8px;
        }
        .footer {
            margin-top: 30px;
            font-size: 13px;
            color: #6b7280;
            border-top: 1px solid #e5e7eb;
            padding-top: 14px;
        }
    </style>
</head>
<body>
    <div class="container">
        <h1>CSI Global Services</h1>
        <div class="subtitle">Infrastructure Operations Knowledge Assistant</div>

        <div class="info-box">
            <b>Indexed Knowledge Sources</b><br><br>
            • Tenneco operational DokuWiki knowledge base<br>
            • Unix/Linux infrastructure procedures<br>
            • SAP operational documentation<br>
            • VMware and PowerCLI procedures<br>
            • AIX / VIOS operational runbooks<br>
            • Oracle RAC and migration procedures<br><br>
            Current environment: <b>POC</b>
        </div>

        <textarea id="question" placeholder="Ask infrastructure or operational questions..."></textarea>
        <br>
        <button id="askBtn" onclick="askQuestion()">Ask</button>

        <div class="examples">
            <b>Example questions:</b>

            <div class="example" onclick="setQuestion('What SAP failover procedures do we have for Tenneco?')">
                What SAP failover procedures do we have for Tenneco?
            </div>

            <div class="example" onclick="setQuestion('Show VMware related operational procedures.')">
                Show VMware related operational procedures.
            </div>

            <div class="example" onclick="setQuestion('What AIX migration procedures are documented?')">
                What AIX migration procedures are documented?
            </div>

            <div class="example" onclick="setQuestion('Show Oracle RAC migration related notes.')">
                Show Oracle RAC migration related notes.
            </div>

            <div class="example" onclick="setQuestion('How do we expand a filesystem in RHEL?')">
                How do we expand a filesystem in RHEL?
            </div>
        </div>

        <div id="output"></div>

        <div class="footer">
            Powered by CSI Global Services internal POC stack: FastAPI, Qdrant, Ollama, and indexed Tenneco DokuWiki data.
        </div>
    </div>

<script>
function setQuestion(q) {
    document.getElementById("question").value = q;
}

async function askQuestion() {
    const question = document.getElementById("question").value;
    const output = document.getElementById("output");
    const btn = document.getElementById("askBtn");

    if (!question.trim()) {
        alert("Enter a question first.");
        return;
    }

    btn.disabled = true;
    btn.innerText = "Thinking...";
    output.innerHTML = "<div class='answer'>Processing... this may take 1-3 minutes on the current CPU-only POC VM.</div>";

    try {
        const response = await fetch("/ask", {
            method: "POST",
            headers: {"Content-Type": "application/json"},
            body: JSON.stringify({question: question})
        });

        const data = await response.json();

        let html = "<div class='answer'><b>Answer:</b>\\n\\n" + escapeHtml(data.answer) + "</div>";

        html += "<div class='sources'><b>Sources:</b>";
        data.sources.forEach(src => {
            html += "<div class='source-item'>" + escapeHtml(src.file_path) +
                    "<br>Score: " + src.original_vector_score + "</div>";
        });
        html += "</div>";

        output.innerHTML = html;

    } catch (err) {
        output.innerHTML = "<div class='answer'>Error: " + escapeHtml(err.toString()) + "</div>";
    }

    btn.disabled = false;
    btn.innerText = "Ask";
}

function escapeHtml(text) {
    return text
        .replace(/&/g, "&amp;")
        .replace(/</g, "&lt;")
        .replace(/>/g, "&gt;");
}
</script>
</body>
</html>
"""
