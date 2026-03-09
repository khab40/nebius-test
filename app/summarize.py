import json
import re
import logging
from pathlib import Path
from typing import Dict, List

logger = logging.getLogger(__name__)

from .selection import build_tree, select_files, safe_read_text, detect_languages_and_tools
from .llm import chat_completion, LLMError

# RAG chunk retrieval (top-K relevant snippets). If app/rag.py is missing or disabled,
# summarization will fall back to the classic context builder.
try:
    from .rag import build_chunks, rag_select  # type: ignore
except Exception:  # pragma: no cover
    build_chunks = None
    rag_select = None


class SummarizationError(Exception):
    pass


JSON_BLOCK_RE = re.compile(r"\{.*\}", re.DOTALL)


def build_context(repo_root: Path, max_total_chars: int = 22000) -> str:
    parts: List[str] = []
    tree = build_tree(repo_root, max_depth=4)
    parts.append("=== DIRECTORY TREE (truncated) ===\n" + tree)

    selected = select_files(repo_root, max_files=28)

    def per_file_cap(p: Path) -> int:
        name = p.name.lower()
        if "readme" in name:
            return 6000
        if name in {"pyproject.toml", "requirements.txt", "package.json"}:
            return 3000
        if name.startswith(("openapi", "swagger")):
            return 4000
        return 2000

    total = sum(len(x) for x in parts)
    for sf in selected:
        rel = sf.path.relative_to(repo_root)
        text = safe_read_text(sf.path, max_chars=per_file_cap(sf.path))
        if not text.strip():
            continue
        chunk = f"\n\n=== FILE: {rel} ===\n{text}"
        if total + len(chunk) > max_total_chars:
            break
        parts.append(chunk)
        total += len(chunk)

    return "\n".join(parts)


async def build_rag_context(repo_root: Path, max_chars: int = 14000) -> tuple[str, List[str]]:
    """Build a compact context using RAG-selected chunks.

    Returns: (context_text, evidence_files)
    """
    # If rag.py is missing/disabled, fall back to classic context building.
    if build_chunks is None or rag_select is None:
        return "", []

    # If anything in retrieval fails (embeddings/network/etc.), do NOT crash the request.
    # Return an empty context so caller falls back to classic mode.
    try:
        chunks = build_chunks(repo_root)
        queries = [
            "What does this project do?",
            "How do you install, run, and test this project?",
            "What is the project structure (src/tests/docs)?",
            "What API endpoints exist and how are they implemented?",
            "What are the main dependencies and technologies?",
        ]
        picked = await rag_select(chunks, queries, top_k=10)

        evidence: List[str] = []
        parts: List[str] = []
        total = 0

        for c in picked:
            evidence.append(c.file)
            chunk = f"\n\n=== RAG CHUNK: {c.file} ===\n{c.text.strip()}"
            if total + len(chunk) > max_chars:
                break
            parts.append(chunk)
            total += len(chunk)

        # de-dupe evidence preserving order
        seen = set()
        evidence_unique: List[str] = []
        for e in evidence:
            if e not in seen:
                seen.add(e)
                evidence_unique.append(e)

        return "\n".join(parts).strip(), evidence_unique[:50]
    except Exception as e:
        logger.exception("RAG retrieval failed; falling back to classic context. Reason: %s", e)
        return "", []


def parse_llm_json(text: str) -> Dict:
    try:
        return json.loads(text)
    except Exception:
        pass

    m = JSON_BLOCK_RE.search(text)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass

    raise SummarizationError("LLM response was not valid JSON.")


async def summarize_repo(repo_root: Path) -> Dict:
    langs = detect_languages_and_tools(repo_root)

    # Prefer RAG-selected chunks to fit the context window while keeping high signal.
    tree_only = "=== DIRECTORY TREE (truncated) ===\n" + build_tree(repo_root, max_depth=4)
    rag_context, rag_evidence = await build_rag_context(repo_root)

    if rag_context.strip():
        context = tree_only + "\n" + rag_context
        evidence = rag_evidence
        retrieval_mode = "rag-10chunks"
    else:
        # Fallback to classic (non-RAG) context builder
        context = build_context(repo_root)
        evidence = []
        retrieval_mode = "classic"

    system = (
        "You are a senior software engineer. "
        "Given a GitHub repository snapshot, produce a concise, human-readable summary."
    )

    user = f"""Return ONLY valid JSON with keys: summary (string), technologies (array of strings), structure (string).

Rules:
- summary: what the project does (2-6 sentences).
- technologies: include programming languages + key frameworks/libraries you can infer from config files and code (dedupe).
- structure: describe the layout (where main code lives, tests, docs, configs) in 2-5 sentences.
- If unsure, be explicit (e.g., 'appears to', 'likely').

Repository signals:
Detected languages/tools (heuristic): {langs}

Repository content (directory tree + RAG-selected snippets; filtered & truncated):
- retrieval_mode: {retrieval_mode}
- evidence_files: {evidence}

{context}
""".strip()

    try:
        out = await chat_completion(
            messages=[
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            temperature=0.2,
            json_mode=True,
        )
    except LLMError as e:
        raise SummarizationError(str(e)) from e

    data = parse_llm_json(out)

    summary = str(data.get("summary", "")).strip()
    technologies = data.get("technologies", [])
    structure = str(data.get("structure", "")).strip()

    if not summary or not structure or not isinstance(technologies, list):
        raise SummarizationError("LLM JSON missing required fields.")

    technologies = [str(x).strip() for x in technologies if str(x).strip()]
    for l in langs:
        if l not in technologies:
            technologies.append(l)

    return {"summary": summary, "technologies": technologies, "structure": structure}
