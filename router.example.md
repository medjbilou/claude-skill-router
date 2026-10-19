# My routing rules

Copy this file to ~/.claude/router.md and edit it. /route reads it before the catalog, and a rule
that matches the request beats the catalog's own picks. One line per kind of task. Name only skills
you have installed (`/route` with no request, or `inventory.py`, lists them).

- Polishing an existing UI screen -> better-ui (never impeccable unless I name it)
- Reviewing a diff or a PR -> simplify first, then code-review
- Any production error or stack trace -> diagnosing-bugs
- Writing in French -> skip humanizer
- Anything that deploys -> ask me first, even in a test environment
