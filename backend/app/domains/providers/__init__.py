"""Providers domain: the Model Gateway and its two provider implementations
(Ollama primary, Anthropic/Claude secondary) — graceful degradation per
CONTEXT.md. Provider invocation details are logged, not persisted, in MVP
(see gateway.py and REPOSITORY_STRUCTURE.md's MVP-simplification notes).
"""
