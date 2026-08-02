"""Skills domain: the four skills (QA, Research, Ship30, Artifact) plus the
Router (auto routing, manual override, skill chaining) that dispatches
between them. Routing decisions are logged, not persisted, in MVP — see
`skill_router.py` and REPOSITORY_STRUCTURE.md's MVP-simplification notes.
"""
