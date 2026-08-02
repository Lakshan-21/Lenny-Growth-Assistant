\# Lenny Growth Assistant



An AI-powered knowledge workspace that enables users to query a curated knowledge base, generate research briefs, create content artifacts, and transform insights into Ship30-style content.



\## Features



\### Knowledge Retrieval

\- Semantic search across ingested knowledge sources

\- Citation-backed answers

\- Source attribution and traceability

\- Context-aware question answering



\### Research Brief Generation

\- AI-generated research briefs

\- Structured synthesis of retrieved information

\- Evidence-backed insights



\### Artifact Generation

\- Generate reusable content artifacts

\- Markdown and HTML rendering

\- Artifact management and retrieval



\### Ship30 Content Creation

Generate:

\- LinkedIn posts

\- X (Twitter) threads

\- Articles



\### Session Management

\- Persistent chat sessions

\- Conversation history

\- Workspace organization



\---



\## Architecture



\### Backend

Built with:



\- FastAPI

\- SQLAlchemy

\- Alembic

\- PostgreSQL

\- Anthropic API

\- Ollama

\- Vector embeddings

\- Pytest



Structure:



```text

backend/

├── app/

│   ├── config/

│   ├── database/

│   ├── domains/

│   ├── exceptions/

│   └── main.py

├── tests/

└── pyproject.toml

```



\### Frontend



Built with:



\- Next.js

\- TypeScript

\- React

\- Tailwind CSS

\- TanStack Query

\- shadcn/ui



Structure:



```text

frontend/

├── app/

├── components/

├── hooks/

├── lib/

└── types/

```



\---



\## Core Domains



\### Knowledge Domain

Responsible for:



\- Document ingestion

\- Chunking

\- Embedding generation

\- Retrieval



\### Skills Domain



Supported skills:



\- QA

\- Research

\- Artifact Generation

\- Ship30 Content Generation



\### Session Domain



Provides:



\- Session creation

\- Message storage

\- Conversation management



\---



\## Installation



\### Prerequisites



\- Python 3.11+

\- Node.js 20+

\- PostgreSQL

\- Ollama (optional)

\- Anthropic API Key



\---



\### Backend Setup



```bash

cd backend



python -m venv .venv



source .venv/bin/activate

\# Windows:

\# .venv\\Scripts\\activate



pip install -e .



alembic upgrade head



uvicorn app.main:app --reload

```



Backend runs on:



```text

http://localhost:8000

```



\---



\### Frontend Setup



```bash

cd frontend



npm install



npm run dev

```



Frontend runs on:



```text

http://localhost:3000

```



\---



\## Environment Variables



Backend example:



```env

DATABASE\_URL=

ANTHROPIC\_API\_KEY=

OLLAMA\_BASE\_URL=

```



Frontend example:



```env

NEXT\_PUBLIC\_API\_URL=http://localhost:8000

```



\---



\## Testing



Run backend tests:



```bash

pytest

```



Run specific tests:



```bash

pytest tests/

```



\---



\## Knowledge Corpus



The transcript corpus used during development is intentionally excluded from version control.



```text

transcripts/

```



Users should provide their own corpus for ingestion.



\---



\## API Capabilities



\### Sessions



\- Create session

\- Retrieve session

\- List sessions



\### QA



\- Ask questions

\- Retrieve cited answers



\### Research



\- Generate research briefs



\### Artifacts



\- Create artifacts

\- Retrieve artifacts



\### Ship30



\- Generate:

&#x20; - LinkedIn posts

&#x20; - X threads

&#x20; - Articles



\---



\## Tech Stack



\### Backend



\- FastAPI

\- SQLAlchemy

\- Alembic

\- PostgreSQL

\- Anthropic

\- Ollama

\- Pytest



\### Frontend



\- Next.js

\- React

\- TypeScript

\- Tailwind CSS

\- shadcn/ui

\- TanStack Query



\---



\## Project Status



Current Status: MVP Complete



Implemented:



\- Knowledge ingestion pipeline

\- Semantic retrieval

\- Citation-backed QA

\- Research generation

\- Artifact management

\- Ship30 content generation

\- Session management

\- Frontend workspace UI



Future Improvements:



\- Multi-user support

\- Authentication enhancements

\- Advanced filtering

\- Analytics dashboard

\- Improved artifact workflows



\---



\## License



This project was developed as a take-home assignment and portfolio project.

