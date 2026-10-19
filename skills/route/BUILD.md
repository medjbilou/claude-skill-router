# Build the personal skill catalog

The catalog tells the router, for every installed skill, when to use it, when not to, what to run
after it, and what it needs. It is built once per machine by parallel agents that read each skill.
`<base>` is the skill's base directory; `S` is `python3 <base>/scripts/inventory.py`;
`C` is the catalog folder (`~/.claude/route-catalog`, or `$ROUTE_CATALOG_DIR`).

## 1. Estimate and confirm

Run `S` (no flag) and count the skills, then tell the user, in two lines:
- how many skills and how many batch agents (one per 40 skills, plus one Default-picks agent per
  ~4 categories), and that each catalog agent reads about 40 skill files (roughly 150k tokens);
- that nothing is installed, removed or edited outside `C`.

Wait for a go, unless the user already said to go ahead or this is a non-interactive run.

## 2. Write the profile

Write `C/PROFILE.md` (at most 25 lines) so the agents tailor the catalog to this user. Use what you
can read cheaply: `~/.claude/CLAUDE.md`, this repo's `CLAUDE.md` and README, the language files and
package manifests at the repo root, and your memory of this conversation. Cover: role, main
languages and frameworks, platforms and hosting used, platforms clearly NOT used, the user's own
custom skills and their business domain, and stated preferences. Write facts, not guesses; leave a
line out when you do not know it. Show it to the user in one short block; they can correct it later.

## 3. List built-in skills

Built-in skills have no file on disk, so the script cannot find them. Write every skill in your own
available-skills list to `C/_work/visible.txt`, one per line: `name<TAB>description`. The script
keeps only the ones it does not find on disk.

## 4. Make the batches

Run `S --batches 40`. It writes `C/_work/batch-NN.json` (each skill with its path, source, user-only
flag, description and how often the user ran it) and `C/_work/all-names.json`.

## 5. Catalog agents

Read `<base>/prompts/catalog-agent.md`. Spawn one general-purpose agent per batch, all in ONE
message so they run in parallel (waves of at most 10). Give each agent that prompt with these
placeholders filled: `{BATCH}` the batch json path, `{OUT}` the same path ending in `.md`,
`{NAMES}` = `C/_work/all-names.json`, `{PROFILE}` = `C/PROFILE.md`, `{SCRIPT}` = `S`.
Wait for all of them.

## 6. Assemble

Run `S --assemble`. It merges the batch output into one file per category and reports MISSING skills
and unparsed lines. For a few problems, fix the batch `.md` yourself and run `--assemble` again; for
many, re-run the agent of that batch.

## 7. Default picks

Run `S --status` to list the categories whose header still says `Default picks: (pending)`.
Read `<base>/prompts/picks-agent.md` and spawn agents in parallel, each owning about 4 of those
categories (`{FILES}` = the category file paths, `{PROFILE}` = `C/PROFILE.md`). For a category with
fewer than 3 skills, write its Default picks line yourself.

## 8. Finish

Run `S --index`, then `S --check` (expect `catalog in sync`) and `S --status` (expect no pending
categories). Delete `C/_work/`. Report: number of skills cataloged, categories, anything skipped,
and the skills whose descriptions the agents flagged as empty or misleading (from their final
messages), so the user can fix them.
