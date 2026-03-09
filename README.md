<p align="center">
  <img src="docs/logo.png" width="200" alt="Nebius Test Logo"/>
</p>

# Repo Summarizer API (FastAPI)

[![CI](https://github.com/khab40/nebius-test/actions/workflows/ci.yml/badge.svg?branch=main)](https://github.com/Khab40/nebius-test/actions/workflows/ci.yml)
[![Release](https://github.com/khab40/nebius-test/actions/workflows/release.yml/badge.svg)](https://github.com/Khab40/nebius-test/actions/workflows/release.yml)
[![Docker API](https://img.shields.io/badge/GHCR-nebius--test--api-blue)](https://github.com/khab40/nebius-test/pkgs/container/nebius-test-api)
[![Docker UI](https://img.shields.io/badge/GHCR-nebius--test--ui-blue)](https://github.com/khab40/nebius-test/pkgs/container/nebius-test-ui)
[![Release version](https://img.shields.io/github/v/release/khab40/nebius-test)](https://github.com/khab40/nebius-test/releases)

![Python](https://img.shields.io/badge/python-3.10%2B-blue)
![FastAPI](https://img.shields.io/badge/FastAPI-0.100%2B-009688)
![Docker](https://img.shields.io/badge/docker-ready-2496ED)
![RAG](https://img.shields.io/badge/RAG-top--K%20chunks-orange)

API service that accepts a public GitHub repository URL and returns:
- a human-readable summary
- main technologies used
- brief project structure description

It downloads the repo as a ZIP, filters/chooses the most relevant files (README/docs/configs/tree + selected code),
fits them into the LLM context window, and calls an LLM to generate the summary.

### Docker Compose architecture

![Docker Compose architecture](docs/diagrams/readme-mermaid-01-d8bf1129.png)

<details>
<summary>Mermaid source (GitHub Web / VS Code)</summary>

![Diagram 1](docs/diagrams/readme-mermaid-01-d8bf1129.png)

```mermaid
flowchart LR
  U["User / Browser"] -->|HTTP :8501| S["Streamlit UI"]
  S -->|POST /summarize| A["FastAPI API :8000"]
  A -->|Download ZIP| G["GitHub Repo"]
  A -->|Embeddings| E["Embedding API"]
  A -->|Completion| L["LLM Provider"]

  subgraph DockerCompose
    S
    A
  end
```

</details>

### API + RAG flow

![API + RAG flow](docs/diagrams/readme-mermaid-02-9c8d8587.png)

<details>
<summary>Mermaid source (GitHub Web / VS Code)</summary>

![Diagram 2](docs/diagrams/readme-mermaid-02-9c8d8587.png)

```mermaid
sequenceDiagram
    autonumber
    participant U as User
    participant S as Streamlit UI
    participant A as FastAPI API
    participant G as GitHub
    participant R as RAG (chunk + retrieve)
    participant E as Embeddings (OpenAI)
    participant L as LLM (OpenAI/Nebius)

    U->>S: Enter repo URL + click Summarize
    S->>A: POST /summarize { github_url }
    A->>G: Download repo (ZIP)
    A->>A: Filter/score files (docs/config/entrypoints)
    A->>R: Chunk selected files

    alt LLM_PROVIDER = openai
        R->>E: Embed chunks + queries
        E-->>R: Vectors
        R-->>A: Top-K relevant chunks
    else LLM_PROVIDER = nebius
        R-->>A: Keyword-based Top-K chunks
    end

    A->>L: Prompt (tree + facts + Top-K chunks)
    L-->>A: JSON summary
    A-->>S: { summary, technologies, structure, evidence, confidence }
```

</details>

## Screenshots

Example embedding:

![UI Home](docs/screenshots/ui-home.png)
![UI Result](docs/screenshots/ui-result.png)

## Requirements
- Python 3.10+

## LLM providers
Supports **OpenAI by default**, and **Nebius Token Factory** optionally.

### OpenAI (default)
Env vars:
- `OPENAI_API_KEY` (required)
- `OPENAI_MODEL` (optional, default: `gpt-4o-mini`)
- `OPENAI_EMBEDDING_MODEL` (optional, default: `text-embedding-3-small`)
  Note: `OPENAI_EMBEDDING_MODEL` controls the embeddings model used for RAG retrieval when `LLM_PROVIDER=openai` (default: `text-embedding-3-small`).
- `OPENAI_BASE_URL` (optional, default: `https://api.openai.com/v1/`)
- `LLM_PROVIDER` (optional, default: `openai`)

### Nebius Token Factory (optional)
Env vars:
- `NEBIUS_API_KEY` (required)
- `NEBIUS_MODEL` (optional, default: `meta-llama/Meta-Llama-3.1-8B-Instruct-fast`)
- `NEBIUS_BASE_URL` (optional, default: `https://api.tokenfactory.nebius.com/v1/`)
- `LLM_PROVIDER=nebius`

## LangSmith Monitoring & Tracing

This application is integrated with **LangSmith** for comprehensive LLM monitoring, debugging, and performance analysis.

### Features
- **Real-time Tracing**: Complete execution flow tracking for all LLM calls
- **Performance Metrics**: Latency, token usage, and cost monitoring
- **Error Tracking**: Detailed error analysis and debugging information
- **Dataset Management**: Create evaluation datasets from production traces
- **Model Comparison**: Compare performance across different models and providers

### Setup
The integration is automatically enabled when the following environment variables are set:

```bash
# LangSmith Configuration
LANGCHAIN_API_KEY="lsv2_pt_..."  # Your LangSmith API key
LANGCHAIN_TRACING_V2=true       # Enable tracing
LANGCHAIN_PROJECT="nebius-test"  # Project name for organization
```

### Accessing LangSmith Dashboard

1. Visit [LangSmith Dashboard](https://smith.langchain.com)
2. Select the "nebius-test" project from the dropdown
3. View traces, performance metrics, and monitoring data

### What You'll See

- **Traces**: Complete request/response flows with input prompts and LLM outputs
- **Token Usage**: Input/output token counts and cost estimates
- **Latency Metrics**: Response times for each LLM call
- **Error Analysis**: Failed requests with detailed error information
- **Model Performance**: Success rates and quality metrics

### Benefits

- **Debug Issues**: Trace through complex LLM interactions
- **Optimize Performance**: Identify slow or costly operations
- **Monitor Quality**: Track response quality and consistency
- **Cost Management**: Monitor and control LLM usage costs
- **Continuous Improvement**: Use traces to create evaluation datasets

The LangSmith integration provides enterprise-grade observability for your LLM-powered application, helping you maintain high performance and reliability.

## Install (local dev, no Docker)
```bash
python -m venv .venv
source .venv/bin/activate
pip install -r app/requirements.txt
```

## Run locally (OpenAI)
```bash
export LLM_PROVIDER=openai
export OPENAI_API_KEY="YOUR_OPENAI_KEY"
# Optional:
export OPENAI_MODEL="gpt-4o-mini"
export OPENAI_EMBEDDING_MODEL="text-embedding-3-small"

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Run locally (Nebius)
```bash
export LLM_PROVIDER=nebius
export NEBIUS_API_KEY="YOUR_NEBIUS_KEY"
# Optional:
export NEBIUS_MODEL="meta-llama/Meta-Llama-3.1-8B-Instruct-fast"

uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload
```

## Test
```bash
curl -X POST http://localhost:8000/summarize   -H "Content-Type: application/json"   -d '{"github_url": "https://github.com/psf/requests"}'
```

## Docker (optional)
```bash
# OpenAI:
export OPENAI_API_KEY="YOUR_OPENAI_KEY"
docker compose up --build

# Or build the API image directly:
docker build -f app/Dockerfile -t repo-summarizer-api:local .
```

Note: docker-compose includes an API healthcheck using `GET /health` and Streamlit waits for the API to become healthy.

## Error format
On error:
```json
{ "status": "error", "message": "..." }
```

## Repo→LLM strategy (what we send)
1) Directory tree (depth-limited; ignores node_modules, dist, venv, binaries, etc.)
2) README + key docs
3) Dependency/config files
4) Deterministic extraction: dependencies + entrypoints + detected endpoints
5) RAG-selected code chunks: chunk selected important files and retrieve top relevant chunks for: what it does / how to run / endpoints / structure / deps

## RAG retrieval (implementation)
To fit large repositories into the LLM context while keeping high signal, the service uses a lightweight RAG step:
- select important files (README/docs/configs + entrypoints/routes)
- chunk file contents with overlap
- retrieve top‑K relevant chunks for fixed questions (what it does / how to run / endpoints / structure / deps)
- OpenAI provider uses semantic retrieval via embeddings; Nebius falls back to keyword retrieval

The selected snippets (with evidence file names) are combined with a depth‑limited directory tree and deterministic facts before calling the LLM.

## Tests (pytest)

### Install (includes test deps)

```bash
pip install -r app/requirements.txt
```

### Run

```bash
pytest -q
```

### Create the first unit tests

This repo uses only local/mocked tests (no real calls to GitHub/OpenAI/Nebius).


## Answers on submission questions
Q: Which model you chose and why?
A: I chose gpt-4o-mini for Open AI and meta-llama/Meta-Llama-3.1-8B-Instruct-fast for Nebius because of the wish to keep balance between quality, speed and cost.

Q: Your approach to handling repository contents
A: Exclude binaries/build artifacts/generated data; include directory tree + docs + dependency/config files; extract endpoints/entrypoints deterministically; then use RAG-selected top-K chunks (chunk important files and retrieve the most relevant snippets) to fit the LLM context window while keeping high signal.


## Release images

Prebuilt container images are published to GitHub Container Registry (GHCR) for both API and UI.

You can pull them with:

```bash
docker pull ghcr.io/khab40/nebius-test-api:latest
docker pull ghcr.io/khab40/nebius-test-ui:latest
```

If you want docker‑compose to use the published images instead of building locally, set:

```bash
export REPO_SUMMARIZER_API_IMAGE=ghcr.io/khab40/nebius-test-api:latest
export REPO_SUMMARIZER_UI_IMAGE=ghcr.io/khab40/nebius-test-ui:latest
```


Then run:

```bash
docker compose up
```
