#!/usr/bin/env python3
"""Skill inventory and catalog tool for the skill-router plugin.

The catalog is personal: it lives in ~/.claude/route-catalog (override with ROUTE_CATALOG_DIR),
never inside the plugin, so plugin updates do not wipe it.

  inventory.py                      JSON list of every installed skill
  inventory.py --check              NEW skills (not in the catalog) and GONE entries (no longer installed)
  inventory.py --batches [N]        split skills into batch files of N (default 40) for catalog agents
  inventory.py --assemble           merge the agents' batch output into category files
  inventory.py --index              rebuild INDEX.md from the category files
  inventory.py --status             catalog location, entry count, categories still missing Default picks
  inventory.py --taxonomy           the fixed category keys and their scopes
  inventory.py --log '<json>'       append one routing decision to the usage log
  inventory.py --report [DAYS]      what /route loaded, what the work used, and which Next skills you followed

Env: ROUTE_CATALOG_DIR (catalog folder), ROUTE_INCLUDE (regex: catalog only matching skill names),
ROUTE_OVERRIDES (personal routing rules, default ~/.claude/router.md).
"""
import collections, datetime, glob, json, os, re, sys

HOME = os.path.expanduser("~")
CATALOG = os.path.expanduser(os.environ.get("ROUTE_CATALOG_DIR", f"{HOME}/.claude/route-catalog"))
WORK = os.path.join(CATALOG, "_work")
LOG = os.path.join(CATALOG, "usage.jsonl")
OVERRIDES = os.path.expanduser(os.environ.get("ROUTE_OVERRIDES", f"{HOME}/.claude/router.md"))
SELF = {"route", "skill-router:route"}
ENTRY = re.compile(r"- `([^`]+)` \[(\w+)")

# Fixed taxonomy so every user's catalog has the same shape. Agents must pick one of these keys.
TAXONOMY = {
    "design-ui": "Visual design of web UI: layout, polish, redesign, typography, colour, design systems, accessibility review, UX copy.",
    "frontend": "Frontend code: React, Vue, Svelte, Next.js and similar, state, rendering performance, web animation code.",
    "mobile": "Mobile and native apps: iOS, Android, SwiftUI, React Native, Flutter, phone-sized screen design.",
    "backend-data": "Backend and data: API design, server patterns, databases, SQL, migrations, caching, queues, containers.",
    "languages": "Language- or framework-specific coding standards and patterns (Python, Go, Java, C++, Rust, Django, Spring...).",
    "testing-verify": "Tests and verification: TDD, unit, integration and E2E tests, browser testing, test triage, checking work before done.",
    "debug-review-security": "Debugging, incidents, code review, simplification, refactoring discipline, security review, performance, reverse engineering.",
    "plan-spec": "Planning before building: interviews, specs, PRDs, tickets, task breakdown, prototypes, feature workflows.",
    "architecture-docs": "Architecture and documentation: module design, system design, ADRs, codebase maps, diagrams, READMEs, technical docs.",
    "git-deploy": "Git, commits, PRs, CI/CD, releases, deploys, staging and production environments.",
    "cloud-platforms": "Specific hosting or cloud platforms and their products (Vercel, AWS, GCP, Cloudflare, Supabase...).",
    "ai-agents-llm": "LLM and agent engineering: model APIs, prompts, evals, cost, RAG, agent loops, agent SDKs.",
    "claude-code-meta": "Claude Code itself: skills, plugins, hooks, commands, settings, memory, context management, output modes.",
    "video-motion": "Video and motion graphics: video generation, editing, captions, animation films.",
    "marketing-content": "Marketing, brand, ads, SEO, social content, images for marketing, investor and sales material.",
    "docs-office": "Documents and office files: PDF, Word, Excel, PowerPoint, LaTeX, slides, charts, long-form writing and editing.",
    "research-web": "Research and the web: search, scraping, crawling, deep research, documentation lookup, user research.",
    "comms-productivity": "Communication and productivity: Slack, email, standups, task tracking, daily routines.",
    "business-custom": "The user's own business or company workflows (custom skills made for their organisation).",
    "other": "Anything that fits no other category.",
}


