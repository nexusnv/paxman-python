/* paxman-teach — span picker instrumented for progress capture.
 *
 * Usage:
 *   PaxmanTeach.spanPicker({
 *     mount: document.getElementById("exercise"),
 *     simulate: "SIUnit NameGrammar (case-folded lexicon)",
 *     rounds: [
 *       { text: "Add 5 kilogram", targets: [[6,14]], why: "…", },
 *       { text: "840 XYZ",        targets: [], why: "…", },   // empty => "no matches" path
 *     ],
 *   });
 *
 * Spans are half-open [start, end): the learner clicks the FIRST matched char,
 * then the LAST matched char; end becomes lastIndex + 1 automatically.
 *
 * Telemetry: every finished round pushes a "round" event to
 * PaxmanTeach.telemetry ({type:"round", round, caption, targets, attempts,
 * miss_picks, first_try, declared_empty}); "Play again" bumps replayCount and a
 * {type:"exercise_complete"} event carries totals. progress.js (if loaded)
 * drains the queue and ships it to the capture endpoint.
 */
(function () {
  "use strict";

  var NS = (window.PaxmanTeach = window.PaxmanTeach || {});
  NS.telemetry = NS.telemetry || [];
  function emit(ev) { NS.telemetry.push(ev); }

  function el(tag, cls, text) {
    var node = document.createElement(tag);
    if (cls) node.className = cls;
    if (text !== undefined) node.textContent = text;
    return node;
  }

  function describeMiss(userStart, userEnd, targets) {
    var t = targets[0];
    var hint;
    if (t && userStart === t[0] && Math.abs(userEnd - t[1]) === 1) {
      hint =
        "So close! The interval is half-open [start, end): END points one past " +
        "the last kept character.";
    } else if (t && Math.abs(userStart - t[0]) === 1) {
      hint = "Off by one at the START side of the span. Try again.";
    } else if (userEnd <= userStart) {
      hint = "Second click must land AFTER the first. Click the last matched character.";
    } else if (t && t[1] - t[0] === userEnd - userStart && userStart !== t[0]) {
      hint = "Right length, wrong place — where does that token actually begin?";
    } else {
      hint = "That span isn't one this grammar emits. Re-trace the input, then retry.";
    }
    return hint;
  }

  function buildRound(container, round, state, opts) {
    container.innerHTML = "";
    state.first = null;
    state.roundAttempts = 0;
    state.missPicks = [];

    var promptRow = el("div", "sp-caption");
    if (round.caption) promptRow.appendChild(el("span", "sp-grammar", round.caption));
    container.appendChild(promptRow);

    var grid = el("div", "sp-grid");
    var chars = Array.from(round.text);
    chars.forEach(function (ch, i) {
      var cellWrap = el("span", "sp-cellwrap");
      var btn = el("button", "sp-ch", ch === " " ? "\u2423" : ch);
      btn.type = "button";
      btn.setAttribute("aria-label", "character " + i + (ch === " " ? ", space" : ""));
      btn.dataset.i = String(i);
      cellWrap.appendChild(btn);
      cellWrap.appendChild(el("span", "sp-idx", String(i)));
      grid.appendChild(cellWrap);
    });
    container.appendChild(grid);

    var status = el("div", "sp-status", "\u00a0");
    container.appendChild(status);

    function setStatus(msg, cls) {
      status.textContent = msg;
      status.className = "sp-status" + (cls ? " " + cls : "");
    }
    setStatus(
      round.targets.length === 0
        ? "Click every character you believe belongs to a match — or declare there are none."
        : "Click the FIRST character of the match, then the LAST.",
      ""
    );

    function paint(range, cls) {
      for (var k = range[0]; k < range[1]; k++) {
        var b = grid.querySelector('[data-i="' + k + '"]');
        if (b) b.classList.add(cls);
      }
    }
    function clearTransient() {
      Array.prototype.forEach.call(grid.querySelectorAll(".sp-ch"), function (b) {
        b.classList.remove("sel-start", "miss");
      });
    }

    function finishRound(hit) {
      emit({
        type: "round",
        round: state.roundIndex,
        caption: round.caption || "",
        targets: round.targets,
        attempts: state.roundAttempts,
        miss_picks: state.missPicks,
        first_try: hit && state.roundAttempts === 1,
        declared_empty: round.targets.length === 0,
      });
    }

    function succeed(hitRange, note) {
      clearTransient();
      hitRange.forEach(function (r) { paint(r, "hit"); });
      grid.setAttribute("data-solved", "true");
      setStatus("\u2713 Correct." + (note ? " " + note : ""), "ok");
      if (!opts.silent) opts.onSolved();
      finishRound(true);
      setTimeout(function () { opts.advance(); }, 1600);
    }

    function attempt(a, b) {
      var s = Math.min(a, b), eInc = Math.max(a, b);
      var span = [s, eInc + 1];
      var matchIdx = round.targets.findIndex(function (t) {
        return t[0] === span[0] && t[1] === span[1];
      });
      opts.attempts++;
      state.roundAttempts++;
      if (matchIdx !== -1) {
        /* round.why is shown on correct rounds too (and always on empty
           rounds) — set it whenever there is something worth teaching. */
        succeed([span], round.why || null);
      } else if (round.targets.length === 0 && opts.emptyButtonUsed && !opts.triedEmptyThisRound) {
        /* fallthrough: wrong positive pick on an empty round */
        state.missPicks.push(span.slice());
        paint(span, "miss");
        opts.triedEmptyThisRound = false;
        setStatus(
          "\u2717 This grammar emits NOTHING for that region — clear your picks and press \u201cNo matches\u201d.",
          "bad"
        );
      } else {
        state.missPicks.push(span.slice());
        paint(span, "miss");
        setStatus("\u2717 " + describeMiss(s, span[1], round.targets), "bad");
        setTimeout(function () { clearTransient(); }, 900);
      }
      if (state.afterWrong) {
        state.afterWrong = false;
        return;
      }
    }

    grid.addEventListener("click", function (ev) {
      var btn = ev.target.closest(".sp-ch");
      if (!btn || grid.getAttribute("data-solved")) return;
      var i = Number(btn.dataset.i);
      if (state.first === null) {
        state.first = i;
        btn.classList.add("sel-start");
        setStatus("First char = " + i + ". Now click the LAST character.", "");
      } else {
        attempt(state.first, i);
        state.first = null;
      }
    });

    if (round.targets.length === 0) {
      var noneBtn = el("button", "sp-none-btn", "No matches here");
      noneBtn.type = "button";
      noneBtn.addEventListener("click", function () {
        if (grid.getAttribute("data-solved")) return;
        opts.attempts++;
        state.roundAttempts++;
        opts.triedEmptyThisRound = true;
        succeed([], round.why);
      });
      var row2 = el("div", "sp-actions");
      row2.appendChild(noneBtn);
      container.appendChild(row2);
    }
  }

  NS.spanPicker = function (config) {
    var mount = typeof config.mount === "string"
      ? document.querySelector(config.mount)
      : config.mount;
    var state = { roundIndex: 0, attempts: 0 };
    var outerState = { first: null, roundAttempts: 0, missPicks: [], replayCount: 0 };
    var headline = el("div", "sp-headline");
    mount.appendChild(headline);
    var box = el("div", "sp-box");
    mount.appendChild(box);
    var scoreLine = el("div", "sp-score");
    mount.appendChild(scoreLine);

    if (config.simulate) headline.textContent = "Simulated grammar: " + config.simulate;

    function advance() {
      state.roundIndex++;
      if (state.roundIndex < config.rounds.length) {
        render();
      } else {
        finish();
      }
    }

    function render() {
      var r = config.rounds[state.roundIndex];
      state.first = null;
      buildRound(box, r, outerState, {
        attempts: state,
        onSolved: function () {},
        advance: advance,
      });
      headline.textContent =
        "Simulated grammar: " + config.simulate +
        " — Round " + (state.roundIndex + 1) + " / " + config.rounds.length;
    }

    function finish() {
      emit({
        type: "exercise_complete",
        total_attempts: state.attempts,
        replays: outerState.replayCount,
        rounds_total: config.rounds.length,
      });
      box.innerHTML = "";
      headline.textContent = "";
      scoreLine.innerHTML = "";
      var done = el("div", "sp-done");
      done.appendChild(el("p", "", "Exercise complete — " + config.rounds.length + "/" +
        config.rounds.length + " rounds in " + state.attempts +
        " clicks. Fewer clicks = sharper recall."));
      var again = el("button", "sp-again-btn", "Play again");
      again.type = "button";
      again.addEventListener("click", function () {
        outerState.replayCount++;
        state.attempts = 0;
        state.roundIndex = 0;
        render();
      });
      done.appendChild(again);
      scoreLine.appendChild(done);
    }

    render();
  };
})();
