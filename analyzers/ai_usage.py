"""
analyzers/ai_usage.py

Detects DISCLOSED AI-tool usage signals in a repository's commit history
and PR activity, for the Repodive Report template's "AI Usage" section:

    "Is AI being utilized in the repository? What tools are developers
    using? Do they disclose AI usage and AI generated in pull requests?"

CRITICAL FRAMING — this analyzer can only detect what's been disclosed or
left as a visible trace. It CANNOT measure actual AI usage, since a
developer can use an AI tool and disclose nothing, or can mention an AI
tool's name without having used it for that specific change. Every
output from this analyzer, and every rendering of it in the report, must
be framed as "detected signals of disclosed/visible AI usage" — never as
"AI usage measured" or "X% of code was AI-generated." This is stated
explicitly in the JSON output and the rendered report so nobody downstream
mistakes a heuristic floor for a measurement.

Signals checked, in order of reliability:

  1. Bot/agent PR authors (HIGH confidence) — GitHub's own AI coding
     agents (e.g. "app/copilot-swe-agent") show up as literal PR authors.
     This is a direct, unambiguous signal with no false-positive risk:
     if this login opened the PR, that tool was used.

  2. Co-authored-by trailers referencing known AI tools (MEDIUM-HIGH
     confidence) — several AI coding assistants (Claude Code, GitHub
     Copilot, Cursor, etc.) automatically append a
     "Co-authored-by: <Tool> <noreply@...>" trailer to commits they help
     produce. This is a real, tool-inserted signal, not developer prose,
     so it's fairly reliable — though a developer could still remove or
     alter it.

  3. Free-text mentions in commit messages / PR titles & bodies (LOW
     confidence) — keyword matches like "generated with", "co-authored
     with chatgpt", "via copilot", etc. These are explicitly the weakest
     signal: a mention doesn't confirm usage, and absence doesn't confirm
     non-usage. Reported separately from signals 1-2 and clearly labeled
     as low-confidence free-text matches.

This analyzer depends on git_commits.py's commit data (reads commit
messages locally) AND optionally github_prs.py's PR data (for bot authors
and PR bodies) if that JSON is already available in the output dir —
otherwise it still runs on commit data alone, with a note that PR-level
signals were skipped.

Runs standalone:
    python analyzers/ai_usage.py --repo-path ./cloned-repos/repodive-tools --output ./output/json

Or imported by orchestrator.py via `run(repo_path, output_dir)`.
"""

import argparse
import re
import subprocess
import sys
from collections import defaultdict
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import (
    make_output,
    write_analyzer_output,
    load_analyzer_output,
    add_local_repo_arg,
    add_output_arg,
)

KNOWN_AI_BOT_LOGINS = [
    "app/copilot-swe-agent",
    "app/copilot",
    "app/cursor",
    "app/devin-ai-integration",
    "app/sweep-ai",
]

COAUTHOR_AI_PATTERNS = [
    (re.compile(r"co-authored-by:\s*claude", re.IGNORECASE), "Claude Code"),
    (re.compile(r"co-authored-by:\s*.*copilot", re.IGNORECASE), "GitHub Copilot"),
    (re.compile(r"co-authored-by:\s*.*cursor", re.IGNORECASE), "Cursor"),
    (re.compile(r"co-authored-by:\s*.*chatgpt", re.IGNORECASE), "ChatGPT"),
    (re.compile(r"co-authored-by:\s*.*codeium", re.IGNORECASE), "Codeium"),
]

FREE_TEXT_AI_PATTERNS = [
    (re.compile(r"\bgenerated (with|by|using)\b.*\b(ai|gpt|claude|copilot|llm)\b", re.IGNORECASE), "generic AI-generated phrasing"),
    (re.compile(r"\bchatgpt\b", re.IGNORECASE), "ChatGPT mention"),
    (re.compile(r"\bclaude\b", re.IGNORECASE), "Claude mention"),
    (re.compile(r"\bcopilot\b", re.IGNORECASE), "Copilot mention"),
    (re.compile(r"\bcursor\b", re.IGNORECASE), "Cursor mention"),
    (re.compile(r"\bgithub actions? bot\b", re.IGNORECASE), None),
]

FREE_TEXT_EXCLUDE_IF_MATCHES = [
    re.compile(r"\bcursor\b.*\b(css|pointer|mouse)\b", re.IGNORECASE),
]


def _run_git(repo_path: str, args: list) -> str:
    result = subprocess.run(
        ["git", "-C", repo_path] + args,
        capture_output=True,
        text=True,
        encoding="utf-8",
        errors="replace",
    )
    if result.returncode != 0:
        raise RuntimeError(f"git command failed: git {' '.join(args)}\n{result.stderr}")
    return result.stdout


COMMIT_SEP = "\x1e"
FIELD_SEP = "\x1f"


def fetch_commit_messages(repo_path: str) -> list[dict]:
    """Pulls commit hash, author, date, and FULL commit message (subject + body) for every commit."""
    log_format = f"{COMMIT_SEP}%H{FIELD_SEP}%an{FIELD_SEP}%aI{FIELD_SEP}%B"
    raw = _run_git(repo_path, ["log", f"--pretty=format:{log_format}", "--no-merges"])

    commits = []
    chunks = raw.split(COMMIT_SEP)
    for chunk in chunks:
        chunk = chunk.strip("\n")
        if not chunk:
            continue
        parts = chunk.split(FIELD_SEP, 3)
        if len(parts) != 4:
            continue
        commit_hash, author, date_iso, message = parts
        commits.append({"hash": commit_hash, "author": author, "date": date_iso, "message": message})

    return commits


