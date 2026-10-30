"""
config.py

Shared configuration and helpers for all repodive analyzer scripts.
Every analyzer imports from here so paths, JSON contract, and GitHub
auth handling stay consistent across the whole toolkit.
"""

import os
import json
import sys
from datetime import datetime, timezone
from pathlib import Path


# ---------------------------------------------------------------------------
# GitHub auth
# ---------------------------------------------------------------------------

def get_github_token():
    """
    Returns a GitHub token from the GITHUB_TOKEN environment variable, or
    None if unset. Scripts should work without a token (unauthenticated,
    60 req/hr) but will be much faster and safer against rate limits with
    one set (5000 req/hr).

    To set it:
        export GITHUB_TOKEN=ghp_xxxxxxxxxxxx
    """
    token = os.environ.get("GITHUB_TOKEN")
    if not token:
        print(
            "[warn] GITHUB_TOKEN not set. Proceeding unauthenticated "
            "(60 requests/hour limit). Set GITHUB_TOKEN to avoid rate-limit "
            "failures on larger repos.",
            file=sys.stderr,
        )
    return token


def github_auth_headers():
    """Returns the Authorization header dict to pass to requests, or {} if no token."""
    token = get_github_token()
    if token:
        return {
            "Authorization": f"Bearer {token}",
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
    return {"Accept": "application/vnd.github+json"}


# ---------------------------------------------------------------------------
# JSON output contract
# ---------------------------------------------------------------------------
#
# Every analyzer should produce a dict shaped like this and pass it to
# write_analyzer_output(). This keeps the orchestrator's job trivial: it
# just loads every JSON file in the output dir and feeds `data` into the
# markdown template under a key matching `analyzer`.

def make_output(analyzer_name: str, repository: str, data: dict) -> dict:
    """Wraps analyzer results in the standard repodive JSON envelope."""
    return {
        "analyzer": analyzer_name,
        "repository": repository,
        "generated_at": datetime.now(timezone.utc).isoformat(),
        "data": data,
    }


def write_analyzer_output(output_dir: str, analyzer_name: str, payload: dict) -> Path:
    """
    Writes an analyzer's output dict to <output_dir>/<analyzer_name>.json.
    Returns the path written, for logging/confirmation.
    """
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)
    file_path = out_path / f"{analyzer_name}.json"
    with open(file_path, "w", encoding="utf-8") as f:
        json.dump(payload, f, indent=2, default=str)
    print(f"[ok] wrote {file_path}")
    return file_path


def load_analyzer_output(output_dir: str, analyzer_name: str) -> dict | None:
    """
    Loads a previously-written analyzer JSON file, if it exists.
    Returns None if the file isn't there yet (e.g. that analyzer hasn't
    been run), so the orchestrator/template can render a "not available"
    placeholder instead of crashing.
    """
    file_path = Path(output_dir) / f"{analyzer_name}.json"
    if not file_path.exists():
        return None
    with open(file_path, "r", encoding="utf-8") as f:
        return json.load(f)


# ---------------------------------------------------------------------------
# Common CLI argument helpers
# ---------------------------------------------------------------------------
#
# Analyzers fall into two camps:
#   - "local" analyzers operate on a cloned repo on disk (--repo-path)
#   - "github" analyzers hit the GitHub API (--github-repo org/name)
# Some (like releases) may want both. These helpers keep argparse setup
# consistent and short in every script.

def add_local_repo_arg(parser):
    parser.add_argument(
        "--repo-path",
        required=True,
        help="Path to the locally cloned repository to analyze.",
    )


def add_github_repo_arg(parser):
    parser.add_argument(
        "--github-repo",
        required=True,
        help="GitHub repo in 'org/name' format, e.g. DSACMS/repodive-tools",
    )


def add_output_arg(parser, default="./output/json"):
    parser.add_argument(
        "--output",
        default=default,
        help=f"Directory to write this analyzer's JSON output (default: {default})",
    )


# ---------------------------------------------------------------------------
# Misc shared utilities
# ---------------------------------------------------------------------------

def days_between(iso_a: str | None, iso_b: str | None) -> float | None:
    """Returns the number of days between two ISO8601 timestamps, or None if either is missing."""
    if not iso_a or not iso_b:
        return None
    fmt_a = datetime.fromisoformat(iso_a.replace("Z", "+00:00"))
    fmt_b = datetime.fromisoformat(iso_b.replace("Z", "+00:00"))
    return (fmt_b - fmt_a).total_seconds() / 86400.0


def median(values: list[float]) -> float | None:
    if not values:
        return None
    s = sorted(values)
    n = len(s)
    mid = n // 2
    return s[mid] if n % 2 else (s[mid - 1] + s[mid]) / 2


def average(values: list[float]) -> float | None:
    if not values:
        return None
    return sum(values) / len(values)