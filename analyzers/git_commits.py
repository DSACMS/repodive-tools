"""
analyzers/git_commits.py

Analyzes commit history from a LOCAL git clone (no GitHub API calls —
everything here comes from `git log`). Covers the Repodive Report
template sections:

  Development Activity > Commits
    - commit frequency / distribution over time
    - spikes right before releases vs. steady activity
  Development Activity > Bus Factor
    - knowledge concentration (% of commits/lines by top contributor(s))
    - activity consistency (steady vs. bursty per-contributor patterns)

Design notes:
  - Uses `git log` with a custom format + NUL-byte separators so we can
    safely parse commit messages/author names containing commas, quotes,
    pipes, etc. without a CSV-style parser.
  - Computes per-contributor commit counts AND line churn (insertions +
    deletions) via `--numstat`, since "bus factor" is more meaningful when
    weighted by how much code someone touched, not just commit counts.
  - Bus factor itself is reported two ways: simple (top-contributor %)
    and a basic "N contributors to reach 50%/80% of commits" count, which
    is a common informal bus-factor heuristic.

Runs standalone:
    python analyzers/git_commits.py --repo-path ./cloned-repos/repodive-tools --output ./output/json

Or imported by orchestrator.py via `run(repo_path, output_dir)`.
"""

import argparse
import subprocess
import sys
from collections import defaultdict
from datetime import datetime
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import (
    make_output,
    write_analyzer_output,
    add_local_repo_arg,
    add_output_arg,
    median,
    average,
)

FIELD_SEP = "\x1f"
COMMIT_SEP = "\x1e"


def _run_git(repo_path: str, args: list) -> str:
    """Runs a git command in repo_path and returns stdout as text. Raises on failure."""
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


def verify_git_repo(repo_path: str):
    """Confirms repo_path is actually a git repository before we try to parse anything."""
    p = Path(repo_path)
    if not p.exists():
        raise FileNotFoundError(f"Path does not exist: {repo_path}")
    git_dir = p / ".git"
    if not git_dir.exists():
        raise RuntimeError(
            f"{repo_path} does not look like a git repository (no .git directory found)."
        )


def fetch_commit_log(repo_path: str) -> list[dict]:
    """
    Pulls full commit history with author, date, and numstat (lines added/removed
    per file) for every commit. Returns a list of commit dicts:
        {
            "hash": str,
            "author_name": str,
            "author_email": str,
            "date": str (ISO8601),
            "insertions": int,
            "deletions": int,
            "files_changed": int,
        }
    """
    log_format = f"{COMMIT_SEP}%H{FIELD_SEP}%an{FIELD_SEP}%ae{FIELD_SEP}%aI"
    raw = _run_git(
        repo_path,
        ["log", f"--pretty=format:{log_format}", "--numstat", "--no-merges"],
    )

    commits = []
    chunks = raw.split(COMMIT_SEP)
    for chunk in chunks:
        chunk = chunk.strip("\n")
        if not chunk:
            continue

        lines = chunk.split("\n")
        header = lines[0]
        parts = header.split(FIELD_SEP)
        if len(parts) != 4:
            continue 
        commit_hash, author_name, author_email, date_iso = parts

        insertions = 0
        deletions = 0
        files_changed = 0
        for stat_line in lines[1:]:
            stat_line = stat_line.strip()
            if not stat_line:
                continue
            stat_parts = stat_line.split("\t")
            if len(stat_parts) < 3:
                continue
            added, removed, _path = stat_parts[0], stat_parts[1], stat_parts[2]
            files_changed += 1
            if added.isdigit():
                insertions += int(added)
            if removed.isdigit():
                deletions += int(removed)

        commits.append(
            {
                "hash": commit_hash,
                "author_name": author_name,
                "author_email": author_email,
                "date": date_iso,
                "insertions": insertions,
                "deletions": deletions,
                "files_changed": files_changed,
            }
        )

    return commits


def compute_monthly_distribution(commits: list[dict]) -> list[dict]:
    """Returns commit counts per calendar month, sorted chronologically."""
    monthly = defaultdict(int)
    for c in commits:
        month = c["date"][:7]
        monthly[month] += 1
    return [{"month": m, "commits": n} for m, n in sorted(monthly.items())]


def detect_activity_spikes(monthly: list[dict], spike_multiplier: float = 2.0) -> list[dict]:
    """
    Flags months where commit volume is `spike_multiplier`x+ the trailing
    3-month average — a simple heuristic for "last-minute crunch before
    release" patterns called out in the template.
    """
    spikes = []
    counts = [m["commits"] for m in monthly]
    for i in range(3, len(monthly)):
        trailing_avg = average(counts[i - 3 : i])
        if trailing_avg and counts[i] >= trailing_avg * spike_multiplier:
            spikes.append(
                {
                    "month": monthly[i]["month"],
                    "commits": counts[i],
                    "trailing_3mo_avg": round(trailing_avg, 1),
                    "multiplier": round(counts[i] / trailing_avg, 1),
                }
            )
    return spikes


