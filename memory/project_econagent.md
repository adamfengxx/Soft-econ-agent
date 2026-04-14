---
name: EconAgent project state
description: Phase 1 backend implementation status and key architectural decisions
type: project
---

Phase 1 backend is complete and all imports verified clean.

**Why:** User wants to ship this project from architecture doc to working code.

**How to apply:** When continuing work, backend is runnable pending only .env setup. Next work is Phase 2 (Docker + React frontend).

Key architectural decisions made during Phase 1:
- Changed from Send API parallel dispatch to sequential Coordinator node (avoids LangGraph state-tracking bugs with parallel workers)
- SSE mechanism uses LangGraph `get_stream_writer()` + `stream_mode="custom"` (not asyncio.Queue or astream_events filtering)
- Model changed from `gpt-5` (nonexistent) to `gpt-4o` via `settings.MODEL_NAME`
- `task_results` uses `operator.or_` reducer for safe dict merging
- `AgentState` is `TypedDict(total=False)` to allow partial node updates
- venv is at project root `/Users/xinxin/Desktop/soft-econ-agent/.venv/`, not inside `backend/`
- All Python files under `backend/app/`; run uvicorn from `backend/` directory
