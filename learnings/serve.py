#!/usr/bin/env python3
"""Static server + progress capture for the paxman learnings workspace.

Serve (static files AND a capture endpoint):
    uv run python learnings/serve.py            # http://127.0.0.1:8000
    uv run python learnings/serve.py --port 8123

Teacher digest of captured learner progress:
    uv run python learnings/serve.py --digest

Capture API: POST /api/progress with the schema-1 JSON payload built by
learnings/assets/progress.js. Each accepted payload is persisted verbatim as
learnings/progress/<lesson>--<UTC-timestamp>.json; the digest aggregates those
files per lesson (latest capture per round/question wins, so replays simply
overwrite earlier entries).
"""

from __future__ import annotations

import argparse
import json
import re
import sys
import time
from datetime import datetime, timezone
from http.server import SimpleHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

ROOT = Path(__file__).resolve().parent
PROGRESS_DIR = ROOT / "progress"
MAX_BODY = 64 * 1024
LESSON_RE = re.compile(r"[^a-z0-9-]")


class CaptureHandler(SimpleHTTPRequestHandler):
    def __init__(self, *args, **kwargs) -> None:
        super().__init__(*args, directory=str(ROOT), **kwargs)

    def _json(self, status: int, body: dict) -> None:
        raw = json.dumps(body).encode()
        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def do_POST(self) -> None:  # noqa: N802 (http.server API)
        if self.path.rstrip("/") != "/api/progress":
            self.send_error(404)
            return
        try:
            length = int(self.headers.get("Content-Length") or 0)
        except ValueError:
            self._json(400, {"error": "bad Content-Length"})
            return
        if not 0 < length <= MAX_BODY:
            self._json(413, {"error": "payload too large or empty"})
            return
        try:
            payload = json.loads(self.rfile.read(length).decode("utf-8"))
        except (UnicodeDecodeError, json.JSONDecodeError):
            self._json(400, {"error": "invalid JSON"})
            return
        if (
            not isinstance(payload, dict)
            or payload.get("schema") != 1
            or not isinstance(payload.get("lesson"), str)
            or not payload["lesson"]
        ):
            self._json(422, {"error": "schema mismatch: need schema=1 and non-empty lesson"})
            return

        lesson = LESSON_RE.sub("", payload["lesson"].lower())[:80] or "unknown"
        PROGRESS_DIR.mkdir(exist_ok=True)
        stamp = time.strftime("%Y%m%dT%H%M%S", time.gmtime()) + f"-{int(time.time() * 1000) % 1000:03d}"
        out = PROGRESS_DIR / f"{lesson}--{stamp}.json"
        out.write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        self._json(201, {"saved": out.name})


def load_captures() -> dict[str, list[dict]]:
    captures: dict[str, list[dict]] = {}
    if not PROGRESS_DIR.is_dir():
        return captures
    for path in sorted(PROGRESS_DIR.glob("*.json")):
        try:
            payload = json.loads(path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError) as exc:
            print(f"  ! skipping unreadable {path.name}: {exc}", file=sys.stderr)
            continue
        captures.setdefault(payload.get("lesson", "unknown"), []).append(payload)
    return captures


def fmt_span(span: list[int]) -> str:
    try:
        s, e = int(span[0]), int(span[1])
    except (TypeError, ValueError, IndexError):
        return repr(span)
    return f"[{s},{e})"


def digest() -> None:
    captures = load_captures()
    if not captures:
        print(f"No captures yet in {PROGRESS_DIR}/")
        print("Learner activity appears here once lessons are played against serve.py.")
        return

    print(f"Progress from {PROGRESS_DIR}/\n")
    for lesson, payloads in sorted(captures.items()):
        latest_rounds: dict[int, dict] = {}
        latest_retrieval: dict[int, dict] = {}
        complete_totals: list[dict] = []
        first_seen = last_seen = ""
        for payload in payloads:
            stamp = payload.get("captured_at_utc", "")
            first_seen = min(x for x in (first_seen, stamp) if x) if first_seen else stamp
            last_seen = max(last_seen, stamp)
            for rnd in payload.get("rounds") or []:
                latest_rounds[rnd["round"]] = rnd          # replay overwrite = freshest state
            for q in payload.get("retrieval") or []:
                latest_retrieval[q["q"]] = q
            if payload.get("exercise_complete"):
                complete_totals.append(payload["exercise_complete"])

        rounds = [latest_rounds[k] for k in sorted(latest_rounds)]
        questions = [latest_retrieval[k] for k in sorted(latest_retrieval)]
        first_try = sum(1 for r in rounds if r.get("first_try"))
        misses: list[tuple[int, list]] = [
            (r["round"], r.get("miss_picks") or []) for r in rounds if r.get("miss_picks")
        ]

        print(f"── lesson {lesson}")
        print(f"   sessions seen: {len(payloads)}   window: {first_seen} … {last_seen}")
        if rounds:
            rate = first_try / len(rounds)
            verdict = "strong" if rate == 1 else "solid" if rate >= 0.75 else "needs calibration"
            print(
                f"   exercise: {first_try}/{len(rounds)} rounds first-try "
                f"({rate:.0%}) → {verdict}"
            )
        for r in rounds:
            flag = "✓" if r.get("first_try") else ("△" if r["attempts"] <= 2 else "✗")
            desc = f"round {r['round']} [{flag}] attempts={r['attempts']}"
            if r.get("declared_empty"):
                desc += " (empty-input round)"
            elif isinstance(r.get("targets"), list):
                desc += f" target={','.join(fmt_span(t) for t in r['targets']) or 'none'}"
            if r.get("miss_picks"):
                desc += f" missed={','.join(fmt_span(m) for m in r['miss_picks'])}"
            cap = (r.get("caption") or "").strip()
            if cap:
                desc += f"\n       · {cap[:100]}"
            print(f"     - {desc}")
        for rd, spans in misses:
            print(f"     ? calibration note: round {rd} wrong picks {spans}")
        if questions:
            ok = sum(1 for q in questions if q.get("ok"))
            wrong_q = [q for q in questions if not q.get("ok")]
            print(f"   retrieval: {ok}/{len(questions)} correct on final grading")
            for q in wrong_q:
                acc = "|".join(q.get("accepted") or [])
                print(f"     ✗ q{q['q']} gave {q.get('given')!r}, accepted {acc}")
        if complete_totals:
            t = complete_totals[-1]
            summary = f"   last complete run: {t.get('total_attempts')} clicks"
            if t.get("replays"):
                summary += f", {t['replays']} replays"
            print(summary)
        print()


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__.splitlines()[0])
    ap.add_argument("--port", type=int, default=8000, help="serve port (default 8000)")
    ap.add_argument("--digest", action="store_true", help="print learner progress and exit")
    args = ap.parse_args()

    if args.digest:
        digest()
        return

    server = ThreadingHTTPServer(("127.0.0.1", args.port), CaptureHandler)
    where = f"http://127.0.0.1:{args.port}"
    print(f"Serving learnings/ + capture endpoint at {where}  (Ctrl+C to stop)")
    print(f"Captures land in: {PROGRESS_DIR}/")
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        pass
    finally:
        server.server_close()


if __name__ == "__main__":
    main()
