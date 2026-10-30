"""
analyzers/hygiene.py

Checks a LOCAL git clone for the presence of standard repository hygiene
files called out in the Repodive Report template's "Repository Hygiene >
Documentation" table:

    README.md, CONTRIBUTING.md, SECURITY.md, LICENSE, .github/ISSUE_TEMPLATE.md,
    .github/PR_TEMPLATE.md, code.json, CHANGELOG.md, COMMUNITY.md,
    plus a docs/ directory check for things like a docker deployment guide.

This is intentionally a filesystem-only check — no GitHub API calls — since
everything the template's Documentation table asks for ("File Exists?")
is answerable from what's actually in the clone.

Design notes:
  - Filenames are matched case-insensitively and with common extension/
    naming variants (e.g. "LICENSE" vs "LICENSE.md" vs "LICENSE.txt",
    "SECURITY.md" vs ".github/SECURITY.md"), since GitHub itself accepts
    several locations/spellings for these files.
  - Issue/PR templates can be either a single file OR a directory of
    multiple templates (GitHub supports both); both are checked.
  - For each file we also report a short "notes" field flagging if it's
    present but suspiciously small (e.g. a 1-line stub), since the
    template explicitly wants recommendations, not just a checkbox.
  - A few template-recommended items (repo topics, repo description) live
    on GitHub itself, not in the local clone, so this analyzer flags them
    as "requires GitHub API / web check" rather than silently omitting
    them, keeping the Documentation table complete even when a field
    can't be answered locally.

Runs standalone:
    python analyzers/hygiene.py --repo-path ./cloned-repos/repodive-tools --output ./output/json

Or imported by orchestrator.py via `run(repo_path, output_dir)`.
"""

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import (
    make_output,
    write_analyzer_output,
    add_local_repo_arg,
    add_output_arg,
)

STUB_SIZE_THRESHOLD_BYTES = 50

DOCUMENTATION_CHECKS = [
    ("README.md", ["README.md", "README.rst", "README.txt", "README"]),
    ("CONTRIBUTING.md", ["CONTRIBUTING.md", ".github/CONTRIBUTING.md", "docs/CONTRIBUTING.md"]),
    ("SECURITY.md", ["SECURITY.md", ".github/SECURITY.md", "docs/SECURITY.md"]),
    ("LICENSE", ["LICENSE", "LICENSE.md", "LICENSE.txt", "LICENSE.rst", "COPYING"]),
    (
        ".github/ISSUE_TEMPLATE.md",
        [
            ".github/ISSUE_TEMPLATE.md",
            ".github/ISSUE_TEMPLATE",
            ".github/issue_template.md",
        ],
    ),
    (
        ".github/PR_TEMPLATE.md",
        [
            ".github/PULL_REQUEST_TEMPLATE.md",
            ".github/PR_TEMPLATE.md",
            ".github/PULL_REQUEST_TEMPLATE",
        ],
    ),
    ("code.json", ["code.json"]),
    ("CHANGELOG.md", ["CHANGELOG.md", "CHANGELOG.rst", "CHANGELOG.txt", "HISTORY.md"]),
    ("COMMUNITY.md", ["COMMUNITY.md", "COMMUNITY_GUIDELINES.md", ".github/COMMUNITY.md"]),
]

DOCKER_DOC_HINTS = ["docs/docker", "docs/deployment", "DOCKER.md", "docker-compose.yml", "Dockerfile"]

def _find_first_match(repo: Path, candidates: list[str]) -> Path | None:
    """
    Returns the first existing path (file or dir) among candidates,
    checked case-insensitively against what's actually on disk, since
    git/GitHub are case-sensitive but conventions vary (Readme.md,
    README.MD, etc. all show up in the wild).
    """

    for candidate in candidates:
        direct = repo / candidate
        if direct.exists():
            return direct

    search_dirs = {repo, repo / ".github", repo / "docs"}
    lowered_candidates = {c.lower(): c for c in candidates}
    for d in search_dirs:
        if not d.exists() or not d.is_dir():
            continue
        try:
            for entry in d.iterdir():
                rel = str(entry.relative_to(repo)).replace("\\", "/").lower()
                if rel in lowered_candidates:
                    return entry
        except PermissionError:
            continue

    return None


