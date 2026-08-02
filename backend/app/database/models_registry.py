"""Imports every domain's `models.py` for side-effect registration on
`Base.metadata` — the single place Alembic autogenerate (migrations/env.py)
sources its table list from.

NOTE — structural addition, flagged per task instructions: REPOSITORY_STRUCTURE.md's
`database/` file listing (`__init__.py`, `base.py`, `session.py`, `migrations/`)
predates this task's explicit "support Alembic autogenerate" requirement and
does not list this file. It is intentionally NOT re-exported from
`database/__init__.py` (which stays minimal — just `Base`/`get_db`) to avoid
a circular import: `database/__init__.py` is executed before any domain
module in most import paths, so it must never import a domain.

Import order follows DATABASE_SCHEMA.md §7's migration dependency order for
readability; registration itself is order-independent. `skills/` and
`providers/` have no `models.py` — `RoutingDecision`/`ModelInvocation` are
deferred (log-only), per REPOSITORY_STRUCTURE.md's MVP simplification.

At runtime, most of these are already imported transitively via
`app.main`'s router chain; this module exists so migration tooling (which
never imports `app.main`) sees the same complete model set.
"""

from app.domains.auth import models as _auth_models  # noqa: F401  (Profile)
from app.domains.sessions import models as _sessions_models  # noqa: F401  (Session, Message)
from app.domains.knowledge import models as _knowledge_models  # noqa: F401  (Episode, TranscriptChunk, Citation)
from app.domains.artifacts import models as _artifacts_models  # noqa: F401  (Artifact, ResearchBrief)
