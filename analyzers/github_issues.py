"""
analyzers/github_issues.py

Pulls issue data from the GitHub API for a given repo and computes the
issue-tracking health metrics called for in the Repodive Report template
(Development Activity > Issues):

  - Are issues being opened, triaged, and closed at a reasonable pace?
  - A growing backlog of stale, unlabeled issues suggests weak process
    discipline.

Design notes:
  - GitHub's /issues endpoint returns BOTH issues and PRs (a PR is
    internally an issue with a `pull_request` key present). We filter
    those out here so this analyzer is issues-only; PR data already has
    its own analyzer (github_prs.py).
  - "Triaged" is approximated as "has at least one label" — GitHub has no
    universal formal triage concept, so label presence is the most common
    practical proxy or org-level conventions, and it's stated explicitly
    in the output/report as an approximation.
  - "Stale" is defined as open AND no activity (comments/updates) in the
    last N days (default 90, configurable via --stale-days), a common
    convention for repo-health bots like GitHub's own stale-bot default.
  - Time-to-close uses created_at -> closed_at, matching the pattern used
    in github_prs.py's time-to-merge calculation for consistency.

Runs standalone:
    python analyzers/github_issues.py --github-repo DSACMS/repodive-tools --output ./output/json

Or imported by orchestrator.py via `run(github_repo, output_dir)`.
"""

import argparse
import sys
import time
from pathlib import Path
from datetime import datetime, timezone

import requests

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import (
    github_auth_headers,
    make_output,
    write_analyzer_output,
    add_github_repo_arg,
    add_output_arg,
    days_between,
    median,
    average,
)

GITHUB_API = "https://api.github.com"
PER_PAGE = 100
DEFAULT_STALE_DAYS = 90


def _get_paginated(url: str, headers: dict, params: dict | None = None) -> list:
    """Follows GitHub's Link-header pagination and returns the full combined list."""
    results = []
    params = dict(params or {})
    params["per_page"] = PER_PAGE
    next_url = url

    while next_url:
        resp = requests.get(next_url, headers=headers, params=params if next_url == url else None)

        if resp.status_code == 403 and "rate limit" in resp.text.lower():
            reset = resp.headers.get("X-RateLimit-Reset")
            print(
                f"[error] GitHub rate limit hit. Resets at epoch {reset}. "
                f"Set GITHUB_TOKEN to raise your limit to 5000/hr.",
                file=sys.stderr,
            )
            break

        resp.raise_for_status()
        results.extend(resp.json())

        next_url = None
        link_header = resp.headers.get("Link", "")
        for part in link_header.split(","):
            if 'rel="next"' in part:
                next_url = part[part.find("<") + 1 : part.find(">")]
        time.sleep(0.1)

    return results


def fetch_issues(github_repo: str, headers: dict, max_issues: int | None = None) -> list:
    """
    Fetches issues (state=all). GitHub's /issues endpoint includes PRs;
    we filter those out immediately since this analyzer is issues-only.
    """
    url = f"{GITHUB_API}/repos/{github_repo}/issues"
    params = {"state": "all", "sort": "created", "direction": "desc"}
    raw = _get_paginated(url, headers, params)

    issues_only = [item for item in raw if "pull_request" not in item]

    if max_issues:
        issues_only = issues_only[:max_issues]

    return issues_only


def _is_stale(issue: dict, stale_days: int, now: datetime) -> bool:
    """An open issue is stale if its last update was more than stale_days ago."""
    if issue.get("state") != "open":
        return False
    updated_at = issue.get("updated_at")
    if not updated_at:
        return False
    updated = datetime.fromisoformat(updated_at.replace("Z", "+00:00"))
    age_days = (now - updated).total_seconds() / 86400.0
    return age_days > stale_days