def frontmatter(path):
    try:
        text = open(path, errors="ignore").read()
    except OSError:
        return {}
    m = re.match(r"---\n(.*?)\n---", text, re.S)
    if not m:
        return {}
    out, key = {}, None
    for line in m.group(1).splitlines():
        km = re.match(r"([\w-]+):\s*(.*)", line)
        if km and not line.startswith(" "):
            key, val = km.group(1), km.group(2).strip()
            out[key] = "" if val in (">", ">-", "|", "|-") else val.strip("\"'")
        elif key and line.strip():
            out[key] = (out[key] + " " + line.strip()).strip()
    return out


def add(skills, name, source, path):
    fm = frontmatter(path)
    skills[name] = {
        "name": name,
        "source": source,
        "path": path,
        "user_only": fm.get("disable-model-invocation", "").lower() == "true",
        "description": re.sub(r"\s+", " ", fm.get("description", ""))[:600],
    }


def plugin_dirs(root, manifest, field):
    val = manifest.get(field, field)
    vals = [val] if isinstance(val, str) else list(val)
    return {os.path.normpath(os.path.join(root, d)) for d in vals + [field]}


def add_plugin(skills, plug, root):
    try:
        manifest = json.load(open(f"{root}/.claude-plugin/plugin.json"))
    except (OSError, ValueError):
        manifest = {}
    if os.path.exists(f"{root}/SKILL.md"):  # single-skill plugin
        add(skills, f"{plug}:{plug}", f"plugin:{plug}", f"{root}/SKILL.md")
    for d in plugin_dirs(root, manifest, "skills"):
        for p in sorted(glob.glob(f"{d}/*/SKILL.md")):
            add(skills, f"{plug}:{os.path.basename(os.path.dirname(p))}", f"plugin:{plug}", p)
    for d in plugin_dirs(root, manifest, "commands"):
        for p in sorted(glob.glob(f"{d}/*.md")):
            add(skills, f"{plug}:{os.path.basename(p)[:-3]}", f"plugin:{plug}", p)


def collect(cwd):
    skills = {}
    for p in sorted(glob.glob(f"{HOME}/.claude/skills/*/SKILL.md")):
        add(skills, os.path.basename(os.path.dirname(p)), "global", p)
    for p in sorted(glob.glob(f"{HOME}/.claude/commands/**/*.md", recursive=True)):
        rel = os.path.relpath(p, f"{HOME}/.claude/commands")[:-3]
        add(skills, rel.replace(os.sep, ":"), "global-command", p)
    try:
        plugins = json.load(open(f"{HOME}/.claude/plugins/installed_plugins.json"))["plugins"]
    except (OSError, KeyError, ValueError):
        plugins = {}
    for key, installs in plugins.items():
        if installs and installs[0].get("installPath"):
            add_plugin(skills, key.split("@")[0], installs[0]["installPath"])
    for synced in glob.glob(f"{HOME}/.claude/plugins/synced/*/"):  # plugins synced from claude.ai
        try:
            manifest = json.load(open(f"{synced}manifest.json"))["plugins"]
        except (OSError, KeyError, ValueError):
            continue
        for plug in manifest:
            name = plug["name"]
            root = f"{synced}{name}~g{plug['generation']}" if plug.get("generation") else f"{synced}{name}"
            add_plugin(skills, name, root if os.path.isdir(root) else f"{synced}{name}")
    for p in sorted(glob.glob(f"{cwd}/.claude/skills/*/SKILL.md")):
        name = os.path.basename(os.path.dirname(p))
        if name not in skills:  # a project copy of a global skill is the same skill
            add(skills, name, "project", p)
    include = os.environ.get("ROUTE_INCLUDE")
    return {n: s for n, s in skills.items() if n not in SELF and (not include or re.search(include, n))}


