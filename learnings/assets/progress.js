/* paxman-teach — progress capture.
 *
 * Aggregates widget telemetry ({type:"round"} / {"retrieval"} /
 * {"exercise_complete"}) pushed by span-picker.js & answer-check.js onto
 * window.PaxmanTeach.telemetry, then POSTs a schema-1 payload to
 * /api/progress (served by learnings/serve.py, which persists it under
 * learnings/progress/ as JSON).
 *
 * Degrades gracefully on a plain static server: pending payloads are kept
 * in localStorage, retried on next visit, and can be exported manually via
 * the status chip.
 *
 * Page wiring:
 *   <script src="../assets/span-picker.js"></script>
 *   <script src="../assets/answer-check.js"></script>
 *   <script src="../assets/progress.js"></script>
 *   <script>
 *     PaxmanTeach.progress.attach({ lesson: "0002-views-and-offsets" });
 *     ...widget init...
 *   </script>
 */
(function () {
  "use strict";

  var NS = (window.PaxmanTeach = window.PaxmanTeach || {});
  NS.telemetry = NS.telemetry || [];

  var PENDING_KEY = "paxmanProgressPending";
  var DEBOUNCE_MS = 900;

  var lessonId = null;
  var debounceTimer = null;
  var chip = null;
  var chipState = "";

  /* ---------- aggregation ---------- */

  function aggregate() {
    var rounds = {};          // last occurrence wins across replays
    var retrieval = {};       // question index -> last grading
    var complete = null;
    NS.telemetry.forEach(function (ev) {
      if (ev.type === "round") {
        rounds[ev.round] = {
          round: ev.round,
          caption: ev.caption,
          targets: ev.targets,
          attempts: ev.attempts,
          miss_picks: ev.miss_picks,
          first_try: ev.first_try,
          declared_empty: ev.declared_empty,
        };
      } else if (ev.type === "retrieval") {
        retrieval[ev.q] = {
          q: ev.q,
          accepted: ev.accepted,
          given: ev.given,
          ok: ev.ok,
        };
      } else if (ev.type === "exercise_complete") {
        complete = {
          total_attempts: ev.total_attempts,
          replays: ev.replays,
          rounds_total: ev.rounds_total,
        };
      }
    });
    return {
      schema: 1,
      lesson: lessonId || "unknown",
      captured_at_utc: new Date().toISOString(),
      rounds: Object.keys(rounds).sort(function (a, b) { return a - b; })
        .map(function (k) { return rounds[k]; }),
      retrieval: Object.keys(retrieval).sort(function (a, b) { return a - b; })
        .map(function (k) { return retrieval[k]; }),
      exercise_complete: complete,
    };
  }

  function hasSignal(payload) {
    return payload.rounds.length > 0 || payload.retrieval.length > 0;
  }

  /* ---------- transport ---------- */

  function setChip(state, detail) {
    chipState = state;
    if (!chip) return;
    var label = {
      idle: "capture: standby",
      sending: "capture: saving…",
      saved: "capture: saved ✓",
      local: "capture: stored locally",
      error: "capture: export needed",
    }[state] || state;
    chip.textContent = detail ? label + " — " + detail : label;
    chip.className = "pt-chip pt-" + state;
  }

  function send(payload, isFinal) {
    if (!hasSignal(payload)) return;
    setChip("sending");
    fetch("/api/progress", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(payload),
      keepalive: true,
    }).then(function (resp) {
      if (!resp.ok) throw new Error("HTTP " + resp.status);
      clearPending();                 // earlier offline stashes shipped fine; server dedupes by timestamp
      setChip("saved");
    }).catch(function () {
      stashPending(payload);
      if (chipState !== "local") setChip(isFinal ? "error" : "local");
    });
  }

  function readPending() {
    try { return JSON.parse(localStorage.getItem(PENDING_KEY) || "[]"); }
    catch (e) { return []; }
  }

  function stashPending(payload) {
    var arr = readPending();
    arr.push({ payload: payload, queued_at_utc: new Date().toISOString() });
    try { localStorage.setItem(PENDING_KEY, JSON.stringify(arr.slice(-20))); } catch (e) {}
  }

  function clearPending() {
    try { localStorage.removeItem(PENDING_KEY); } catch (e) {}
  }

  function retryPendingOnAttach() {
    var arr = readPending();
    if (!arr.length) return;
    arr.forEach(function (item) {
      fetch("/api/progress", {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify(item.payload),
        keepalive: true,
      }).catch(function () {});
    });
    clearPending();
    setChip("saved", "offline items uploaded");
  }

  function flush(final) {
    var payload = aggregate();
    if (final && !hasSignal(payload)) return;
    send(payload, final);
  }

  function scheduleFlush() {
    clearTimeout(debounceTimer);
    debounceTimer = setTimeout(function () { flush(false); }, DEBOUNCE_MS);
  }

  /* ---------- public API ---------- */

  NS.progress = {
    attach: function (opts) {
      lessonId = opts && opts.lesson ? String(opts.lesson) : null;

      chip = document.createElement("button");
      chip.type = "button";
      chip.title = "Exercise telemetry status. Click to download a manual copy.";
      chip.addEventListener("click", function () {
        var payload = aggregate();
        var blob = new Blob([JSON.stringify(payload, null, 2)], { type: "application/json" });
        var a = document.createElement("a");
        a.href = URL.createObjectURL(blob);
        a.download = "progress--" + payload.lesson + ".json";
        a.click();
        setTimeout(function () { URL.revokeObjectURL(a.href); }, 2000);
      });
      document.body.appendChild(chip);
      setChip("idle");

      // Drain anything recorded by widgets that initialized before attach().
      scheduleFlush();
      retryPendingOnAttach();

      // Wrap emit so future events trigger a debounced upload.
      NS.telemetry.push = function (ev) {
        Array.prototype.push.call(NS.telemetry, ev);
        scheduleFlush();
      };

      window.addEventListener("pagehide", function () { flush(true); });
    },
  };
})();
