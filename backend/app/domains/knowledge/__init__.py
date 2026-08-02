"""Knowledge domain: the Lenny Podcast transcript corpus — episodes,
transcript chunks, offline ingestion pipeline, runtime retrieval.

Internal domain only in MVP — no HTTP endpoints. Retrieval is reached
exclusively via in-process calls from `skills/qa/` and `skills/research/`
(see REPOSITORY_STRUCTURE.md's MVP-simplification notes).
"""
