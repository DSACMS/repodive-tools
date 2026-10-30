"""
analyzers/security_scan.py

Runs gitleaks (https://github.com/gitleaks/gitleaks) against a LOCAL git
clone's full commit history to detect secrets that were ever committed —
even if later removed — per the Repodive Report template's "Code Analysis
/ Testing > Secret Scanning (gitleaks)" section:

    "An initial scan of the commit history found numerous secrets..."

IMPORTANT — secret values are NEVER written to our JSON output or the
rendered report. gitleaks' own output includes the matched secret string
by default; this analyzer strips that field before anything is persisted,
since a repodive report is explicitly meant to be shared with
stakeholders, and a report that itself leaks the secrets it found would
defeat the entire point of running the scan.

What IS retained per finding:
    - file path, line number, commit hash, author, commit date
    - rule/description (e.g. "AWS Access Key", "Generic API Key")
    - a redacted placeholder instead of the actual secret value

Design notes:
  - Uses `gitleaks git --report-format json` to scan the FULL commit
    history (not just the working tree), matching the template's framing
    of "an initial scan of the commit history" — a secret removed in a
    later commit is still a historical exposure and still needs rotation.
  - If gitleaks isn't installed, this analyzer fails clearly with install
    instructions rather than silently skipping, since secret scanning is
    a security-critical check that shouldn't be allowed to fail silently.
  - gitleaks exits with code 1 when leaks ARE found (this is normal,
    expected behavior per gitleaks' own docs, not a crash) and exit code
    0 when none are found. We handle both as success; only other exit
    codes are treated as actual tool failure.

Runs standalone:
    python analyzers/security_scan.py --repo-path ./cloned-repos/repodive-tools --output ./output/json

Or imported by orchestrator.py via `run(repo_path, output_dir)`.
"""

import argparse
import json
import shutil
import subprocess
import sys
import tempfile
from collections import defaultdict
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import (
    make_output,
    write_analyzer_output,
    add_local_repo_arg,
    add_output_arg,
)

REDACTED_PLACEHOLDER = "[REDACTED — value intentionally not persisted in repodive output]"


def verify_gitleaks_installed():
    """Confirms the gitleaks binary is on PATH before attempting to shell out to it."""
    if shutil.which("gitleaks") is None:
        raise RuntimeError(
            "gitleaks is not installed or not on PATH. Install it from "
            "https://github.com/gitleaks/gitleaks#installing "
            "(e.g. `brew install gitleaks`) and try again. Secret scanning "
            "is treated as a required check, not an optional one, so this "
            "analyzer will not silently skip."
        )


def run_gitleaks(repo_path: str) -> list[dict]:
    """
    Runs `gitleaks git` (full history scan) against repo_path and returns
    the parsed findings list. Writes gitleaks' JSON report to a temp file
    since gitleaks' own stdout mixes human-readable logging with the
    report in some versions — the --report-path flag guarantees clean
    JSON regardless of version/verbosity settings.
    """
    verify_gitleaks_installed()

    with tempfile.TemporaryDirectory() as tmp_dir:
        report_path = Path(tmp_dir) / "gitleaks-report.json"

        cmd = [
            "gitleaks",
            "git",
            repo_path,
            "--report-format",
            "json",
            "--report-path",
            str(report_path),
            "--no-banner",
        ]

        print(f"[info] running: {' '.join(cmd)}")
        result = subprocess.run(cmd, capture_output=True, text=True, encoding="utf-8")

        if result.returncode not in (0, 1):
            raise RuntimeError(
                f"gitleaks failed (exit {result.returncode}):\n{result.stderr}"
            )

        if not report_path.exists():
            return []

        with open(report_path, "r", encoding="utf-8") as f:
            content = f.read().strip()
            if not content:
                return []
            return json.loads(content)


def redact_findings(raw_findings: list[dict]) -> list[dict]:
    """
    Strips secret values from gitleaks' raw findings and keeps only
    metadata safe to persist and display in a shared report.
    """
    redacted = []
    for finding in raw_findings:
        redacted.append(
            {
                "rule_id": finding.get("RuleID"),
                "description": finding.get("Description"),
                "file": finding.get("File"),
                "line_number": finding.get("StartLine"),
                "commit": finding.get("Commit"),
                "author": finding.get("Author"),
                "email": finding.get("Email"),
                "date": finding.get("Date"),
                "secret_value": REDACTED_PLACEHOLDER,
            }
        )
    return redacted


def summarize_findings(findings: list[dict]) -> dict:
    """Groups redacted findings by rule type and by file for report summarization."""
    by_rule = defaultdict(int)
    by_file = defaultdict(int)
    by_author = defaultdict(int)
    commits_affected = set()

    for f in findings:
        by_rule[f["rule_id"] or "unknown"] += 1
        by_file[f["file"] or "unknown"] += 1
        by_author[f["author"] or "unknown"] += 1
        if f["commit"]:
            commits_affected.add(f["commit"])

    top_rules = sorted(by_rule.items(), key=lambda kv: kv[1], reverse=True)
    top_files = sorted(by_file.items(), key=lambda kv: kv[1], reverse=True)[:15]
    top_authors = sorted(by_author.items(), key=lambda kv: kv[1], reverse=True)[:10]

    return {
        "total_findings": len(findings),
        "unique_commits_affected": len(commits_affected),
        "unique_files_affected": len(by_file),
        "findings_by_rule": [{"rule_id": r, "count": c} for r, c in top_rules],
        "top_affected_files": [{"file": f, "count": c} for f, c in top_files],
        "top_committing_authors": [{"author": a, "count": c} for a, c in top_authors],
    }


def analyze(repo_path: str) -> dict:
    repo = Path(repo_path)
    if not repo.exists():
        raise FileNotFoundError(f"Path does not exist: {repo_path}")

    raw_findings = run_gitleaks(repo_path)
    redacted = redact_findings(raw_findings)
    summary = summarize_findings(redacted)

    return {
        "summary": summary,
        "scan_scope": "full commit history (git log, not just working tree)",
        "redaction_notice": (
            "All secret values have been redacted from this output. Findings include "
            "file, line, commit, and rule metadata only, sufficient to locate and "
            "rotate the affected credential without re-exposing it in this report."
        ),
        "findings": redacted[:200],
        "findings_truncated": len(redacted) > 200,
    }


def run(repo_path: str, output_dir: str) -> dict:
    """Entry point used by orchestrator.py (direct function call, no subprocess)."""
    data = analyze(repo_path)
    payload = make_output("security_scan", repo_path, data)
    write_analyzer_output(output_dir, "security_scan", payload)
    return payload


def main():
    parser = argparse.ArgumentParser(description="Scan a local repo's full git history for committed secrets via gitleaks.")
    add_local_repo_arg(parser)
    add_output_arg(parser)
    args = parser.parse_args()
    run(args.repo_path, args.output)


if __name__ == "__main__":
    main()