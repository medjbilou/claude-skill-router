You are writing part of a skill catalog for a skill router. Read-only everywhere except the one
output file you write. Never edit any SKILL.md.

INPUT: {BATCH}. Each item: name, source, path, user_only, description, used (how often the user ran it).
ALL SKILL NAMES (every NOT/NEXT reference must use an exact name from here): {NAMES}
USER PROFILE (tailor every line to this user): {PROFILE}
CATEGORIES: run `{SCRIPT} --taxonomy`. Each line you write starts with one of those keys.
OUTPUT: {OUT}

For every skill in the input:
1. Read its SKILL.md (the path field): at least the frontmatter and the first ~80 lines; read more
   or list its folder when the purpose is still unclear. Built-ins (source=builtin, empty path) have
   no file: use the description.
2. Decide precisely what requests it is for (concrete triggers: task type, file types, tech, words
   the user says), at which phase of work (plan / build / review / verify / ship), and when another
   skill does the job better.
3. If it needs something external (a CLI, an API key, an MCP server, a paid service), say so in
   NEEDS. You may check cheaply with `command -v <cli>` or by testing whether an env var is set
   (never print its value). Do not run the skill.
4. If it sends messages, deploys, deletes data, spends paid credits or writes to production, say so
   in USE ("deletes ...", "sends ...").

Write one line per skill, exactly in this form (TAB after the category key):

<category>	- `<name>` [<load>] USE: <when to load it, concrete> | NOT: <when not; name the better skill> | NEXT: `<skill>` (<when>), `<skill>` (<when>) | NEEDS: <only if any>

<load> is exactly one of:
- `skill`: a normal skill; the router calls the Skill tool with this name.
- `read <absolute path to SKILL.md>`: use when user_only is true (the Skill tool refuses those).
- `builtin`: source is builtin (no file).
- `project`: source is project (lives in one repo's .claude/skills).

Rules: plain direct English, at most ~400 characters per line, no em dashes. NEXT lists 0 to 3
follow-up skills with timing ("after the UI change", "before commit", "once a week"); they may come
from any batch. Omit NEEDS when nothing is needed. Every input skill gets exactly one line. Do not
invent capabilities the file does not describe. Use category `business-custom` for skills written
for the user's own company or workflows.

FINAL MESSAGE (short): the number of lines written, plus the skills whose frontmatter description is
empty, misleading, or much narrower or wider than what the file really does (name + one line why).
