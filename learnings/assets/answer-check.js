/* paxman-teach — typed retrieval-answer checker with instant feedback.
 *
 * Usage: <label>Your answer: <input data-accept="end|the end"> </label>
 * Pressing Enter inside the input grades it (trimmed, case-insensitive).
 * Add class "q-block" wrappers around question HTML for shared styling.
 *
 * Telemetry: each grading pushes {type:"retrieval", q, accepted, given, ok}
 * onto PaxmanTeach.telemetry (repeat gradings of one question replace their
 * predecessor when progress.js aggregates).
 */
(function () {
  "use strict";

  var NS = (window.PaxmanTeach = window.PaxmanTeach || {});
  NS.telemetry = NS.telemetry || [];
  NS._qCounter = 0;

  function qIndex(input) {
    if (!input.dataset.qIdx) {
      input.dataset.qIdx = String(NS._qCounter++);
    }
    return Number(input.dataset.qIdx);
  }

  function grade(input) {
    var accepted = input.dataset.accept.split("|").map(function (s) {
      return s.trim().toLowerCase();
    });
    var given = input.value.trim().toLowerCase();
    var block = input.closest(".q-block") || input.parentElement;
    var feedback = block.querySelector(".q-feedback");
    if (!feedback) {
      feedback = document.createElement("div");
      feedback.className = "q-feedback";
      block.appendChild(feedback);
    }
    var ok = accepted.indexOf(given) !== -1;
    if (given !== "") {
      NS.telemetry.push({
        type: "retrieval",
        q: qIndex(input),
        accepted: accepted,
        given: given,
        ok: ok,
      });
    }
    if (ok) {
      input.classList.remove("q-bad");
      input.classList.add("q-ok");
      feedback.textContent = input.dataset.success || "\u2713 Correct.";
      feedback.className = "q-feedback q-fb-ok";
    } else if (given === "") {
      input.classList.remove("q-ok", "q-bad");
      feedback.textContent = "\u00a0";
    } else {
      input.classList.remove("q-ok");
      input.classList.add("q-bad");
      feedback.textContent = input.dataset.retryHint || "\u2717 Not quite — retrieve it before peeking back.";
      feedback.className = "q-feedback q-fb-bad";
    }
  }

  document.addEventListener("keydown", function (ev) {
    if (ev.key !== "Enter") return;
    var input = ev.target.closest("input[data-accept]");
    if (input) {
      ev.preventDefault();
      grade(input);
    }
  });

  document.addEventListener("click", function (ev) {
    var btn = ev.target.closest("[data-check-for]");
    if (!btn) return;
    var input = document.getElementById(btn.getAttribute("data-check-for"));
    if (input) grade(input);
  });
})();
