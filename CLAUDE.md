# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Lore Master is a RAG-based tool for collaborative world-building (writers, RPG creators). Users upload documents into named collections and query them via LLM-generated responses. Entities (characters, creatures, locations, factions, items) accumulate RAG-generated contents per category; confirming a content auto-discards other pending contents in the same category.

## Monorepo Structure

```
loremaster/
├── backend/    # FastAPI + SQLModel + Qdrant + Ollama  →  see backend/CLAUDE.md
├── frontend/   # React 19 + TypeScript + Vite + React Bootstrap  →  see frontend/CLAUDE.md
└── docs/       # Extended documentation
```

Each subdirectory has its own `CLAUDE.md` with full commands, architecture details, and design decisions.

## High-Level Architecture

**Backend** exposes a REST API (`/api/v1/`) consumed by the frontend. All routes are under collections as the top-level resource: `collections → documents | entities → drafts`.

**Data pipeline:** document upload → text extraction (PDF/TXT) → chunking → embedding (`sentence-transformers`) → Qdrant. Query time: user prompt → Qdrant similarity search → prompt + context → Ollama (`llama3.2:latest`) → response.

**Persistence:** SQLite locally, PostgreSQL via Docker. All domain models use soft-delete (`is_deleted` + `deleted_at`).

**UI language:** All user-facing error messages are in Spanish (`frontend/src/utils/errors.ts`).

## Local Development

Start infrastructure first, then each service in its own terminal:

```bash
# Step 1 — infrastructure (Qdrant + PostgreSQL + Redis)
cd backend && docker-compose up -d

# Step 2 — backend (from backend/, virtualenv active)
make install-dev
make run      # http://localhost:8000  — docs at /docs

# Step 3 — frontend (from frontend/)
npm install
npm run dev   # http://localhost:5173  — proxies /api/* → http://localhost:8000
```

Copy `backend/.env.example` to `backend/.env` before starting. See `backend/CLAUDE.md` for env variables and `backend/docker-compose.yml` for service ports.