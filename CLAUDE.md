# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A FastAPI-based skill recommendation system (Lite version) that uses JSON files for data storage and ChromaDB for vector embeddings. No database required.

## Project Structure

```
├── main.py                    # FastAPI app entry point
├── config/
│   ├── config.py              # Settings via pydantic-settings
│   └── .env                   # Environment variables (API keys)
├── script/
│   ├── data_store.py          # JSONDataStore, SkillStore
│   ├── vector_store.py        # ChromaDB + embedding
│   └── skill_agent.py         # Skill recommendation pipeline
├── API/
│   └── api_skills.py          # Skills CRUD + /recommend endpoint
├── data/
│   └── chromadb/              # ChromaDB persistence (gitignored)
└── skills.json                 # Skills data (created at runtime)
```

## Development Commands

```bash
# Install dependencies
pip install -r requirements.txt

# Run the server (data files created automatically on first run)
python main.py
```

The API is available at http://localhost:8000 with Swagger docs at http://localhost:8000/docs

## Architecture

```
main.py → FastAPI app with CORS
    │
    └── API/api_skills.py → SkillAgent → VectorStore + SkillStore
              │
              └── Anthropic (optional LLM reranking)
```

### Recommendation Pipeline

1. **Vector search** - ChromaDB cosine similarity search (top-k via `RERANK_TOP_K`)
2. **Metadata filtering** - category, difficulty_level filters applied post-search
3. **Claude reranking** - if `ANTHROPIC_API_KEY` is set, reorders candidates using LLM

### Singleton Pattern

All stores and agents use module-level singletons: `get_vector_store()`, `get_skill_store()`, `get_skill_agent()`. Settings use `@lru_cache()` via `get_settings()`.

### Configuration

Settings in `config/config.py` are environment-driven via pydantic-settings. Key variables in `.env`:
- `EMBEDDING_MODEL_NAME` - Default: `sentence-transformers/paraphrase-multilingual-MiniLM-L12-v2`
- `ANTHROPIC_API_KEY` - Optional; enables LLM reranking
- `CHROMA_PERSIST_DIR` - Default: `./data/chromadb`

### Embedding Model

Local model (`sentence-transformers`) is used by default. Models are cached at `F:/hf_cache` (configurable via `HF_HOME` environment variable).

### Data Flow for New Items

`POST /api/v1/skills/` → saves to JSON file + indexes in ChromaDB simultaneously. Restart not required.
