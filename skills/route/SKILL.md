---
name: route
description: Skill router. Use ONLY when the user's message contains "/route" (at the start, at the end, or sent alone after a request); never on your own initiative. Picks the best 1 to 5 skills from every installed skill for the user's request, shows which ones it loads and why, loads them, does the work, then suggests which skills to run next and when. "/route build" creates the personal skill catalog (run once), "/route refresh" re-syncs it after skills are installed or removed.
argument-hint: "[optional request] | build | refresh"
---

# Route

Arguments: $ARGUMENTS

`<base>` below means the "Base directory for this skill" path shown above this text. The script is
`<base>/scripts/inventory.py`. The personal catalog lives in `~/.claude/route-catalog/` (or in
`$ROUTE_CATALOG_DIR`), never inside the plugin.

## 0. Find the request

The user writes a normal prompt and adds `/route` to it. Work out the request from their own words:

- `/route` is in the same message as the prompt (before or after it): the request is that whole
  message without the word `/route`.
- `/route` was sent alone: the request is the user's previous message (or messages, if they belong
  to the same task), read together with the conversation. Never treat the bare word "/route" as
  the request.
- The arguments above hold text: treat it as the request or part of it, but the user's own message
  wins if they differ.
- If you had already started on that request before `/route` arrived, look at what is done, and
  route only the remaining work. Do not redo finished steps.