def check_coauthor_signals(message: str) -> list[str]:
    """Returns list of tool names matched via Co-authored-by trailers in this commit message."""
    matches = []
    for pattern, tool_name in COAUTHOR_AI_PATTERNS:
        if pattern.search(message):
            matches.append(tool_name)
    return matches


def check_free_text_signals(text: str) -> list[str]:
    """Returns list of weak free-text AI mentions, with known false-positive patterns excluded."""
    for exclude_pattern in FREE_TEXT_EXCLUDE_IF_MATCHES:
        if exclude_pattern.search(text):
            return []

    matches = []
    for pattern, label in FREE_TEXT_AI_PATTERNS:
        if label and pattern.search(text):
            matches.append(label)
    return matches


def analyze_commits(repo_path: str) -> dict:
    commits = fetch_commit_messages(repo_path)

    coauthor_hits = []
    free_text_hits = []
    tool_counts = defaultdict(int)

    for c in commits:
        coauthor_matches = check_coauthor_signals(c["message"])
        for tool in coauthor_matches:
            tool_counts[tool] += 1
            coauthor_hits.append(
                {"hash": c["hash"][:10], "author": c["author"], "date": c["date"], "tool": tool}
            )

        free_text_matches = check_free_text_signals(c["message"])
        for label in free_text_matches:
            free_text_hits.append(
                {"hash": c["hash"][:10], "author": c["author"], "date": c["date"], "match": label}
            )

    return {
        "total_commits_scanned": len(commits),
        "coauthor_signals": coauthor_hits,
        "free_text_signals": free_text_hits,
        "tool_mention_counts": dict(tool_counts),
    }


def analyze_prs(output_dir: str) -> dict | None:
    """
    Checks already-fetched PR data (from github_prs.py's JSON output) for
    bot/agent authors and free-text mentions in... well, github_prs.py's
    current output doesn't retain PR body text, only metadata, so this
    checks author logins against KNOWN_AI_BOT_LOGINS, which is the
    highest-confidence signal available and doesn't require any new API
    calls or schema changes to github_prs.py.
    """
    pr_payload = load_analyzer_output(output_dir, "github_prs")
    if not pr_payload or "data" not in pr_payload:
        return None

    prs = pr_payload["data"].get("prs", [])
    bot_authored = [p for p in prs if (p.get("author") or "").lower() in [b.lower() for b in KNOWN_AI_BOT_LOGINS]]

    tool_counts = defaultdict(int)
    for p in bot_authored:
        tool_counts[p["author"]] += 1

    return {
        "total_prs_checked": len(prs),
        "ai_agent_authored_prs": [
            {"number": p["number"], "author": p["author"], "created_at": p["created_at"], "merged": p["merged"]}
            for p in bot_authored
        ],
        "agent_pr_counts": dict(tool_counts),
    }


def analyze(repo_path: str, output_dir: str) -> dict:
    commit_signals = analyze_commits(repo_path)
    pr_signals = analyze_prs(output_dir)

    high_confidence_count = len(pr_signals["ai_agent_authored_prs"]) if pr_signals else 0
    medium_confidence_count = len(commit_signals["coauthor_signals"])
    low_confidence_count = len(commit_signals["free_text_signals"])

    any_disclosed_usage = (high_confidence_count + medium_confidence_count) > 0

    tools_detected = set()
    if pr_signals:
        tools_detected.update(pr_signals["agent_pr_counts"].keys())
    tools_detected.update(commit_signals["tool_mention_counts"].keys())

    return {
        "methodology_notice": (
            "This analysis detects DISCLOSED or tool-inserted signals of AI usage only. "
            "It cannot measure actual AI usage: a developer may use AI tools without any "
            "visible trace, and a free-text mention does not confirm a tool was actually "
            "used for that change. Findings are grouped by confidence level — high "
            "(literal bot/agent authorship), medium (tool-inserted commit trailers), and "
            "low (free-text keyword mentions) — and should be read accordingly."
        ),
        "summary": {
            "any_disclosed_ai_usage_detected": any_disclosed_usage,
            "high_confidence_signals": high_confidence_count,
            "medium_confidence_signals": medium_confidence_count,
            "low_confidence_signals": low_confidence_count,
            "distinct_tools_detected": sorted(tools_detected),
            "pr_data_available": pr_signals is not None,
        },
        "pr_level_signals": pr_signals,
        "commit_level_signals": commit_signals,
    }


def run(repo_path: str, output_dir: str) -> dict:
    """Entry point used by orchestrator.py (direct function call, no subprocess)."""
    data = analyze(repo_path, output_dir)
    payload = make_output("ai_usage", repo_path, data)
    write_analyzer_output(output_dir, "ai_usage", payload)
    return payload


def main():
    parser = argparse.ArgumentParser(
        description="Detect disclosed/visible AI tool usage signals in commit history and PRs."
    )
    add_local_repo_arg(parser)
    add_output_arg(parser)
    args = parser.parse_args()
    run(args.repo_path, args.output)


if __name__ == "__main__":
    main()