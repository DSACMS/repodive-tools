"""
analyzers/scc_report.py

Runs the `scc` CLI tool (https://github.com/boyter/scc) against a locally
cloned repository and parses its JSON output into the Repodive Report
template's "Code Breakdown" section:

  - Line counts (total lines, code, comments, blanks)
  - Language breakdown
  - Code complexity (cyclomatic complexity, per scc's estimate)

This analyzer ALSO produces the raw ULOC (unique lines of code) and
complexity totals that cocomo_locomo.py will consume directly — scc's
--format json output already contains everything needed for COCOMO, so
cocomo_locomo.py will call `run()` here (or read this JSON file) rather
than re-running scc itself.

Prerequisites:
  - `scc` must be installed and on PATH. Install via:
      https://github.com/boyter/scc#installation
    e.g. `go install github.com/boyter/scc/v3@latest`
    or   `brew install scc`

Design notes:
  - Uses `scc --format json` for the main language/line breakdown.
  - Excludes common non-human-written / vendored directories by default
    (node_modules, vendor, dist, build, .git) since the template
    explicitly calls out excluding auto-generated directories. This list
    is overridable via --exclude-dir (repeatable).
  - Does NOT run --cost-comparison here; that's COCOMO-specific output
    and belongs in cocomo_locomo.py to keep this analyzer focused on
    "what does the code look like" rather than "what would it cost."

Runs standalone:
    python analyzers/scc_report.py --repo-path ./cloned-repos/repodive-tools --output ./output/json

Or imported by orchestrator.py via `run(repo_path, output_dir)`.
"""

import argparse
import json
import shutil
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import (
    make_output,
    write_analyzer_output,
    add_local_repo_arg,
    add_output_arg,
)

DEFAULT_EXCLUDE_DIRS = [
    "node_modules",
    "vendor",
    "dist",
    "build",
    ".git",
    "__pycache__",
    ".venv",
    "venv",
]


def verify_scc_installed():
    """Confirms the scc binary is on PATH before attempting to shell out to it."""
    if shutil.which("scc") is None:
        raise RuntimeError(
            "scc is not installed or not on PATH. Install it from "
            "https://github.com/boyter/scc#installation (e.g. `brew install scc` "
            "or `go install github.com/boyter/scc/v3@latest`) and try again."
        )


def run_scc(repo_path: str, exclude_dirs: list[str]) -> dict:
    """
    Runs `scc --format json` against repo_path, excluding the given
    directories, and returns the parsed JSON (a list of per-language
    dicts, per scc's output format).
    """
    verify_scc_installed()

    cmd = ["scc", "--format", "json"]
    for d in exclude_dirs:
        cmd += ["--exclude-dir", d]
    cmd.append(repo_path)

    print(f"[info] running: {' '.join(cmd)}")
    result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

    if result.returncode != 0:
        raise RuntimeError(f"scc failed (exit {result.returncode}):\n{result.stderr}")

    try:
        return json.loads(result.stdout)
    except json.JSONDecodeError as e:
        raise RuntimeError(f"Could not parse scc JSON output: {e}\nRaw output:\n{result.stdout[:500]}")


def summarize_languages(scc_output: list[dict]) -> list[dict]:
    """
    scc's JSON output is a list of language entries, each with file-level
    detail under "Files". We strip per-file noise for the report and keep
    language-level totals, sorted by code line count descending.
    """
    languages = []
    for entry in scc_output:
        languages.append(
            {
                "name": entry.get("Name"),
                "files": entry.get("Count", 0),
                "lines": entry.get("Lines", 0),
                "code": entry.get("Code", 0),
                "comments": entry.get("Comment", 0),
                "blanks": entry.get("Blank", 0),
                "complexity": entry.get("Complexity", 0),
                "bytes": entry.get("Bytes", 0),
            }
        )
    languages.sort(key=lambda l: l["code"], reverse=True)
    return languages


def compute_totals(languages: list[dict]) -> dict:
    """Sums language-level stats into repo-wide totals."""
    totals = {
        "files": 0,
        "lines": 0,
        "code": 0,
        "comments": 0,
        "blanks": 0,
        "complexity": 0,
        "bytes": 0,
    }
    for lang in languages:
        totals["files"] += lang["files"]
        totals["lines"] += lang["lines"]
        totals["code"] += lang["code"]
        totals["comments"] += lang["comments"]
        totals["blanks"] += lang["blanks"]
        totals["complexity"] += lang["complexity"]
        totals["bytes"] += lang["bytes"]
    return totals


def compute_language_percentages(languages: list[dict], total_code: int) -> list[dict]:
    """Adds a % of total codebase (by code lines) to each language entry."""
    out = []
    for lang in languages:
        pct = round((lang["code"] / total_code) * 100, 1) if total_code else None
        out.append({**lang, "pct_of_codebase": pct})
    return out


def top_complexity_files(scc_output: list[dict], top_n: int = 15) -> list[dict]:
    """
    Flattens all per-file entries across languages and returns the N most
    complex files by scc's cyclomatic complexity estimate — useful for
    flagging "this file probably needs a refactor" candidates in the
    report without requiring a human to dig through scc's raw output.
    """
    all_files = []
    for entry in scc_output:
        lang_name = entry.get("Name")
        for f in entry.get("Files", []) or []:
            all_files.append(
                {
                    "path": f.get("Location"),
                    "language": lang_name,
                    "lines": f.get("Lines", 0),
                    "code": f.get("Code", 0),
                    "complexity": f.get("Complexity", 0),
                }
            )
    all_files.sort(key=lambda f: f["complexity"], reverse=True)
    return all_files[:top_n]


def analyze(repo_path: str, exclude_dirs: list[str] | None = None) -> dict:
    exclude_dirs = exclude_dirs if exclude_dirs is not None else DEFAULT_EXCLUDE_DIRS

    repo = Path(repo_path)
    if not repo.exists():
        raise FileNotFoundError(f"Path does not exist: {repo_path}")

    scc_output = run_scc(repo_path, exclude_dirs)
    languages = summarize_languages(scc_output)
    totals = compute_totals(languages)
    languages_with_pct = compute_language_percentages(languages, totals["code"])
    hotspots = top_complexity_files(scc_output, top_n=15)

    return {
        "excluded_dirs": exclude_dirs,
        "totals": totals,
        "languages": languages_with_pct,
        "complexity_hotspots": hotspots,
        # Kept for cocomo_locomo.py to consume without re-running scc.
        # scc's --cost-comparison / COCOMO math needs total code lines +
        # a per-language breakdown, both of which are already here.
        "_raw_scc_output_available": True,
    }


def run(repo_path: str, output_dir: str, exclude_dirs: list[str] | None = None) -> dict:
    """Entry point used by orchestrator.py (direct function call, no subprocess)."""
    data = analyze(repo_path, exclude_dirs=exclude_dirs)
    payload = make_output("scc_report", repo_path, data)
    write_analyzer_output(output_dir, "scc_report", payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Run scc against a local repo and summarize code breakdown.")
    add_local_repo_arg(parser)
    add_output_arg(parser)
    parser.add_argument(
        "--exclude-dir",
        action="append",
        dest="exclude_dirs",
        default=None,
        help=(
            "Directory to exclude from scc analysis (repeatable). "
            f"Defaults to: {', '.join(DEFAULT_EXCLUDE_DIRS)}"
        ),
    )
    args = parser.parse_args()
    run(args.repo_path, args.output, exclude_dirs=args.exclude_dirs)


if __name__ == "__main__":
    main()