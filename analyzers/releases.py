"""
analyzers/releases.py

Pulls tag/release data from the GitHub API for a given repo and computes
the release cadence metrics called for in the Repodive Report template
(Development Activity > Releases):

  - Release cadence — look at tags/releases for a consistent, intentional
    rhythm rather than irregular or absent versioning.

Design notes:
  - Uses GitHub's /releases endpoint (formal Releases, which have titles,
    notes, published_at) rather than /tags (which are just git refs with
    no publish date or notes). Most CMS-style repos following semver and
    using GitHub Releases properly will have both; if a repo only uses
    raw tags without ever publishing a Release, this analyzer will
    correctly report "no releases found" and the report should recommend
    adopting GitHub Releases for visibility.
  - "Consistent rhythm" is operationalized as: the coefficient of
    variation (stddev / mean) of the gaps between consecutive releases.
    Lower CV = more regular cadence; higher CV = irregular/bursty.
    This is a standard way to quantify "how consistent are these
    intervals" without just eyeballing a list of dates.
  - Semver parsing is best-effort (handles common "v1.2.3" / "1.2.3"
    patterns) so we can flag major vs. minor vs. patch releases
    separately, which is useful context for cadence (frequent patches +
    rare majors is a very different story than frequent majors).

Runs standalone:
    python analyzers/releases.py --github-repo DSACMS/repodive-tools --output ./output/json

Or imported by orchestrator.py via `run(github_repo, output_dir)`.
"""

import argparse
import re
import statistics
import sys
import time
from pathlib import Path

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

SEMVER_PATTERN = re.compile(r"v?(\d+)\.(\d+)\.(\d+)")


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


def fetch_releases(github_repo: str, headers: dict) -> list:
    """Fetches formal GitHub Releases (not raw tags), newest first by default."""
    url = f"{GITHUB_API}/repos/{github_repo}/releases"
    return _get_paginated(url, headers)


def fetch_tags(github_repo: str, headers: dict) -> list:
    """
    Fetches raw git tags as a fallback/supplement. Tags have no publish
    date via this endpoint directly (would require a follow-up commit
    lookup per tag), so we only use this to report "tags exist but no
    formal Releases were published" as a hygiene note, not for cadence math.
    """
    url = f"{GITHUB_API}/repos/{github_repo}/tags"
    return _get_paginated(url, headers)


def classify_semver_bump(prev_version: tuple | None, curr_version: tuple | None) -> str | None:
    """Classifies a release as major/minor/patch based on semver diff from the previous release."""
    if prev_version is None or curr_version is None:
        return None
    if curr_version[0] != prev_version[0]:
        return "major"
    if curr_version[1] != prev_version[1]:
        return "minor"
    if curr_version[2] != prev_version[2]:
        return "patch"
    return "none"


def parse_semver(tag_name: str) -> tuple | None:
    match = SEMVER_PATTERN.search(tag_name or "")
    if not match:
        return None
    return tuple(int(g) for g in match.groups())


def compute_cadence_stats(sorted_releases: list[dict]) -> dict:
    """
    Computes gap-between-releases statistics (in days) and a coefficient
    of variation to quantify how regular or irregular the release rhythm
    is. sorted_releases must be sorted oldest-first.
    """
    gaps = []
    for i in range(1, len(sorted_releases)):
        gap = days_between(sorted_releases[i - 1]["published_at"], sorted_releases[i]["published_at"])
        if gap is not None:
            gaps.append(gap)

    if not gaps:
        return {
            "gap_count": 0,
            "median_gap_days": None,
            "average_gap_days": None,
            "stddev_gap_days": None,
            "coefficient_of_variation": None,
            "cadence_assessment": "Not enough releases to assess cadence (need at least 2).",
        }

    med = median(gaps)
    avg = average(gaps)
    stddev = statistics.pstdev(gaps) if len(gaps) > 1 else 0.0
    cv = (stddev / avg) if avg else None

    if cv is None:
        assessment = "Not enough data."
    elif cv < 0.3:
        assessment = "Highly consistent — releases follow a regular, predictable rhythm."
    elif cv < 0.7:
        assessment = "Moderately consistent — some variation in release timing, but a general pattern exists."
    else:
        assessment = "Irregular — release timing is inconsistent, suggesting ad hoc rather than planned releases."

    return {
        "gap_count": len(gaps),
        "median_gap_days": round(med, 1) if med is not None else None,
        "average_gap_days": round(avg, 1) if avg is not None else None,
        "stddev_gap_days": round(stddev, 1),
        "coefficient_of_variation": round(cv, 2) if cv is not None else None,
        "cadence_assessment": assessment,
    }


def analyze(github_repo: str) -> dict:
    headers = github_auth_headers()

    print(f"[info] fetching releases for {github_repo} ...")
    raw_releases = fetch_releases(github_repo, headers)
    print(f"[info] fetched {len(raw_releases)} releases")

    raw_tags = fetch_tags(github_repo, headers)

    enriched = []
    for r in raw_releases:
        enriched.append(
            {
                "tag_name": r.get("tag_name"),
                "name": r.get("name") or r.get("tag_name"),
                "published_at": r.get("published_at"),
                "created_at": r.get("created_at"),
                "is_prerelease": r.get("prerelease", False),
                "is_draft": r.get("draft", False),
                "author": (r.get("author") or {}).get("login", "unknown"),
                "semver": parse_semver(r.get("tag_name")),
            }
        )

    # Exclude drafts from cadence math (they aren't actually published) but
    # keep them in the raw list for visibility.
    published = [r for r in enriched if not r["is_draft"] and r["published_at"]]
    published_sorted = sorted(published, key=lambda r: r["published_at"])

    # classify version bump type release-over-release
    for i, r in enumerate(published_sorted):
        prev_semver = published_sorted[i - 1]["semver"] if i > 0 else None
        r["bump_type"] = classify_semver_bump(prev_semver, r["semver"])

    cadence = compute_cadence_stats(published_sorted)

    bump_counts = {"major": 0, "minor": 0, "patch": 0, "none": 0, "unparseable": 0}
    for r in published_sorted:
        if r["bump_type"] is None:
            bump_counts["unparseable"] += 1
        else:
            bump_counts[r["bump_type"]] += 1

    prerelease_count = sum(1 for r in enriched if r["is_prerelease"])

    return {
        "summary": {
            "total_releases": len(enriched),
            "published_releases": len(published),
            "draft_releases": sum(1 for r in enriched if r["is_draft"]),
            "prerelease_count": prerelease_count,
            "raw_tag_count": len(raw_tags),
            "tags_without_formal_releases": max(0, len(raw_tags) - len(enriched)),
            "first_release": published_sorted[0]["published_at"] if published_sorted else None,
            "latest_release": published_sorted[-1]["published_at"] if published_sorted else None,
        },
        "cadence": cadence,
        "version_bump_breakdown": bump_counts,
        "releases": list(reversed(published_sorted)),  # newest-first for display
    }


def run(github_repo: str, output_dir: str) -> dict:
    """Entry point used by orchestrator.py (direct function call, no subprocess)."""
    data = analyze(github_repo)
    payload = make_output("releases", github_repo, data)
    write_analyzer_output(output_dir, "releases", payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Analyze GitHub release cadence for a repo.")
    add_github_repo_arg(parser)
    add_output_arg(parser)
    args = parser.parse_args()
    run(args.github_repo, args.output)


if __name__ == "__main__":
    main()