"""
analyzers/github_prs.py

Pulls pull-request and review data from the GitHub API for a given repo
and computes the PR-health metrics called for in the Repodive Report
template (Development Activity > Pull Requests):

  - PRs created/merged over time
  - % authored by bots
  - time-to-merge (median/average)
  - self-merge rate (merged with 0 reviews)
  - PR size distribution (XS/S/M/L/XL)
  - per-contributor breakdown

This is a direct port of the old pr-metrics-analyzer.js logic, but it
fetches PRs + reviews itself via the GitHub REST API instead of expecting
pre-exported pr-metrics.json / pr-reviews.jsonl files.

Runs standalone:
    python analyzers/github_prs.py --github-repo DSACMS/repodive-tools --output ./output/json

Or imported by orchestrator.py via `run(github_repo, output_dir)`.
"""

import argparse
import re
import sys
import time
from pathlib import Path

import requests

# Allow running this file directly (python analyzers/github_prs.py) as well
# as importing it from orchestrator.py at the project root.
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
        # be polite between pages
        time.sleep(0.1)

    return results


def is_bot(login: str, is_bot_flag: bool) -> bool:
    if is_bot_flag:
        return True
    return bool(re.search(r"\[bot\]$", login or "", re.IGNORECASE)) or (login or "").startswith("app/")


def fetch_prs(github_repo: str, headers: dict, max_prs: int | None = None) -> list:
    """Fetches closed + open PRs (state=all), newest first."""
    url = f"{GITHUB_API}/repos/{github_repo}/pulls"
    params = {"state": "all", "sort": "created", "direction": "desc"}
    prs = _get_paginated(url, headers, params)
    if max_prs:
        prs = prs[:max_prs]
    return prs


def fetch_reviews_for_pr(github_repo: str, pr_number: int, headers: dict) -> list:
    url = f"{GITHUB_API}/repos/{github_repo}/pulls/{pr_number}/reviews"
    resp = requests.get(url, headers=headers, params={"per_page": PER_PAGE})
    if resp.status_code == 200:
        return resp.json()
    return []


def bucket_size(size: int) -> str:
    if size < 10:
        return "XS (<10)"
    if size < 100:
        return "S (10-99)"
    if size < 500:
        return "M (100-499)"
    if size < 1000:
        return "L (500-999)"
    return "XL (1000+)"


