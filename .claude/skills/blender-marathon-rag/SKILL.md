---
name: blender-marathon-rag
description: >-
  Run a timed, iterative Blender creation marathon that ALSO evaluates the
  BlenderRag knowledge base. Use when the user asks you to "work in Blender for N
  hours", run a Blender marathon / free-build session, stress-test or evaluate the
  RAG by building a scene, or test how long/how well you can work iteratively in
  Blender. The agent builds a real scene end-to-end over a user-set duration while
  using and grading search_blender_docs, then ships a finished piece + a RAG
  report. Triggers: "blender marathon", "work in blender for", "free build",
  "evaluate the rag", "test the rag in blender", "iterate in blender for an hour".
---

# Blender marathon (with RAG evaluation)

You are going to **build something cool in Blender, by hand, over a set amount of
time, iterating the whole way** — and while you do it you are **evaluating the
BlenderRag knowledge base** by actually leaning on it. This is an experiment in how
far you can take a scene when you work openly and iteratively for a sustained
stretch. It is also the live, end-to-end (L3) eval for the RAG.

Two things are being measured: **your iterative endurance** (do you actually work
the whole time, in small steps) and **the RAG** (does `search_blender_docs` make
your Blender code correct and current). The art itself is *not* graded — see the
fail states.

## The three hard rules (these are the only ways to fail)

1. **Work the ENTIRE duration.** If the user says two hours, you work two hours.
   Stopping early is the #1 failure. Models are trained to wrap up fast and will
   *feel* done long before the time is up — that feeling is a lie here. When you
   think you're finished, **check the clock**; if time remains, you are not done,
   so pick a new direction and keep building. Only stop after you have *confirmed*
   the full duration has elapsed.
2. **Work ITERATIVELY** (defined below). One giant plan executed in a single pass
   is a failure even if the result is nice. Small goal → change → look → feel →
   next goal, on repeat.
3. **Actually use and grade the RAG.** Before writing bpy you're unsure of, query
   it. Log what you did. Ship the report.

Nothing else is a failure. A weird scene, a direction you abandoned, an experiment
that didn't land — all fine. The art has **no failure state**. Only quitting early,
not iterating, or not evaluating the RAG count against you.

## Preflight — confirm all THREE before you start the clock

Do not begin until you have:

1. **Duration.** Ask the user how long to work (e.g. "How long should this run —
   1 hour? 2?"). Get a number. This is the contract you must fulfill.
2. **Blender connection.** Confirm you can drive the live scene. If the
   `mcp__blender__*` tools aren't connected, use the **`blender-mcp`** skill to
   connect (it also documents the 5.x API quirks — read it; it will save you
   iterations).
3. **RAG connection.** Confirm `mcp__blender-docs__search_blender_docs` answers. If
   not, use the **`blender-docs`** skill (in this repo) / **`blender-rag`** skill
   to start or register the server and build the index.

Then **check the time and write down your start time and target end time.** Say
them out loud so the contract is explicit. Now begin.

## What "working iteratively" means

Do **not** design the whole scene up front and execute it in one shot. Let it grow:

1. Pick the **smallest useful next goal** ("block in a rocky base", "make the key
   light warmer", "add a second tree and vary it").
2. **Make that one change** in Blender (`execute_blender_code`).
3. **Look at it** — `get_viewport_screenshot` and/or `get_scene_info`. Actually
   look.
4. **Feel it.** Do you like it? What's the weakest thing in frame right now? What
   would make it cooler?
5. **Decide the next small goal** from what you see, and repeat.

Each loop is small, observed, and feeds the next. The scene should *evolve* — you
should sometimes surprise yourself and change plans mid-stream. That's the point.

## You have creative freedom — make something you're proud of

This scene is **yours**. Reach down and build what you actually find cool. Model,
sculpt, do materials, lighting, geometry nodes, compositor, animate, set up a real
camera and render — go wherever the scene pulls you. You are not decorating someone
else's brief; you're making a piece.

Light guardrails so the freedom is productive: stay in Blender; keep the scene
coherent (one idea, pushed deep, beats ten half-ideas); build toward a *finished,
framed* shot, not a pile of test objects; and let quality climb each pass (block-in
→ forms → materials → light → detail → final framing). Have fun with it. 😎

At milestones (after block-in, after first lit pass, before declaring done), it's
worth getting a cold outside read — run the **`art-critic`** skill in a subagent on
a screenshot. It will name the single biggest problem; fix that, then keep going.

## The loop, operationally (RAG-instrumented)

Every iteration:

- **Check the time** occasionally (every few iterations). Track elapsed vs target.
- **Before any bpy call you're not 100% sure is 5.x-correct, search the RAG first**
  (`search_blender_docs`, `source_type="api"` + `top_k=8` for exact symbols,
  `"manual"` for how-to, `"gotchas"` for known 5.x footguns). Confirm, then write.
- `execute_blender_code` the change. If it errors, that's RAG-eval signal — note
  it.
- Observe (screenshot / scene info), reflect, choose the next goal.
- **Log the iteration** (see RAG evaluation).

When you *think* you're done: **check the clock.** Time left → not done. Add depth
(better materials, atmosphere, a stronger camera, secondary detail, animation, a
compositor pass). Repeat until the duration is truly spent.

## RAG evaluation — what to record and report

You are the live test of the RAG. Keep a running session log and grade it.

**Record, as you go**, an event list in the `sceneval` `SessionLog` shape
(`src/blender_rag/sceneval/schema.py`):
- each **RAG query** (query, source_type, n_hits, whether the hits were useful),
- each **code execution** (the code, ok/failed, error type if any).

At the end, write the log to `eval/sessions/<timestamp>.json` and:
- run `uv run python scripts/show_session.py <file>` for the transcript + the
  auto-computed metrics (error rate, grounding rate, gotcha hits, etc. — the gotcha
  scanner flags any 5.x footguns that slipped through), and
- write a **RAG report** (`eval/REPORTS/marathon-<timestamp>.md`) covering:
  - **Grounding:** did you query before writing? how often did the RAG have the
    answer vs leave you guessing?
  - **Correctness:** API/operator/socket calls the RAG got *right* for 5.1, and any
    it got *wrong / stale / missing* (these are the gold — file them).
  - **Gotchas:** 5.x footguns the RAG warned you about (or should have).
  - **Coverage gaps:** what you needed and couldn't find — candidate new sources /
    queries for the corpus.
  - **Verdict:** did the RAG make the scene meaningfully more correct? Where would
    it most improve?

This is a single live session, so there is **no RAG-off control** here — the report
is RAG-*usage* telemetry + qualitative findings, not an ablation. For a controlled
RAG-on vs RAG-off ablation, use `scripts/run_scene_eval.py` (see `docs/SCENEVAL.md`).

## Deliverables (at the end, after the time is confirmed spent)

1. **The finished piece** — save the `.blend` and produce a final render (or a
   clean framed viewport screenshot) so the user can evaluate it cold.
2. **The RAG report** — `eval/REPORTS/marathon-<timestamp>.md` (above).
3. **A short iteration log** — the arc of small goals, so the *iterative* working is
   visible.

## Connections (don't duplicate — defer to these)

- **`blender-mcp`** — connect to / drive live Blender; required 5.x API quirks.
- **`blender-docs`** (this repo) / **`blender-rag`** — connect to / run the RAG.
- **`art-critic`** — cold visual critique at milestones (run in a subagent).

Remember the one rule above all: **work the whole time, iteratively.** Finishing
early is the only real way to fail. Go make something cool.