def analyze(github_repo: str, stale_days: int = DEFAULT_STALE_DAYS, max_issues: int | None = None) -> dict:
    headers = github_auth_headers()
    now = datetime.now(timezone.utc)

    print(f"[info] fetching issues for {github_repo} ...")
    raw_issues = fetch_issues(github_repo, headers, max_issues=max_issues)
    print(f"[info] fetched {len(raw_issues)} issues (PRs excluded)")

    enriched = []
    for issue in raw_issues:
        login = (issue.get("user") or {}).get("login", "unknown")
        labels = [l.get("name") for l in (issue.get("labels") or []) if l.get("name")]
        created_at = issue.get("created_at")
        closed_at = issue.get("closed_at")
        state = issue.get("state")
        ttc_days = days_between(created_at, closed_at) if closed_at else None
        comments = issue.get("comments", 0)

        enriched.append(
            {
                "number": issue["number"],
                "author": login,
                "state": state,
                "created_at": created_at,
                "closed_at": closed_at,
                "updated_at": issue.get("updated_at"),
                "labels": labels,
                "is_triaged": len(labels) > 0,
                "comments": comments,
                "time_to_close_days": round(ttc_days, 2) if ttc_days is not None else None,
                "is_stale": _is_stale(issue, stale_days, now),
            }
        )

    open_issues = [i for i in enriched if i["state"] == "open"]
    closed_issues = [i for i in enriched if i["state"] == "closed"]
    stale_issues = [i for i in enriched if i["is_stale"]]
    untriaged_open = [i for i in open_issues if not i["is_triaged"]]

    ttc_values = [i["time_to_close_days"] for i in closed_issues if i["time_to_close_days"] is not None]

    monthly = {}
    for i in enriched:
        created_month = (i["created_at"] or "")[:7] or None
        closed_month = (i["closed_at"] or "")[:7] or None
        if created_month:
            monthly.setdefault(created_month, {"opened": 0, "closed": 0})["opened"] += 1
        if closed_month:
            monthly.setdefault(closed_month, {"opened": 0, "closed": 0})["closed"] += 1
    monthly_rows = [{"month": m, **v} for m, v in sorted(monthly.items())]

    # Simple backlog trend: cumulative (opened - closed) over time, to see
    # whether the backlog is growing, shrinking, or flat — directly
    # answers the template's "growing backlog" concern.
    running_backlog = 0
    backlog_trend = []
    for row in monthly_rows:
        running_backlog += row["opened"] - row["closed"]
        backlog_trend.append({"month": row["month"], "net_backlog": running_backlog})

    label_counts = {}
    for i in enriched:
        for label in i["labels"]:
            label_counts[label] = label_counts.get(label, 0) + 1
    top_labels = sorted(label_counts.items(), key=lambda kv: kv[1], reverse=True)[:15]

    return {
        "summary": {
            "total_issues": len(enriched),
            "open_issues": len(open_issues),
            "closed_issues": len(closed_issues),
            "stale_open_issues": len(stale_issues),
            "stale_days_threshold": stale_days,
            "untriaged_open_issues": len(untriaged_open),
            "untriaged_open_pct": (
                round((len(untriaged_open) / len(open_issues)) * 100, 1) if open_issues else None
            ),
            "median_time_to_close_days": round(median(ttc_values), 2) if ttc_values else None,
            "average_time_to_close_days": round(average(ttc_values), 2) if ttc_values else None,
            "current_net_backlog": running_backlog,
        },
        "monthly_cadence": monthly_rows,
        "backlog_trend": backlog_trend,
        "top_labels": [{"label": l, "count": c} for l, c in top_labels],
        "stale_issue_numbers": [i["number"] for i in stale_issues],
        "issues": enriched,
    }


def run(github_repo: str, output_dir: str, stale_days: int = DEFAULT_STALE_DAYS, max_issues: int | None = None) -> dict:
    """Entry point used by orchestrator.py (direct function call, no subprocess)."""
    data = analyze(github_repo, stale_days=stale_days, max_issues=max_issues)
    payload = make_output("github_issues", github_repo, data)
    write_analyzer_output(output_dir, "github_issues", payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Analyze GitHub issue tracking health for a repo.")
    add_github_repo_arg(parser)
    add_output_arg(parser)
    parser.add_argument(
        "--stale-days",
        type=int,
        default=DEFAULT_STALE_DAYS,
        help=f"Days of inactivity before an open issue is considered stale (default: {DEFAULT_STALE_DAYS}).",
    )
    parser.add_argument(
        "--max-issues",
        type=int,
        default=None,
        help="Optional cap on number of issues to fetch (useful for quick testing on large repos).",
    )
    args = parser.parse_args()
    run(args.github_repo, args.output, stale_days=args.stale_days, max_issues=args.max_issues)


if __name__ == "__main__":
    main()