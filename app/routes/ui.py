from fastapi import APIRouter
from fastapi.responses import HTMLResponse

from app.config import (
    APP_FULL_NAME,
    APP_NAME,
    COLLECTION_NAME,
    DATASET_NAME,
    FINAL_TOP_K,
    LLM_MODEL,
    RETRIEVAL_TOP_K,
)


router = APIRouter()


@router.get("/ui", response_class=HTMLResponse)
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
        h1 {{ margin-top: 0; color: #1f2937; font-size: 40px; }}
        .subtitle {{ font-size: 18px; color: #374151; margin-top: -14px; margin-bottom: 20px; }}
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
            width: 100%; height: 95px; font-size: 16px; padding: 12px;
            border-radius: 8px; border: 1px solid #ccc; box-sizing: border-box;
        }}
        button {{
            margin-top: 12px; padding: 12px 22px; font-size: 16px;
            border: none; border-radius: 8px; background: #2563eb; color: white; cursor: pointer;
        }}
        button:disabled {{ background: #9ca3af; }}
        .answer {{
            margin-top: 25px; padding: 18px; background: #f9fafb;
            border-left: 4px solid #2563eb; white-space: pre-wrap;
            border-radius: 8px; line-height: 1.45;
        }}
        .sources {{ margin-top: 20px; font-size: 14px; color: #374151; }}
        .source-item {{
            background: #eef2ff; padding: 8px; margin-top: 6px;
            border-radius: 6px; word-break: break-all;
        }}
        .examples {{ margin-top: 20px; color: #4b5563; }}
        .example {{ cursor: pointer; color: #2563eb; margin-bottom: 8px; }}
        .footer {{
            margin-top: 30px; font-size: 13px; color: #6b7280;
            border-top: 1px solid #e5e7eb; padding-top: 14px;
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
            Model: <b>{LLM_MODEL}</b> | Collection: <b>{COLLECTION_NAME}</b><br>
            Retrieval: <b>Top {RETRIEVAL_TOP_K} retrieved, Top {FINAL_TOP_K} synthesized, compressed context</b><br>
            OpenAI-compatible endpoint: <b>/v1</b>
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
            <div class="example" onclick="setQuestion('Tell me about Flexera agent installation')">Tell me about Flexera agent installation</div>
        </div>

        <div id="output"></div>

        <div class="footer">
            PEKA POC stack: FastAPI, Qdrant, Ollama, local embeddings, enterprise knowledge retrieval, and Open WebUI-compatible API.
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