def analyze(github_repo: str, max_prs: int | None = None) -> dict:
    headers = github_auth_headers()

    print(f"[info] fetching PRs for {github_repo} ...")
    raw_prs = fetch_prs(github_repo, headers, max_prs=max_prs)
    print(f"[info] fetched {len(raw_prs)} PRs, fetching reviews for each ...")

    enriched = []
    for i, pr in enumerate(raw_prs):
        login = (pr.get("user") or {}).get("login", "unknown")
        bot = is_bot(login, False)
        additions = pr.get("additions")  # NOTE: list endpoint doesn't include additions/deletions
        deletions = pr.get("deletions")

        # The /pulls list endpoint doesn't return additions/deletions or merged_at
        # reliably for all cases, so fetch the single-PR endpoint for size + merge info.
        detail_resp = requests.get(
            f"{GITHUB_API}/repos/{github_repo}/pulls/{pr['number']}", headers=headers
        )
        detail = detail_resp.json() if detail_resp.status_code == 200 else {}
        additions = detail.get("additions", 0) or 0
        deletions = detail.get("deletions", 0) or 0
        merged_at = detail.get("merged_at")
        created_at = pr.get("created_at")

        reviews = fetch_reviews_for_pr(github_repo, pr["number"], headers)
        review_count = len(reviews)
        reviewers = {
            (r.get("user") or {}).get("login")
            for r in reviews
            if (r.get("user") or {}).get("login")
        }

        size = additions + deletions
        self_merge = review_count == 0 and bool(merged_at)
        ttm_days = days_between(created_at, merged_at)

        enriched.append(
            {
                "number": pr["number"],
                "author": login,
                "is_bot": bot,
                "created_at": created_at,
                "merged_at": merged_at,
                "merged": bool(merged_at),
                "additions": additions,
                "deletions": deletions,
                "size": size,
                "review_count": review_count,
                "unique_reviewers": len(reviewers),
                "self_merge": self_merge,
                "time_to_merge_days": round(ttm_days, 2) if ttm_days is not None else None,
            }
        )

        if (i + 1) % 25 == 0:
            print(f"[info]   processed {i + 1}/{len(raw_prs)} PRs")

    human_prs = [p for p in enriched if not p["is_bot"]]
    merged_human_prs = [p for p in human_prs if p["merged"]]

    ttm_values = [p["time_to_merge_days"] for p in merged_human_prs if p["time_to_merge_days"] is not None]
    size_values = [p["size"] for p in human_prs]
    self_merge_count = sum(1 for p in merged_human_prs if p["self_merge"])
    no_review_count = sum(1 for p in merged_human_prs if p["review_count"] == 0)

    buckets = {"XS (<10)": 0, "S (10-99)": 0, "M (100-499)": 0, "L (500-999)": 0, "XL (1000+)": 0}
    for p in human_prs:
        buckets[bucket_size(p["size"])] += 1

    by_author = {}
    for p in human_prs:
        a = by_author.setdefault(
            p["author"],
            {"pr_count": 0, "merged_count": 0, "self_merge_count": 0, "total_additions": 0, "total_deletions": 0},
        )
        a["pr_count"] += 1
        if p["merged"]:
            a["merged_count"] += 1
        if p["self_merge"]:
            a["self_merge_count"] += 1
        a["total_additions"] += p["additions"]
        a["total_deletions"] += p["deletions"]

    contributor_rows = []
    for author, v in by_author.items():
        self_merge_rate = (
            round((v["self_merge_count"] / v["merged_count"]) * 100, 1) if v["merged_count"] > 0 else None
        )
        contributor_rows.append({"author": author, **v, "self_merge_rate_pct": self_merge_rate})
    contributor_rows.sort(key=lambda r: r["pr_count"], reverse=True)

    monthly = {}
    for p in human_prs:
        created_month = (p["created_at"] or "")[:7] or None
        merged_month = (p["merged_at"] or "")[:7] or None
        if created_month:
            monthly.setdefault(created_month, {"opened": 0, "merged": 0})["opened"] += 1
        if merged_month:
            monthly.setdefault(merged_month, {"opened": 0, "merged": 0})["merged"] += 1
    monthly_rows = [{"month": m, **v} for m, v in sorted(monthly.items())]

    bot_count = len(enriched) - len(human_prs)

    return {
        "summary": {
            "total_prs_fetched": len(enriched),
            "human_prs": len(human_prs),
            "bot_prs": bot_count,
            "bot_pct": round((bot_count / len(enriched)) * 100, 1) if enriched else None,
            "merged_human_prs": len(merged_human_prs),
            "median_time_to_merge_days": round(median(ttm_values), 2) if ttm_values else None,
            "average_time_to_merge_days": round(average(ttm_values), 2) if ttm_values else None,
            "median_pr_size": round(median(size_values)) if size_values else None,
            "average_pr_size": round(average(size_values)) if size_values else None,
            "self_merge_count": self_merge_count,
            "self_merge_pct": (
                round((self_merge_count / len(merged_human_prs)) * 100, 1) if merged_human_prs else None
            ),
            "merged_with_zero_reviews_count": no_review_count,
            "merged_with_zero_reviews_pct": (
                round((no_review_count / len(merged_human_prs)) * 100, 1) if merged_human_prs else None
            ),
        },
        "size_distribution": buckets,
        "monthly_cadence": monthly_rows,
        "contributors": contributor_rows,
        "prs": enriched,
    }


def run(github_repo: str, output_dir: str, max_prs: int | None = None) -> dict:
    """Entry point used by orchestrator.py (direct function call, no subprocess)."""
    data = analyze(github_repo, max_prs=max_prs)
    payload = make_output("github_prs", github_repo, data)
    write_analyzer_output(output_dir, "github_prs", payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Analyze GitHub PR health metrics for a repo.")
    add_github_repo_arg(parser)
    add_output_arg(parser)
    parser.add_argument(
        "--max-prs",
        type=int,
        default=None,
        help="Optional cap on number of PRs to fetch (useful for quick testing on large repos).",
    )
    args = parser.parse_args()
    run(args.github_repo, args.output, max_prs=args.max_prs)


if __name__ == "__main__":
    main()