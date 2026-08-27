# Progress captures

Learner exercise telemetry lands here automatically when the course is served
via `uv run python learnings/serve.py` (see repo root `../serve.py`) — one
JSON file per upload event, named `<lesson>--<UTC timestamp>.json`.

Schema (version 1): see the header comment in `../assets/progress.js`.
Short version: `schema`, `lesson`, `captured_at_utc`, `rounds[]`
(per-round attempts, miss picks, first-try flag), `retrieval[]`
(question gradings), `exercise_complete` totals. Replays append fresh
events; the teacher's `--digest` treats the latest capture per
round/question as current state.

These files are learning evidence, not source code — fine to commit.
No payload leaves localhost.