def check_file_hygiene(repo_path: str) -> list[dict]:
    """Runs the Documentation table checks and returns one row per expected file."""
    repo = Path(repo_path)
    rows = []

    for display_name, candidates in DOCUMENTATION_CHECKS:
        match = _find_first_match(repo, candidates)
        if match is None:
            rows.append(
                {
                    "file": display_name,
                    "exists": False,
                    "matched_path": None,
                    "notes": "Not found.",
                    "recommendation": f"Add a {display_name} file following CMS repository templates.",
                }
            )
            continue

        notes = ""
        if match.is_file():
            size = match.stat().st_size
            if size < STUB_SIZE_THRESHOLD_BYTES:
                notes = f"Present but only {size} bytes — likely a stub/placeholder, review contents."
            else:
                notes = f"Present ({size:,} bytes)."
        else:
            try:
                count = len(list(match.iterdir()))
            except PermissionError:
                count = "unknown"
            notes = f"Present as a directory with {count} template(s)."

        rows.append(
            {
                "file": display_name,
                "exists": True,
                "matched_path": str(match.relative_to(repo)),
                "notes": notes,
                "recommendation": "" if not notes.startswith("Present but only") else "Review and expand stub content.",
            }
        )

    return rows


def check_docker_docs(repo_path: str) -> dict:
    """Checks for any sign of docker/deployment documentation, per the template's hint item."""
    repo = Path(repo_path)
    found = []
    for hint in DOCKER_DOC_HINTS:
        p = repo / hint
        if p.exists():
            found.append(hint)

    return {
        "found": len(found) > 0,
        "matched_paths": found,
        "notes": (
            "Found deployment-related file(s)/dir(s)." if found
            else "No docker/deployment documentation found."
        ),
    }


def check_github_only_items() -> list[dict]:
    """
    Items the template's Repository Hygiene section calls for that live on
    GitHub itself (topics, description) rather than in the local clone.
    Flagged explicitly rather than omitted, so the report's Documentation
    table stays complete and the gap is visible rather than silently
    skipped.
    """
    return [
        {
            "item": "Repository Topics and Tags",
            "exists": None,
            "notes": "Not checkable from a local clone — requires GitHub API or web UI check.",
            "recommendation": "Verify repository has relevant topics set for discoverability.",
        },
        {
            "item": "Landing Page Description",
            "exists": None,
            "notes": "Not checkable from a local clone — requires GitHub API or web UI check.",
            "recommendation": "Verify repository has a clear, non-empty description set on GitHub.",
        },
    ]


def analyze(repo_path: str) -> dict:
    repo = Path(repo_path)
    if not repo.exists():
        raise FileNotFoundError(f"Path does not exist: {repo_path}")

    doc_rows = check_file_hygiene(repo_path)
    docker_docs = check_docker_docs(repo_path)
    github_only = check_github_only_items()

    present_count = sum(1 for r in doc_rows if r["exists"])
    total_count = len(doc_rows)

    return {
        "summary": {
            "files_present": present_count,
            "files_total": total_count,
            "completeness_pct": round((present_count / total_count) * 100, 1) if total_count else None,
        },
        "documentation": doc_rows,
        "docker_deployment_docs": docker_docs,
        "github_only_checks": github_only,
    }


def run(repo_path: str, output_dir: str) -> dict:
    """Entry point used by orchestrator.py (direct function call, no subprocess)."""
    data = analyze(repo_path)
    payload = make_output("hygiene", repo_path, data)
    write_analyzer_output(output_dir, "hygiene", payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Check a local repo for standard hygiene/documentation files.")
    add_local_repo_arg(parser)
    add_output_arg(parser)
    args = parser.parse_args()
    run(args.repo_path, args.output)


if __name__ == "__main__":
    main()