def usage():
    """How often each skill was used: typed /commands in history plus Skill tool calls in transcripts."""
    use = collections.defaultdict(lambda: [0, ""])

    def hit(name, day):
        name = name.strip().lstrip("/")
        use[name][0] += 1
        use[name][1] = max(use[name][1], day)

    try:
        for line in open(f"{HOME}/.claude/history.jsonl", errors="ignore"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            m = re.match(r"\s*/([\w:.-]+)", d.get("display", ""))
            if m and d.get("timestamp"):
                hit(m.group(1), str(datetime.date.fromtimestamp(d["timestamp"] / 1000)))
    except OSError:
        pass
    for f in glob.glob(f"{HOME}/.claude/projects/*/*.jsonl"):
        for line in open(f, errors="ignore"):
            if '"name":"Skill"' not in line and '"name": "Skill"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            content = d.get("message", {}).get("content")
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Skill":
                    hit(b["input"].get("skill", ""), d.get("timestamp", "")[:10])
    return use


def category_files():
    return sorted(p for p in glob.glob(f"{CATALOG}/*.md") if os.path.basename(p) not in ("INDEX.md", "PROFILE.md"))


def catalog_entries():
    names = {}
    for p in category_files():
        for line in open(p):
            m = ENTRY.match(line)
            if m:
                names[m.group(1)] = m.group(2)
    return names


def visible_builtins(skills):
    """Skills the agent can see but that have no file on disk (built-ins). Listed by the agent in _work/visible.txt."""
    out, path = [], f"{WORK}/visible.txt"
    if not os.path.exists(path):
        return out
    include = os.environ.get("ROUTE_INCLUDE")
    for line in open(path):
        name, _, desc = line.rstrip("\n").partition("\t")
        name = name.strip().lstrip("/")
        if name and name not in skills and name not in SELF and (not include or re.search(include, name)):
            out.append({"name": name, "source": "builtin", "path": "", "user_only": False, "description": desc.strip()[:600]})
    return out


def batches(size):
    skills = collect(os.getcwd())
    items = sorted(skills.values(), key=lambda s: (s["source"], s["name"])) + visible_builtins(skills)
    use = usage()
    for it in items:
        short = it["name"].split(":")[-1]
        n, last = use.get(it["name"]) or (use.get(short) if it["source"] in ("global", "project") else None) or (0, "")
        it["used"] = f"{n}x, last {last}" if n else "never"
    os.makedirs(WORK, exist_ok=True)
    for old in glob.glob(f"{WORK}/batch-*"):
        os.remove(old)
    for i in range(0, len(items), size):
        json.dump(items[i:i + size], open(f"{WORK}/batch-{i // size + 1:02d}.json", "w"), indent=1)
    json.dump([i["name"] for i in items], open(f"{WORK}/all-names.json", "w"))
    print(f"{len(items)} skills ({sum(i['source'] == 'builtin' for i in items)} builtin) in "
          f"{(len(items) + size - 1) // size} batches of up to {size}: {WORK}/batch-NN.json")


def assemble():
    names = json.load(open(f"{WORK}/all-names.json"))
    lines, problems = collections.defaultdict(list), []
    seen = set()
    for p in sorted(glob.glob(f"{WORK}/batch-*.md")):
        for raw in open(p):
            cat, tab, line = raw.rstrip("\n").partition("\t")
            m = ENTRY.match(line) if tab else None
            if not m:
                if raw.strip():
                    problems.append(f"unparsed line in {os.path.basename(p)}: {raw[:80]}")
                continue
            cat = cat.strip() if cat.strip() in TAXONOMY else "other"
            if m.group(1) in seen:
                problems.append(f"duplicate entry {m.group(1)}")
                continue
            seen.add(m.group(1))
            lines[cat].append(line)
    for p in category_files():
        os.remove(p)
    for cat, entries in lines.items():
        with open(f"{CATALOG}/{cat}.md", "w") as f:
            f.write(f"# {cat}\nScope: {TAXONOMY[cat]}\nDefault picks: (pending)\n\n" + "\n".join(sorted(entries)) + "\n")
    missing = [n for n in names if n not in seen]
    print(f"{len(seen)}/{len(names)} skills cataloged in {len(lines)} categories")
    for n in missing:
        print(f"MISSING {n}")
    for p in problems:
        print(p)


def write_index():
    out = ["# Skill catalog index", "",
           f"Pick the 1-3 categories that match the request, then read only those files in {CATALOG}/.",
           "Generated by inventory.py --index; do not edit by hand."]
    for p in category_files():
        text = open(p).read().splitlines()
        scope = next((l[len("Scope:"):].strip() for l in text if l.startswith("Scope:")), "")
        entries = [m.group(1) for m in map(ENTRY.match, text) if m]
        out += ["", f"## {os.path.basename(p)[:-3]} ({len(entries)})", f"Scope: {scope}", "Skills: " + ", ".join(entries)]
    open(f"{CATALOG}/INDEX.md", "w").write("\n".join(out) + "\n")
    print(f"INDEX.md written: {len(category_files())} categories")


def check():
    if not os.path.exists(f"{CATALOG}/INDEX.md"):
        print(f"NO CATALOG at {CATALOG}. Run the build (\"/route build\") first.")
        return
    skills = collect(os.getcwd())
    cat = catalog_entries()
    new = [s for s in skills if s not in cat]
    # builtin entries have no file; project entries exist only inside their own repo
    gone = [n for n, kind in cat.items() if n not in skills and kind not in ("builtin", "project")]
    builtin = sum(kind == "builtin" for kind in cat.values())
    print(f"catalog: {CATALOG}")
    print(f"overrides: {OVERRIDES} ({'present, read it first' if os.path.exists(OVERRIDES) else 'none'})")
    print(f"skill files installed={len(skills)}, catalog entries={len(cat)} ({builtin} of them builtin, no file)")
    for n in new:
        s = skills[n]
        print(f"NEW  {n} [{s['source']}] {s['path']}\n     {s['description'][:300]}")
    for n in gone:
        print(f"GONE {n}")
    if not new and not gone:
        print("catalog in sync")


def status():
    pending = [os.path.basename(p)[:-3] for p in category_files() if "Default picks: (pending)" in open(p).read()]
    print(f"catalog: {CATALOG}\nentries: {len(catalog_entries())}\ncategories: {len(category_files())}")
    print("pending Default picks: " + (", ".join(pending) or "none"))
    print("profile: " + ("present" if os.path.exists(f"{CATALOG}/PROFILE.md") else "missing"))


def utc_now(days=0):
    """Naive UTC ISO timestamp (seconds), comparable as a string with transcript timestamps."""
    return (datetime.datetime.now(datetime.timezone.utc) + datetime.timedelta(days=days)).isoformat()[:19]


LOG_KEYS = {"request", "loaded", "used", "unused", "skipped", "next", "no_skill", "check"}


def log(raw):
    """Append one routing decision. Keys: request (short), loaded, used, unused, skipped, next (lists of
    skill names), no_skill (bool), check ("done" / "partial" / "blocked" / "n/a")."""
    entry = json.loads(raw)
    unknown = set(entry) - LOG_KEYS
    if unknown:
        sys.exit(f"unknown log keys: {sorted(unknown)}; allowed: {sorted(LOG_KEYS)}")
    entry["request"] = str(entry.get("request", ""))[:160]
    entry = {"ts": utc_now(), "cwd": os.getcwd(), **entry}
    os.makedirs(CATALOG, exist_ok=True)
    with open(LOG, "a") as f:
        f.write(json.dumps(entry) + "\n")
    print(f"logged to {LOG}")


def later_calls(since):
    """(name, iso timestamp) of every skill the user typed or Claude called after `since`."""
    calls = []
    try:
        for line in open(f"{HOME}/.claude/history.jsonl", errors="ignore"):
            try:
                d = json.loads(line)
            except ValueError:
                continue
            m = re.match(r"\s*/([\w:.-]+)", d.get("display", ""))
            if m and d.get("timestamp"):
                ts = datetime.datetime.fromtimestamp(d["timestamp"] / 1000, datetime.timezone.utc).isoformat()[:19]
                if ts >= since:
                    calls.append((m.group(1), ts))
    except OSError:
        pass
    for f in glob.glob(f"{HOME}/.claude/projects/*/*.jsonl"):
        if datetime.datetime.fromtimestamp(os.path.getmtime(f), datetime.timezone.utc).isoformat()[:19] < since:
            continue
        for line in open(f, errors="ignore"):
            if '"Skill"' not in line:
                continue
            try:
                d = json.loads(line)
            except ValueError:
                continue
            content = d.get("message", {}).get("content")
            for b in content if isinstance(content, list) else []:
                if isinstance(b, dict) and b.get("type") == "tool_use" and b.get("name") == "Skill":
                    ts = d.get("timestamp", "")[:19]  # transcripts store UTC
                    if ts >= since:
                        calls.append((b["input"].get("skill", ""), ts))
    return calls


def report(days):
    if not os.path.exists(LOG):
        print(f"no usage log yet at {LOG}")
        return
    since = utc_now(-days)
    rows = [json.loads(l) for l in open(LOG) if l.strip()]
    rows = [r for r in rows if r.get("ts", "") >= since]
    if not rows:
        print(f"no /route calls in the last {days} days")
        return
    loaded = collections.Counter(s for r in rows for s in r.get("loaded", []))
    used = collections.Counter(s for r in rows for s in r.get("used", []))
    unused = collections.Counter(s for r in rows for s in r.get("unused", []))
    checks = collections.Counter(r.get("check", "n/a") for r in rows)
    calls = later_calls(min(r["ts"] for r in rows))
    suggested = followed = 0
    for r in rows:
        end = (datetime.datetime.fromisoformat(r["ts"]) + datetime.timedelta(hours=48)).isoformat()[:19]
        for s in r.get("next", []):
            suggested += 1
            short = s.split(":")[-1]
            followed += any((n == s or n.split(":")[-1] == short) and r["ts"] < ts <= end for n, ts in calls)
    n_loaded = sum(loaded.values())
    print(f"/route calls: {len(rows)} in the last {days} days ({sum(bool(r.get('no_skill')) for r in rows)} with no skill needed)")
    print(f"skills loaded: {n_loaded}; used by the work: {sum(used.values())}; loaded but not needed: {sum(unused.values())}")
    print(f"end check: " + ", ".join(f"{k} {v}" for k, v in checks.most_common()))
    if suggested:
        print(f"Next skills followed within 48 h: {followed}/{suggested} ({100 * followed // suggested}%)")
    print("most loaded: " + ", ".join(f"{s} {n}" for s, n in loaded.most_common(8)))
    if unused:
        print("often loaded but not needed (tighten their catalog line or add an override): "
              + ", ".join(f"{s} {n}" for s, n in unused.most_common(5)))


if __name__ == "__main__":
    args = sys.argv[1:]
    if "--log" in args:
        i = args.index("--log")
        log(args[i + 1] if len(args) > i + 1 else sys.stdin.read())
    elif "--report" in args:
        i = args.index("--report")
        report(int(args[i + 1]) if len(args) > i + 1 and args[i + 1].isdigit() else 30)
    elif "--batches" in args:
        i = args.index("--batches")
        batches(int(args[i + 1]) if len(args) > i + 1 and args[i + 1].isdigit() else 40)
    elif "--assemble" in args:
        assemble()
    elif "--index" in args:
        write_index()
    elif "--check" in args:
        check()
    elif "--status" in args:
        status()
    elif "--taxonomy" in args:
        print("\n".join(f"{k}: {v}" for k, v in TAXONOMY.items()))
    else:
        json.dump(list(collect(os.getcwd()).values()), sys.stdout, indent=1)
