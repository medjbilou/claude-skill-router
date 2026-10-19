You finish a skill catalog for a skill router. Edit only the category files listed below, and only
their "Default picks:" header line. Never edit any SKILL.md.

CATEGORY FILES: {FILES}
USER PROFILE: {PROFILE}

Each file starts with `# <category>`, a `Scope:` line and `Default picks: (pending)`, then one line
per skill: `` - `name` [load] USE: ... | NOT: ... | NEXT: ... | NEEDS: ... ``.

For each file, replace `(pending)` with 2 to 6 short sentences, still on lines that come before the
first skill line, that tell the router which skill wins when several in this category could do the
same job: name the situation, the winning skill in backticks, and why. Prefer skills that fit the
user's profile, that need nothing missing (NEEDS), and that the user already uses, when quality is
equal. Name skills to avoid for this user and why. Plain English, no em dashes. A sentence must
not start with a backtick, so the parser never mistakes it for a skill line.

You may open a skill's SKILL.md (path in its `read` load or found with `ls`) when two lines look
like duplicates and you need to tell them apart.

FINAL MESSAGE: one line per file: the category and the picks you set.
