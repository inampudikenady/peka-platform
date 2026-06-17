import re

from llama_index.core import VectorStoreIndex, StorageContext
from llama_index.embeddings.huggingface import HuggingFaceEmbedding
from llama_index.llms.ollama import Ollama
from llama_index.vector_stores.qdrant import QdrantVectorStore
from qdrant_client import QdrantClient

from app.config import (
    COLLECTION_NAME,
    DATASET_NAME,
    EMBED_MODEL_NAME,
    FINAL_TOP_K,
    LLM_MODEL,
    LLM_TIMEOUT,
    MAX_COMPRESSED_LINES_PER_SOURCE,
    QDRANT_HOST,
    QDRANT_PORT,
    RETRIEVAL_TOP_K,
)
from app.prompts import QA_PROMPT


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


def source_filename(file_path: str) -> str:
    return file_path.split("/")[-1] if file_path else "unknown"


def normalize_text(text: str) -> str:
    return " ".join((text or "").split()).strip().lower()


def get_question_terms(question: str):
    stop_words = {
        "what", "when", "where", "why", "how", "do", "does", "did", "is", "are",
        "was", "were", "the", "a", "an", "to", "for", "of", "in", "on", "and",
        "or", "with", "about", "tell", "me", "show", "we", "have", "related",
        "procedure", "procedures", "documented", "please",
    }

    terms = re.findall(r"[a-zA-Z0-9_.:/+-]+", question.lower())
    return [t for t in terms if len(t) > 2 and t not in stop_words]


def deduplicate_nodes(nodes):
    seen = set()
    unique_nodes = []

    for node in nodes:
        clean_text = normalize_text(node.text)

        if not clean_text:
            continue

        fingerprint = clean_text[:500]

        if fingerprint in seen:
            continue

        seen.add(fingerprint)
        unique_nodes.append(node)

    return unique_nodes


def compress_node_text(question: str, text: str, max_lines: int = MAX_COMPRESSED_LINES_PER_SOURCE):
    """
    Block-aware context compressor.

    Keeps matching operational lines plus nearby lines so commands and steps do not
    get disconnected from their surrounding procedure.
    """
    if not text:
        return ""

    question_terms = get_question_terms(question)

    operational_terms = [
        "install", "installation", "setup", "configure", "configuration",
        "verify", "validate", "validation", "check", "status", "service",
        "systemctl", "lssrc", "start", "stop", "restart",
        "error", "issue", "risk", "warning", "failed", "failure",
        "prerequisite", "requirement", "step", "run", "command",
        "copy", "download", "extract", "unzip", "permission",
        "linux", "aix", "rhel", "oracle", "sap", "vmware",
        "agent", "inventory", "flexera", "flexnet", "ndtrack", "mgssetup",
    ]

    raw_lines = text.splitlines()
    selected_indexes = set()

    for idx, raw_line in enumerate(raw_lines):
        line = raw_line.strip()

        if not line or len(line) <= 2:
            continue

        line_l = line.lower()
        score = 0

        for term in question_terms:
            if term in line_l:
                score += 3

        for term in operational_terms:
            if term in line_l:
                score += 1

        if line.endswith(":"):
            score += 2

        if line.startswith(("-", "*", "1.", "2.", "3.", "4.", "5.")):
            score += 1

        if any(x in line for x in ["sudo ", "systemctl", "./", "lssrc", "rpm ", "unzip ", "chmod "]):
            score += 3

        if score > 0:
            selected_indexes.add(idx)
            if idx - 1 >= 0:
                selected_indexes.add(idx - 1)
            if idx + 1 < len(raw_lines):
                selected_indexes.add(idx + 1)
            if idx + 2 < len(raw_lines):
                selected_indexes.add(idx + 2)

    if not selected_indexes:
        return "\n".join(raw_lines[:max_lines]).strip()

    final_lines = []
    seen = set()

    for idx in sorted(selected_indexes):
        line = raw_lines[idx].strip()

        if not line:
            continue

        normalized = normalize_text(line)

        if normalized in seen:
            continue

        seen.add(normalized)
        final_lines.append(line)

        if len(final_lines) >= max_lines:
            break

    return "\n".join(final_lines).strip()


def rerank_nodes(question: str, nodes, final_k: int = FINAL_TOP_K):
    q = question.lower()

    boost_terms = []
    penalty_terms = []

    if any(x in q for x in ["rhel", "redhat", "red hat", "linux"]):
        boost_terms += ["rhel", "redhat", "red hat", "linux"]
        penalty_terms += ["hpux", "hp-ux", "aix", "vios", "hmc"]

    if any(x in q for x in ["filesystem", "file system", "fs", "mount"]):
        boost_terms += [
            "filesystem", "file system", "fs", "lvm",
            "lvextend", "resize2fs", "xfs_growfs",
        ]

    if "sap" in q:
        boost_terms += ["sap"]

    if any(x in q for x in ["vmware", "vcenter", "powercli", "vsphere"]):
        boost_terms += ["vmware", "vcenter", "powercli", "vsphere"]

    if any(x in q for x in ["oracle", "rac", "database", "db"]):
        boost_terms += ["oracle", "rac", "db", "database"]

    if any(x in q for x in ["incident", "ticket", "change", "cmdb", "servicenow"]):
        boost_terms += ["incident", "ticket", "change", "cmdb", "servicenow"]

    if any(x in q for x in ["flexera", "flexnet", "agent", "inventory"]):
        boost_terms += ["flexera", "flexnet", "agent", "inventory", "mgssetup", "ndtrack"]

    if any(x in q for x in ["install", "installation", "setup", "configure"]):
        boost_terms += ["install", "installation", "setup", "configure", "service", "systemctl"]

    if any(x in q for x in ["validate", "validation", "verify", "check", "status"]):
        boost_terms += ["validate", "verify", "check", "status", "systemctl", "lssrc"]

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
                score += 0.025

        for term in penalty_terms:
            if term in filename:
                score -= 0.15
            if term in text:
                score -= 0.03

        scored.append((score, node))

    scored.sort(key=lambda x: x[0], reverse=True)

    ranked_nodes = [node for score, node in scored]
    ranked_nodes = deduplicate_nodes(ranked_nodes)

    return ranked_nodes[:final_k]


def build_context(question: str, nodes) -> str:
    context_blocks = []

    for idx, node in enumerate(nodes, start=1):
        file_path = node.metadata.get("file_path", "") or "unknown"
        file_name = source_filename(file_path)
        compressed_text = compress_node_text(question, node.text)

        context_blocks.append(
            f"""
Source {idx}
File Name: {file_name}
File Path: {file_path}

Relevant Content:
{compressed_text}
""".strip()
        )

    return "\n\n---------------------\n\n".join(context_blocks)

def run_peka_question(question: str, skip_retrieval: bool = False):
    if skip_retrieval:
        selected_nodes = []
        context = ""
    else:
        raw_nodes = retriever.retrieve(question)

        selected_nodes = rerank_nodes(
            question,
            raw_nodes,
            final_k=FINAL_TOP_K,
        )

        context = build_context(question, selected_nodes)

    prompt = QA_PROMPT.format(
        dataset_name=DATASET_NAME,
        context_str=context,
        query_str=question,
    )

    response = llm.complete(prompt)

    sources = []
    seen_paths = set()

    for node in selected_nodes:
        path = node.metadata.get("file_path")

        if path in seen_paths:
            continue

        seen_paths.add(path)

        sources.append(
            {
                "file_path": path,
                "file_name": source_filename(path),
                "original_vector_score": node.score,
            }
        )

    return str(response).strip(), sources