def compute_contributor_stats(commits: list[dict]) -> list[dict]:
    """Aggregates commit count and line churn per contributor (grouped by email)."""
    by_author = defaultdict(
        lambda: {"name": None, "email": None, "commits": 0, "insertions": 0, "deletions": 0, "first_commit": None, "last_commit": None}
    )

    for c in commits:
        key = c["author_email"] or c["author_name"]
        a = by_author[key]
        a["name"] = c["author_name"]
        a["email"] = c["author_email"]
        a["commits"] += 1
        a["insertions"] += c["insertions"]
        a["deletions"] += c["deletions"]
        date = c["date"]
        if a["first_commit"] is None or date < a["first_commit"]:
            a["first_commit"] = date
        if a["last_commit"] is None or date > a["last_commit"]:
            a["last_commit"] = date

    rows = list(by_author.values())
    for r in rows:
        r["total_churn"] = r["insertions"] + r["deletions"]
    rows.sort(key=lambda r: r["commits"], reverse=True)
    return rows


def compute_bus_factor(contributors: list[dict], total_commits: int) -> dict:
    """
    Two bus-factor views:
      - top_contributor_pct: what % of all commits the single most active
        person made (high = concentrated risk)
      - contributors_to_50pct / contributors_to_80pct: how many people,
        starting from the most active, are needed to account for 50%/80%
        of all commits (low number = concentrated risk)
    """
    if not contributors or total_commits == 0:
        return {
            "top_contributor_pct": None,
            "contributors_to_50pct": None,
            "contributors_to_80pct": None,
            "total_contributors": 0,
        }

    top_pct = round((contributors[0]["commits"] / total_commits) * 100, 1)

    running = 0
    to_50, to_80 = None, None
    for i, c in enumerate(contributors):
        running += c["commits"]
        pct = running / total_commits
        if to_50 is None and pct >= 0.5:
            to_50 = i + 1
        if to_80 is None and pct >= 0.8:
            to_80 = i + 1
            break

    return {
        "top_contributor_pct": top_pct,
        "contributors_to_50pct": to_50,
        "contributors_to_80pct": to_80,
        "total_contributors": len(contributors),
    }


def compute_activity_consistency(contributors: list[dict], commits: list[dict]) -> list[dict]:
    """
    For each of the top 10 contributors, computes the number of distinct
    months they committed in, vs. the span of months between their first
    and last commit — a rough "steady vs. bursty" signal. A ratio close to
    1.0 means they commit almost every month they're active; a low ratio
    means long gaps punctuated by bursts.
    """
    commits_by_author = defaultdict(list)
    for c in commits:
        key = c["author_email"] or c["author_name"]
        commits_by_author[key].append(c["date"][:7])

    results = []
    for c in contributors[:10]:
        key = c["email"] or c["name"]
        months_active = sorted(set(commits_by_author[key]))
        if not months_active:
            continue

        first = datetime.strptime(months_active[0], "%Y-%m")
        last = datetime.strptime(months_active[-1], "%Y-%m")
        span_months = (last.year - first.year) * 12 + (last.month - first.month) + 1
        consistency_ratio = round(len(months_active) / span_months, 2) if span_months > 0 else None

        results.append(
            {
                "author": c["name"],
                "distinct_months_active": len(months_active),
                "span_months": span_months,
                "consistency_ratio": consistency_ratio,
            }
        )

    return results


def analyze(repo_path: str) -> dict:
    verify_git_repo(repo_path)

    print(f"[info] reading git log for {repo_path} ...")
    commits = fetch_commit_log(repo_path)
    print(f"[info] parsed {len(commits)} commits")

    monthly = compute_monthly_distribution(commits)
    spikes = detect_activity_spikes(monthly)
    contributors = compute_contributor_stats(commits)
    bus_factor = compute_bus_factor(contributors, len(commits))
    consistency = compute_activity_consistency(contributors, commits)

    dates = [c["date"] for c in commits]
    repo_first_commit = min(dates) if dates else None
    repo_last_commit = max(dates) if dates else None

    return {
        "summary": {
            "total_commits": len(commits),
            "total_contributors": len(contributors),
            "first_commit": repo_first_commit,
            "last_commit": repo_last_commit,
        },
        "monthly_distribution": monthly,
        "activity_spikes": spikes,
        "bus_factor": bus_factor,
        "contributors": contributors[:25],
        "activity_consistency": consistency,
    }


def run(repo_path: str, output_dir: str) -> dict:
    """Entry point used by orchestrator.py (direct function call, no subprocess)."""
    data = analyze(repo_path)
    payload = make_output("git_commits", repo_path, data)
    write_analyzer_output(output_dir, "git_commits", payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Analyze local git commit history, bus factor, and activity patterns.")
    add_local_repo_arg(parser)
    add_output_arg(parser)
    args = parser.parse_args()
    run(args.repo_path, args.output)


if __name__ == "__main__":
    main()