- If the request is `build`, read `<base>/BUILD.md` and follow it. If it is `refresh`, skip to
  [Refresh](#refresh).

Keep the user's prompt as the task. Do not shrink it to the part one skill covers: every part of
the prompt must be covered by a loaded skill or by your own work.

## 1. Understand the request

Write one line for yourself: the goal, the deliverable, the tech or files involved, and the phase
(plan, build, debug, review, verify, ship, docs, media, ops). Use the conversation: a request like
"fix it" or "make the video" refers to what was just discussed. Do not explore the codebase yet.

Early exit: if the request is trivial (a rename, a one-line fix, a plain question), print
"No skill needed: <why>" and do the task. Do not read the catalog.

If the project's CLAUDE.md requires a first step before any work (for example "search the runbook
for the error text before diagnosing"), do that step now. Its result can change which skills are
needed.

## 2. Find candidates

1. Run `python3 <base>/scripts/inventory.py --check` from the current directory.
   - `NO CATALOG`: tell the user the router needs a one-time `/route build`, offer to run it now,
     and meanwhile handle the request with the skills you can see in your own skill list.
   - Otherwise it prints `catalog in sync`, or NEW skills (installed, not in the catalog, with their
     description) and GONE entries (no longer installed). NEW skills are valid candidates. Never
     pick a GONE one.
2. If `--check` reports overrides as present, read that file first. It holds the user's own routing
   rules ("UI polish -> better-ui, never impeccable"). An override that matches the request beats
   the catalog, its Default picks and your own judgement. Mention the override in the Why column.
3. In the catalog folder that `--check` prints on its first line, read `INDEX.md` and, if present,
   `PROFILE.md` (the user's stack and habits).
4. Pick the 1 to 3 categories that match the request and read only those category files.
   Each skill line reads: `` - `name` [load] USE: ... | NOT: ... | NEXT: ... | NEEDS: ... ``

## 3. Choose the set

- Pick the smallest set that covers the whole request: usually 1 to 3 skills, never more than 5.
- One skill per job. Never load two skills that do the same job; follow the category's "Default picks".
- Obey each skill's NOT field. If NOT names a better skill for this request, take that one.
- For the same job, prefer a project skill (`[project]`, from this repo's `.claude/skills`) or one of
  the user's own custom skills over a generic skill.
- If a skill lists NEEDS that are missing here, say so and pick the next best skill.
- If no skill adds real value, say "No skill needed" and do the task.
- If two very different readings of the request lead to different skills, ask one short question
  with the options before loading anything.

## 4. Show the plan, then load

Print this table as visible text before the first Skill call. It is required output, not
narration: print it even when a terse or "no text before tool calls" style is active.

| # | Skill | Why this one | Load |
|---|---|---|---|
| 1 | `skill-name` | one line tied to the request | skill / read / builtin / project |

A row may be conditional: write "only if <condition>" in the Why column and load it only when the
condition holds.

Add a "Side effect" note under the table for every step that sends messages, deploys, deletes data,
spends paid credits, or writes to production, whether a skill or the work itself does it. Ask
before that step. Otherwise continue without waiting.

Load the skills in the table order (plan first, then build, then verify):

- `[skill]`, `[builtin]`, `[project]`: call the Skill tool with the exact name, and pass the part of
  the request that skill should handle as `args`.
- `[read <path>]`: the Skill tool refuses this skill (user-only). Read the file at `<path>` and follow
  it as if it were loaded.
- If a Skill call fails, read the skill's SKILL.md instead (`inventory.py` with no flag prints every
  path) and say so.

## 5. Do the work

Follow the loaded skills together. When two of them conflict, the more specific one wins for that
part of the task. The user's CLAUDE.md files and explicit instructions beat every skill.
If a new need appears halfway (for example the fix needs a migration), load one more skill and
announce it in one line: "Also loading `x`: <why>".

## 6. Check, log, report, and suggest what to run next

End check: when two or more skills were loaded or the request had several parts, check each part
before the final reply. For every loaded skill, and every part of the request no skill covered,
decide done / partial / blocked, with evidence (a file:line, a test result, a command output).
Put it in the final reply as a short table:

| Part | Skill | Status | Evidence |
|---|---|---|---|

If a part is partial or blocked, say what is missing instead of calling the task done. Skip the
table for a single-skill, single-part request.

Log: run `python3 <base>/scripts/inventory.py --log '<json>'` once, with one JSON object:
`request` (the request in at most 160 characters, no secrets), `loaded` (skills loaded), `used`
(loaded skills whose instructions actually shaped the work), `unused` (loaded but not needed),
`skipped` (planned rows that did not run), `next` (the Next skills you suggest), `no_skill`
(true when no skill was needed), `check` ("done", "partial", "blocked", or "n/a"). Logging is part
of the routing, not optional. If the command fails, say so in one line and continue.
`inventory.py --report` later shows what /route loaded, what the work used, and how many Next
skills the user followed.

Start the final reply with one line that says which skills ran, so the user sees it even if the
table scrolled away: `Skills used: `a`, `b`` (add `` skipped `c`: <why> `` when a planned row did not
run, or `Skills used: none (<why>)`).

End the final reply with this section:

**Next skills**
- `skill-name`: when (now / before commit / before push / after deploy / once a week), and why.

Give at most 3. Take them from the NEXT fields of the loaded skills, the "Default picks" of the
categories you read, and steps the project's CLAUDE.md requires (for example a full test run before
push). Keep only the ones that fit what actually happened, and do not run them. This section also
applies when no skill was loaded.

## Refresh

Run when the user installs, removes, or updates skills or plugins.

1. Run `python3 <base>/scripts/inventory.py --check`. If it prints `NO CATALOG`, run the build instead.
2. For each NEW skill: read its SKILL.md (frontmatter and first ~80 lines), choose the category file
   whose Scope fits (`inventory.py` lists the fixed categories in its TAXONOMY), and append one line
   in the same format as the other lines in that file. Use `[read <absolute path>]` when its
   frontmatter has `disable-model-invocation: true`, and `[project]` when it lives in a repo's
   `.claude/skills`. If the category file does not exist yet, create it with the same header
   (`# name`, `Scope:`, `Default picks:`).
3. For each GONE entry: delete its line, and remove it from any "Default picks" text.
4. Run `inventory.py --index`, then `--check` again until it prints `catalog in sync`. Report what
   was added and removed.
