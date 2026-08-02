# Locked Architecture Decisions

## Frontend

- Next.js 15
- TypeScript
- Tailwind CSS
- shadcn/ui

## Backend

- FastAPI
- Vertical Slice Architecture

Domains:

- auth
- sessions
- skills
- artifacts
- knowledge
- providers

Shared:

- config
- database
- exceptions

## Authentication

- Supabase Auth
- Register
- Login
- Logout
- Password Reset

No guest mode.

## Database

- Supabase PostgreSQL
- pgvector

## Embeddings

- bge-m3 via Ollama

## Models

Primary:
- Ollama

Secondary:
- Claude SDK

Graceful Degradation:
- Ollama → Claude fallback

## Sessions

- Chat-based sessions
- Session sidebar
- Session history
- Artifacts attached to sessions

## Skills

- QA
- Research
- Ship30
- Artifact

## Router

Modes:
- Auto
- QA
- Research
- Ship30

Features:
- Auto Routing
- Manual Override
- Skill Chaining

## Knowledge Base

- Lenny Podcast transcript corpus
- Offline ingestion pipeline
- Runtime retrieval

## Citations

- Inline citations
- Episode name
- Timestamp
- Transcript excerpt
- Expandable source panel

## Artifacts

- Side panel
- Markdown rendering
- HTML rendering

Actions:
- Copy
- Download Markdown

Not Included:
- PDF Export
- Notion Export

## Infrastructure

- No Docker for MVP

## Architecture Rule

Do not redesign architecture.
Do not replace technology choices.
Build on top of these decisions.