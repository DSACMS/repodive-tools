"""
orchestrator.py

Runs all repodive analyzers against a single repository (one local clone +
one GitHub org/repo pair) and assembles their JSON outputs into a single
Markdown report that follows the structure of the Repodive Report template.

Analyzers are imported and called directly as functions (not subprocess),
per project decision: this keeps data passing simple (dicts, not
stdout-parsing) while each analyzer file still works standalone via its
own `if __name__ == "__main__"` block.

As more analyzers are added (commits, scc, cocomo/locomo, hygiene, issues,
releases, security, AI usage) they get:
  1. imported at the top
  2. added to the ANALYZERS list below
  3. a rendering section added in render_report()

Usage:
    python orchestrator.py \\
        --repo-path ./cloned-repos/repodive-tools \\
        --github-repo DSACMS/repodive-tools \\
        --output ./output
"""

import argparse
import sys
from datetime import datetime, timezone
from pathlib import Path

from config import load_analyzer_output

from analyzers import (
    github_prs,
    git_commits,
    scc_report,
    hygiene,
    cocomo_locomo,
    github_issues,
    releases,
    security_scan,
    ai_usage,
)


def run_all_analyzers(repo_path: str, github_repo: str, json_output_dir: str, cocomo_mode: str = "organic") -> dict:
    """
    Runs every available analyzer in sequence and returns a dict of
    {analyzer_name: payload} for use in rendering. Each analyzer also
    independently writes its own JSON file to json_output_dir, so a
    partial/failed run still leaves usable artifacts behind.
    """
    results = {}

    print("\n=== Running: github_prs ===")
    try:
        results["github_prs"] = github_prs.run(github_repo, json_output_dir)
    except Exception as e:
        print(f"[error] github_prs analyzer failed: {e}")
        results["github_prs"] = None

    print("\n=== Running: scc_report ===")
    try:
        results["scc_report"] = scc_report.run(repo_path, json_output_dir)
    except Exception as e:
        print(f"[error] scc_report analyzer failed: {e}")
        results["scc_report"] = None

    # cocomo_locomo depends on scc_report's ULOC output having already
    # been written to json_output_dir — only attempt it if scc succeeded.
    print("\n=== Running: cocomo_locomo ===")
    if results.get("scc_report"):
        try:
            results["cocomo_locomo"] = cocomo_locomo.run(repo_path, json_output_dir, mode=cocomo_mode)
        except Exception as e:
            print(f"[error] cocomo_locomo analyzer failed: {e}")
            results["cocomo_locomo"] = None
    else:
        print("[skip] cocomo_locomo requires scc_report to have succeeded first.")
        results["cocomo_locomo"] = None

    # Future analyzers follow the same try/except pattern, e.g.:
    #
    # print("\n=== Running: cocomo_locomo ===")
    # try:
    #     results["cocomo_locomo"] = cocomo_locomo.run(repo_path, json_output_dir)
    # except Exception as e:
    #     print(f"[error] cocomo_locomo analyzer failed: {e}")
    #     results["cocomo_locomo"] = None

    print("\n=== Running: github_issues ===")
    try:
        results["github_issues"] = github_issues.run(github_repo, json_output_dir)
    except Exception as e:
        print(f"[error] github_issues analyzer failed: {e}")
        results["github_issues"] = None

    print("\n=== Running: releases ===")
    try:
        results["releases"] = releases.run(github_repo, json_output_dir)
    except Exception as e:
        print(f"[error] releases analyzer failed: {e}")
        results["releases"] = None

    print("\n=== Running: git_commits ===")
    try:
        results["git_commits"] = git_commits.run(repo_path, json_output_dir)
    except Exception as e:
        print(f"[error] git_commits analyzer failed: {e}")
        results["git_commits"] = None

    print("\n=== Running: security_scan ===")
    try:
        results["security_scan"] = security_scan.run(repo_path, json_output_dir)
    except Exception as e:
        print(f"[error] security_scan analyzer failed: {e}")
        results["security_scan"] = None

    print("\n=== Running: hygiene ===")
    try:
        results["hygiene"] = hygiene.run(repo_path, json_output_dir)
    except Exception as e:
        print(f"[error] hygiene analyzer failed: {e}")
        results["hygiene"] = None

    print("\n=== Running: ai_usage ===")
    try:
        # Runs after github_prs so it can optionally check PR authorship
        # (bot/agent accounts) if that JSON is already on disk. Still works
        # fine on commit data alone if github_prs failed or wasn't run.
        results["ai_usage"] = ai_usage.run(repo_path, json_output_dir)
    except Exception as e:
        print(f"[error] ai_usage analyzer failed: {e}")
        results["ai_usage"] = None

    return results


def _fmt_pct(value):
    return f"{value}%" if value is not None else "N/A"


def _fmt_num(value):
    return f"{value:,}" if isinstance(value, (int, float)) else "N/A"


def render_pr_section(payload: dict | None) -> str:
    """Renders the 'Pull Requests' subsection of Development Activity."""
    if not payload or not payload.get("data"):
        return (
            "### Pull Requests\n\n"
            "_No PR data available. Run `analyzers/github_prs.py` to populate this section._\n"
        )

    data = payload["data"]
    s = data["summary"]

    lines = []
    lines.append("### Pull Requests\n")
    lines.append(f"_Data as of {payload['generated_at']}_\n")

    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total PRs analyzed | {_fmt_num(s['total_prs_fetched'])} |")
    lines.append(f"| Human-authored PRs | {_fmt_num(s['human_prs'])} |")
    lines.append(f"| Bot-authored PRs | {_fmt_num(s['bot_prs'])} ({_fmt_pct(s['bot_pct'])}) |")
    lines.append(f"| Merged (human) PRs | {_fmt_num(s['merged_human_prs'])} |")
    lines.append(f"| Median time-to-merge | {s['median_time_to_merge_days']} days |")
    lines.append(f"| Average time-to-merge | {s['average_time_to_merge_days']} days |")
    lines.append(f"| Median PR size (lines changed) | {_fmt_num(s['median_pr_size'])} |")
    lines.append(f"| Self-merged PRs (0 reviews) | {_fmt_num(s['self_merge_count'])} ({_fmt_pct(s['self_merge_pct'])}) |")
    lines.append(
        f"| Merged with zero reviews | {_fmt_num(s['merged_with_zero_reviews_count'])} "
        f"({_fmt_pct(s['merged_with_zero_reviews_pct'])}) |"
    )
    lines.append("")

    lines.append("**PR size distribution:**\n")
    lines.append("| Bucket | Count |")
    lines.append("|---|---|")
    for bucket, count in data["size_distribution"].items():
        lines.append(f"| {bucket} | {count} |")
    lines.append("")

    lines.append("**Top contributors by PR count:**\n")
    lines.append("| Author | PRs | Merged | Self-Merged | Self-Merge Rate |")
    lines.append("|---|---|---|---|---|")
    for c in data["contributors"][:15]:
        rate = _fmt_pct(c["self_merge_rate_pct"])
        lines.append(f"| {c['author']} | {c['pr_count']} | {c['merged_count']} | {c['self_merge_count']} | {rate} |")
    lines.append("")

    return "\n".join(lines)


def render_commits_section(payload: dict | None) -> str:
    """Renders the 'Commits' subsection of Development Activity."""
    if not payload or not payload.get("data"):
        return (
            "#### Commits\n\n"
            "_No commit data available. Run `analyzers/git_commits.py` to populate this section._\n"
        )

    data = payload["data"]
    s = data["summary"]

    lines = []
    lines.append("#### Commits\n")
    lines.append(f"_Data as of {payload['generated_at']}_\n")

    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total commits (no merges) | {_fmt_num(s['total_commits'])} |")
    lines.append(f"| Total contributors | {_fmt_num(s['total_contributors'])} |")
    lines.append(f"| First commit | {s['first_commit'] or 'N/A'} |")
    lines.append(f"| Last commit | {s['last_commit'] or 'N/A'} |")
    lines.append("")

    spikes = data.get("activity_spikes", [])
    if spikes:
        lines.append(
            f"**Activity spikes detected:** {len(spikes)} month(s) with commit volume "
            f"at least 2x the trailing 3-month average — a possible sign of last-minute, "
            f"pre-release crunch work.\n"
        )
        lines.append("| Month | Commits | Trailing 3-mo Avg | Multiplier |")
        lines.append("|---|---|---|---|")
        for sp in spikes[:10]:
            lines.append(f"| {sp['month']} | {sp['commits']} | {sp['trailing_3mo_avg']} | {sp['multiplier']}x |")
        lines.append("")
    else:
        lines.append("**Activity spikes:** None detected — commit volume looks relatively steady month to month.\n")

    return "\n".join(lines)


def render_bus_factor_section(payload: dict | None) -> str:
    """Renders the 'Bus Factor' subsection of Development Activity."""
    if not payload or not payload.get("data"):
        return (
            "#### Bus Factor\n\n"
            "_No commit data available. Run `analyzers/git_commits.py` to populate this section._\n"
        )

    data = payload["data"]
    bf = data["bus_factor"]
    contributors = data["contributors"]
    consistency = data["activity_consistency"]

    lines = []
    lines.append("#### Bus Factor\n")

    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total contributors | {_fmt_num(bf['total_contributors'])} |")
    lines.append(f"| Top contributor's share of all commits | {_fmt_pct(bf['top_contributor_pct'])} |")
    lines.append(f"| Contributors needed to reach 50% of commits | {_fmt_num(bf['contributors_to_50pct'])} |")
    lines.append(f"| Contributors needed to reach 80% of commits | {_fmt_num(bf['contributors_to_80pct'])} |")
    lines.append("")

    if bf["contributors_to_50pct"] and bf["contributors_to_50pct"] <= 2:
        lines.append(
            "> ⚠️ **Knowledge concentration risk:** half of all commits come from just "
            f"{bf['contributors_to_50pct']} contributor(s). Losing this person/these people "
            "would represent significant institutional knowledge loss.\n"
        )

    lines.append("**Top contributors by commit count:**\n")
    lines.append("| Author | Commits | Lines Changed | First Commit | Last Commit |")
    lines.append("|---|---|---|---|---|")
    for c in contributors[:15]:
        lines.append(
            f"| {c['name']} | {c['commits']} | {_fmt_num(c['total_churn'])} | "
            f"{(c['first_commit'] or '')[:10]} | {(c['last_commit'] or '')[:10]} |"
        )
    lines.append("")

    if consistency:
        lines.append(
            "**Activity consistency** (ratio of months-active to total span; closer to 1.0 = "
            "steady ongoing work, closer to 0 = long gaps punctuated by bursts):\n"
        )
        lines.append("| Author | Months Active | Span (months) | Consistency Ratio |")
        lines.append("|---|---|---|---|")
        for c in consistency:
            lines.append(
                f"| {c['author']} | {c['distinct_months_active']} | {c['span_months']} | "
                f"{c['consistency_ratio']} |"
            )
        lines.append("")

    return "\n".join(lines)


def render_code_breakdown_section(payload: dict | None) -> str:
    """Renders the 'Code Breakdown' subsection of Analysis (line counts, complexity, language breakdown)."""
    if not payload or not payload.get("data"):
        return (
            "### Code Breakdown\n\n"
            "_No scc data available. Run `analyzers/scc_report.py` to populate this section. "
            "Requires the `scc` CLI tool to be installed._\n"
        )

    data = payload["data"]
    t = data["totals"]
    languages = data["languages"]
    hotspots = data["complexity_hotspots"]

    lines = []
    lines.append("### Code Breakdown\n")
    lines.append(f"_Data as of {payload['generated_at']}_\n")
    lines.append(
        f"_Excluded directories: {', '.join(data['excluded_dirs'])}_\n"
    )

    lines.append("#### Line Counts\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total files | {_fmt_num(t['files'])} |")
    lines.append(f"| Total lines | {_fmt_num(t['lines'])} |")
    lines.append(f"| Code lines | {_fmt_num(t['code'])} |")
    lines.append(f"| Comment lines | {_fmt_num(t['comments'])} |")
    lines.append(f"| Blank lines | {_fmt_num(t['blanks'])} |")
    lines.append("")

    lines.append("#### Code Complexity\n")
    lines.append(
        f"Total cyclomatic complexity (scc estimate, summed across all files): "
        f"**{_fmt_num(t['complexity'])}**\n"
    )

    if hotspots:
        lines.append("**Most complex files** (candidates for refactor review):\n")
        lines.append("| File | Language | Code Lines | Complexity |")
        lines.append("|---|---|---|---|")
        for h in hotspots[:10]:
            lines.append(f"| `{h['path']}` | {h['language']} | {h['code']} | {h['complexity']} |")
        lines.append("")

    lines.append("#### Language Breakdown\n")
    lines.append("| Language | Files | Code Lines | % of Codebase | Complexity |")
    lines.append("|---|---|---|---|---|")
    for lang in languages:
        pct = _fmt_pct(lang["pct_of_codebase"])
        lines.append(
            f"| {lang['name']} | {lang['files']} | {_fmt_num(lang['code'])} | {pct} | {_fmt_num(lang['complexity'])} |"
        )
    lines.append("")

    return "\n".join(lines)


def render_hygiene_section(payload: dict | None) -> str:
    """Renders the 'Repository Hygiene > Documentation' section, matching the template's table layout."""
    if not payload or not payload.get("data"):
        return (
            "### Repository Hygiene\n\n"
            "_No hygiene data available. Run `analyzers/hygiene.py` to populate this section._\n"
        )

    data = payload["data"]
    s = data["summary"]
    docs = data["documentation"]
    docker = data["docker_deployment_docs"]
    github_only = data["github_only_checks"]

    lines = []
    lines.append("### Repository Hygiene\n")
    lines.append(f"_Data as of {payload['generated_at']}_\n")
    lines.append(
        f"**Documentation completeness: {s['files_present']}/{s['files_total']} "
        f"({_fmt_pct(s['completeness_pct'])})**\n"
    )

    lines.append("#### Documentation\n")
    lines.append("| File | Exists? | Notes | Recommendations |")
    lines.append("|---|---|---|---|")
    for row in docs:
        check = "✅" if row["exists"] else "❌"
        notes = row["notes"]
        rec = row["recommendation"] or "—"
        lines.append(f"| {row['file']} | {check} | {notes} | {rec} |")

    # Docker/deployment docs as an additional row under the same table, per template's
    # "Docs: docker deployment guide" line item.
    docker_check = "✅" if docker["found"] else "❌"
    docker_rec = "—" if docker["found"] else "Add deployment documentation (Docker setup, env vars, run instructions)."
    lines.append(f"| Docker deployment guide | {docker_check} | {docker['notes']} | {docker_rec} |")
    lines.append("")

    lines.append("#### Repository Details\n")
    lines.append("| Finding | Recommendation |")
    lines.append("|---|---|")
    for item in github_only:
        lines.append(f"| {item['item']} — _{item['notes']}_ | {item['recommendation']} |")
    lines.append("")

    return "\n".join(lines)


def render_costs_section(payload: dict | None, repo_display_name: str) -> str:
    """Renders the 'Costs' section (COCOMO + LOCOMO), mirroring the template's two tables and explanatory text."""
    if not payload or not payload.get("data"):
        return (
            "### Costs\n\n"
            "_No cost data available. Run `analyzers/cocomo_locomo.py` (requires scc_report "
            "to have been run first) to populate this section._\n"
        )

    data = payload["data"]
    cocomo = data["cocomo"]
    locomo = data["locomo"]
    comparison = data["comparison_table"]
    review_range = data["review_pct_range"]

    lines = []
    lines.append("### Costs\n")
    lines.append(f"_Data as of {payload['generated_at']}_\n")

    lines.append(
        f"These figures come from two automated code-analysis models. They estimate time two "
        f"different ways: if humans built the code from scratch, and if an AI tool regenerated it. "
        f"Neither number is a staffing recommendation. Both are rough, formula-based estimates that "
        f"count lines of code; they don't assess actual team performance, code quality, or business "
        f"value.\n"
    )

    lines.append("#### If Humans Built This From Scratch (COCOMO Model)\n")
    lines.append(
        "COCOMO is an industry-standard formula that estimates project time from the size of a "
        "codebase. It works best on code that people wrote by hand, code that required design "
        f"decisions and engineering judgment. (Mode: **{cocomo['mode']}**)\n"
    )
    lines.append(f"| Metric | {repo_display_name} |")
    lines.append("|---|---|")
    lines.append(f"| Estimated Cost | ${cocomo['estimated_cost_usd']:,.2f} |")
    lines.append(f"| Unique lines of code (ULOC) | {cocomo['uloc']:,} |")
    lines.append(f"| Schedule effort | {cocomo['schedule_months']} months |")
    lines.append(f"| People required | {cocomo['people_required']} |")
    lines.append("")
    lines.append(
        "These numbers represent the entire historical effort to build the system from a blank "
        "slate. They are not the cost of maintaining the system today, and they are not a measure "
        "of how many people should currently staff the team.\n"
    )

    lines.append("#### If an AI Tool Regenerated This Code (LOCOMO Model)\n")
    lines.append(
        "LOCOMO estimates what it would cost to have an AI model regenerate the same code, plus "
        "the time a human reviewer would still need to check that output. The table below lays out "
        "cost and time side by side with the human baseline, across three AI model sizes.\n"
    )

    lines.append(f"**Human vs. LLM Cost & Time — {repo_display_name}**\n")
    lines.append("| Metric | Human (COCOMO) | LLM - Small | LLM - Medium | LLM - Large |")
    lines.append("|---|---|---|---|---|")
    for row in comparison:
        lines.append(
            f"| {row['metric']} | {row['human']} | {row['llm_small']} | {row['llm_medium']} | {row['llm_large']} |"
        )
    lines.append("")

    if review_range["min"] is not None:
        lines.append(
            f"Two things matter here. First, the dollar cost to generate code with AI is "
            f"dramatically lower than the human cost to write it, but that's an unfair comparison "
            f"on its own. Second, and more important: a person still has to review every line the "
            f"AI produces. That review time stays fixed regardless of which AI model generates the "
            f"code, and it dominates the AI timeline in every scenario — it's the majority of the "
            f"total time, not an afterthought. For {repo_display_name}, review time makes up "
            f"**{review_range['min']}–{review_range['max']}%** of total AI-assisted delivery time "
            f"depending on model size.\n"
        )

    lines.append("#### Why These Are Brute Force Numbers\n")
    lines.append(
        "Both models work by counting lines of code and running that count through a formula. "
        "They don't know which lines were hard to write and which were simple. They don't know if "
        "a team was understaffed, overstaffed, or working efficiently. They can't tell the "
        "difference between code that reflects careful engineering and code that could have been "
        "written more simply. Additionally, the models do not take into account the entire "
        "development history of the repository — they operate on a snapshot of the current state, "
        "so major changes such as migrations, refactors, and rewrites are not accounted for in the "
        "estimates.\n\n"
        "Because of this, these numbers should not be used to justify hiring or firing decisions, "
        "to judge whether a team is over- or under-resourced, or to set expectations for how fast "
        "a rebuild \"should\" happen. They're best used as a rough sense of scale, to help "
        "stakeholders grasp how large and complex the system is.\n"
    )

    assumptions = locomo["assumptions"]
    lines.append("#### LOCOMO Assumptions Used\n")
    lines.append("| Assumption | Value |")
    lines.append("|---|---|")
    lines.append(f"| Tokens per line of code | {assumptions['tokens_per_line']} |")
    lines.append(f"| Human review pace | {assumptions['review_loc_per_hour']} lines/hour |")
    lines.append(f"| Reviewer hourly rate | ${assumptions['reviewer_hourly_rate_usd']}/hr |")
    for tier_key, tier in assumptions["model_tiers"].items():
        lines.append(
            f"| {tier['label']} — cost per 1M output tokens | ${tier['cost_per_1m_output_tokens_usd']} |"
        )
        lines.append(f"| {tier['label']} — generation speed | {tier['tokens_per_second']} tokens/sec |")
    lines.append(
        "\n_These are illustrative, documented assumptions — not live market pricing. "
        "Override via `--tokens-per-line`, `--review-loc-per-hour`, `--reviewer-hourly-rate`, "
        "or by editing `MODEL_TIERS` in `cocomo_locomo.py` to match your organization's actual rates._\n"
    )

    return "\n".join(lines)


def render_issues_section(payload: dict | None) -> str:
    """Renders the 'Issues' subsection of Development Activity."""
    if not payload or not payload.get("data"):
        return (
            "#### Issues\n\n"
            "_No issue data available. Run `analyzers/github_issues.py` to populate this section._\n"
        )

    data = payload["data"]
    s = data["summary"]

    lines = []
    lines.append("#### Issues\n")
    lines.append(f"_Data as of {payload['generated_at']}_\n")

    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total issues | {_fmt_num(s['total_issues'])} |")
    lines.append(f"| Open issues | {_fmt_num(s['open_issues'])} |")
    lines.append(f"| Closed issues | {_fmt_num(s['closed_issues'])} |")
    lines.append(
        f"| Stale open issues (no activity in {s['stale_days_threshold']}+ days) | "
        f"{_fmt_num(s['stale_open_issues'])} |"
    )
    lines.append(
        f"| Untriaged open issues (no labels) | {_fmt_num(s['untriaged_open_issues'])} "
        f"({_fmt_pct(s['untriaged_open_pct'])}) |"
    )
    lines.append(f"| Median time to close | {s['median_time_to_close_days']} days |")
    lines.append(f"| Average time to close | {s['average_time_to_close_days']} days |")
    lines.append(f"| Current net backlog (opened − closed, cumulative) | {s['current_net_backlog']} |")
    lines.append("")

    if s["current_net_backlog"] > 0:
        lines.append(
            f"> ⚠️ **Growing backlog:** cumulative opened issues exceed closed issues by "
            f"{s['current_net_backlog']}, suggesting triage/closure isn't keeping pace with intake.\n"
        )
    elif s["current_net_backlog"] < 0:
        lines.append(
            "> ✅ Issue closures have outpaced new issues over the observed period — backlog is shrinking.\n"
        )

    if data.get("top_labels"):
        lines.append("**Most common labels:**\n")
        lines.append("| Label | Count |")
        lines.append("|---|---|")
        for l in data["top_labels"][:10]:
            lines.append(f"| {l['label']} | {l['count']} |")
        lines.append("")

    lines.append(
        "_Note: \"triaged\" is approximated here as \"has at least one label\" — GitHub has no "
        "universal formal triage status, so this is a practical proxy, not a guarantee of actual "
        "review._\n"
    )

    return "\n".join(lines)


def render_releases_section(payload: dict | None) -> str:
    """Renders the 'Releases' subsection of Development Activity."""
    if not payload or not payload.get("data"):
        return (
            "#### Releases\n\n"
            "_No release data available. Run `analyzers/releases.py` to populate this section._\n"
        )

    data = payload["data"]
    s = data["summary"]
    cadence = data["cadence"]
    bumps = data["version_bump_breakdown"]

    lines = []
    lines.append("#### Releases\n")
    lines.append(f"_Data as of {payload['generated_at']}_\n")

    if s["total_releases"] == 0:
        lines.append(
            f"No formal GitHub Releases found for this repository. "
            f"{s['raw_tag_count']} raw git tag(s) exist without published Release notes.\n"
        )
        if s["raw_tag_count"] > 0:
            lines.append(
                "> ⚠️ Consider publishing formal GitHub Releases (with notes) against existing "
                "tags to improve visibility into version history for consumers and contributors.\n"
            )
        return "\n".join(lines)

    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Total releases | {_fmt_num(s['total_releases'])} |")
    lines.append(f"| Published releases | {_fmt_num(s['published_releases'])} |")
    lines.append(f"| Draft releases | {_fmt_num(s['draft_releases'])} |")
    lines.append(f"| Pre-releases | {_fmt_num(s['prerelease_count'])} |")
    lines.append(f"| First release | {(s['first_release'] or '')[:10] or 'N/A'} |")
    lines.append(f"| Latest release | {(s['latest_release'] or '')[:10] or 'N/A'} |")
    if s["tags_without_formal_releases"] > 0:
        lines.append(
            f"| Tags without formal Release notes | {_fmt_num(s['tags_without_formal_releases'])} |"
        )
    lines.append("")

    lines.append("**Release cadence:**\n")
    lines.append("| Metric | Value |")
    lines.append("|---|---|")
    lines.append(f"| Median days between releases | {cadence['median_gap_days']} |")
    lines.append(f"| Average days between releases | {cadence['average_gap_days']} |")
    lines.append(f"| Coefficient of variation | {cadence['coefficient_of_variation']} |")
    lines.append("")
    lines.append(f"**Assessment:** {cadence['cadence_assessment']}\n")

    lines.append("**Version bump breakdown:**\n")
    lines.append("| Type | Count |")
    lines.append("|---|---|")
    lines.append(f"| Major | {bumps['major']} |")
    lines.append(f"| Minor | {bumps['minor']} |")
    lines.append(f"| Patch | {bumps['patch']} |")
    if bumps["unparseable"] > 0:
        lines.append(f"| Unparseable (non-semver tag) | {bumps['unparseable']} |")
    lines.append("")

    lines.append("**Recent releases:**\n")
    lines.append("| Tag | Published | Type | Pre-release? |")
    lines.append("|---|---|---|---|")
    for r in data["releases"][:10]:
        pub = (r["published_at"] or "")[:10]
        bump = r.get("bump_type") or "—"
        prerelease = "Yes" if r["is_prerelease"] else "No"
        lines.append(f"| `{r['tag_name']}` | {pub} | {bump} | {prerelease} |")
    lines.append("")

    return "\n".join(lines)


def render_security_scan_section(payload: dict | None) -> str:
    """Renders the 'Secret Scanning (gitleaks)' subsection of Code Analysis / Testing."""
    if not payload or not payload.get("data"):
        return (
            "### Code Analysis / Testing\n\n"
            "#### Secret Scanning (gitleaks)\n\n"
            "_No scan data available. Run `analyzers/security_scan.py` to populate this section. "
            "Requires the `gitleaks` CLI tool to be installed._\n"
        )

    data = payload["data"]
    s = data["summary"]

    lines = []
    lines.append("### Code Analysis / Testing\n")
    lines.append("#### Secret Scanning (gitleaks)\n")
    lines.append(f"_Data as of {payload['generated_at']}_  \n_Scan scope: {data['scan_scope']}_\n")
    lines.append(f"> 🔒 {data['redaction_notice']}\n")

    if s["total_findings"] == 0:
        lines.append(
            "✅ No secrets were detected in the commit history by this scan. "
            "Note: gitleaks relies on pattern-matching rules and cannot guarantee the "
            "complete absence of sensitive material — treat this as a strong signal, not a certainty.\n"
        )
        return "\n".join(lines)

    lines.append(
        f"⚠️ **{s['total_findings']} potential secret(s) found** across "
        f"{s['unique_commits_affected']} commit(s) and {s['unique_files_affected']} file(s) "
        f"in the commit history.\n"
    )
    lines.append(
        "> **Action required:** any credential found here should be treated as compromised "
        "and rotated, even if it was later removed from the codebase — it remains permanently "
        "visible in git history to anyone with repo access unless history is rewritten.\n"
    )

    lines.append("**Findings by rule type:**\n")
    lines.append("| Rule | Count |")
    lines.append("|---|---|")
    for r in s["findings_by_rule"]:
        lines.append(f"| {r['rule_id']} | {r['count']} |")
    lines.append("")

    lines.append("**Most affected files:**\n")
    lines.append("| File | Finding Count |")
    lines.append("|---|---|")
    for f in s["top_affected_files"]:
        lines.append(f"| `{f['file']}` | {f['count']} |")
    lines.append("")

    if data.get("findings_truncated"):
        lines.append(
            f"_Showing a capped subset of findings in raw JSON output "
            f"({len(data['findings'])} of {s['total_findings']} total). "
            f"Re-run gitleaks directly for the complete list during remediation._\n"
        )

    return "\n".join(lines)


def render_ai_usage_section(payload: dict | None) -> str:
    """Renders the 'AI Usage' subsection of Development Activity."""
    if not payload or not payload.get("data"):
        return (
            "#### AI Usage\n\n"
            "_No AI usage data available. Run `analyzers/ai_usage.py` to populate this section._\n"
        )

    data = payload["data"]
    s = data["summary"]

    lines = []
    lines.append("#### AI Usage\n")
    lines.append(f"_Data as of {payload['generated_at']}_\n")
    lines.append(f"> ℹ️ {data['methodology_notice']}\n")

    if not s["any_disclosed_ai_usage_detected"] and s["low_confidence_signals"] == 0:
        lines.append(
            "No disclosed or tool-inserted AI usage signals were detected in commit history "
            "or PR authorship. This does not confirm AI tools weren't used — only that no "
            "visible trace of disclosed usage was found.\n"
        )
        return "\n".join(lines)

    lines.append("| Confidence Level | Signal Type | Count |")
    lines.append("|---|---|---|")
    lines.append(f"| High | Literal bot/agent PR authorship | {s['high_confidence_signals']} |")
    lines.append(f"| Medium | Tool-inserted commit co-author trailers | {s['medium_confidence_signals']} |")
    lines.append(f"| Low | Free-text keyword mentions | {s['low_confidence_signals']} |")
    lines.append("")

    if s["distinct_tools_detected"]:
        lines.append(f"**Tools detected:** {', '.join(s['distinct_tools_detected'])}\n")

    pr_signals = data.get("pr_level_signals")
    if pr_signals and pr_signals["ai_agent_authored_prs"]:
        lines.append("**PRs authored directly by an AI agent (high confidence):**\n")
        lines.append("| PR # | Agent | Created | Merged? |")
        lines.append("|---|---|---|---|")
        for p in pr_signals["ai_agent_authored_prs"][:10]:
            merged = "Yes" if p["merged"] else "No"
            lines.append(f"| #{p['number']} | {p['author']} | {(p['created_at'] or '')[:10]} | {merged} |")
        lines.append("")
    elif not s["pr_data_available"]:
        lines.append(
            "_PR-level authorship signals were not checked — run `analyzers/github_prs.py` "
            "first so its output is available to this analyzer._\n"
        )

    commit_signals = data["commit_level_signals"]
    if commit_signals["coauthor_signals"]:
        lines.append("**Commits with AI co-author trailers (medium confidence):**\n")
        lines.append("| Commit | Author | Date | Tool |")
        lines.append("|---|---|---|---|")
        for c in commit_signals["coauthor_signals"][:10]:
            lines.append(f"| `{c['hash']}` | {c['author']} | {c['date'][:10]} | {c['tool']} |")
        lines.append("")

    if commit_signals["free_text_signals"]:
        lines.append(
            f"**Free-text AI mentions in commit messages (low confidence, {len(commit_signals['free_text_signals'])} total):** "
            "these are keyword matches only and do not confirm actual tool usage — shown for "
            "context, not as a reliable usage count.\n"
        )

    return "\n".join(lines)


def render_report(results: dict, repo_path: str, github_repo: str) -> str:
    """Assembles the full Markdown report matching the Repodive Report template structure."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")

    sections = []
    sections.append(f"# Repodive Report: {github_repo}\n")
    sections.append(
        f"By: CMS.gov Open Source Program Office  \n"
        f"{today} | Version: 1.0 | Unclassified // For Internal Use Only (for now)  \n"
        f"Creative Commons Zero v1.0 Universal (CC0 1.0)\n"
    )

    sections.append("## Executive Summary\n\n_TODO: Summarize goals, repository, and recommendations._\n")
    sections.append("### Repodive Goals\n\n_TODO: List goals guiding this analysis._\n")

    sections.append("## Repository Overview\n")
    sections.append(f"**Repository:** `{github_repo}`  \n**Local path analyzed:** `{repo_path}`\n")
    sections.append("_TODO: Add a short description of the repository._\n")

    sections.append("## OSPO Results\n\n_TODO: Identify maturity model tier and reasoning._\n")

    sections.append("## Recommendations\n\n### Recommendation #1\n\n### Recommendation #2\n\n### Follow-up Questions\n")

    sections.append("## Analysis\n")

    sections.append(render_code_breakdown_section(results.get("scc_report")))

    sections.append("### Development Activity\n")
    sections.append(render_pr_section(results.get("github_prs")))
    sections.append(render_commits_section(results.get("git_commits")))
    sections.append(render_bus_factor_section(results.get("git_commits")))
    sections.append(render_issues_section(results.get("github_issues")))
    sections.append(render_releases_section(results.get("releases")))
    sections.append(render_ai_usage_section(results.get("ai_usage")))

    sections.append("### Engineering Best Practices\n\n_TODO: manual review required per template guidance._\n")

    sections.append(render_hygiene_section(results.get("hygiene")))

    sections.append(render_security_scan_section(results.get("security_scan")))

    sections.append("### Contributors / Staffing\n\n_TODO: cross-reference with contract staffing list._\n")

    sections.append(render_costs_section(results.get("cocomo_locomo"), github_repo))

    return "\n".join(sections)


def print_run_summary(results: dict) -> bool:
    """
    Prints a clear end-of-run summary of which analyzers succeeded vs.
    failed, so a partial failure doesn't get buried in scrolled-past
    console output. Returns True if ALL analyzers succeeded, False if any
    failed — used by main() to set the process exit code.
    """
    succeeded = [name for name, payload in results.items() if payload is not None]
    failed = [name for name, payload in results.items() if payload is None]

    print("\n" + "=" * 60)
    print("RUN SUMMARY")
    print("=" * 60)
    print(f"  Succeeded ({len(succeeded)}/{len(results)}): {', '.join(succeeded) if succeeded else '(none)'}")
    if failed:
        print(f"  FAILED    ({len(failed)}/{len(results)}): {', '.join(failed)}")
        print(
            "\n  The report was still generated, but the sections above show "
            "placeholder text instead of real data. Scroll up to the "
            "'[error]' lines for each failed analyzer's specific exception, "
            "or re-run that analyzer standalone for a clearer traceback, e.g.:"
        )
        for name in failed:
            print(f"      python analyzers/{name}.py --help")
    else:
        print("  All analyzers completed successfully.")
    print("=" * 60)

    return len(failed) == 0


def main():
    parser = argparse.ArgumentParser(description="Run all repodive analyzers and generate a Markdown report.")
    parser.add_argument("--repo-path", required=True, help="Path to the locally cloned repository.")
    parser.add_argument("--github-repo", required=True, help="GitHub repo in 'org/name' format.")
    parser.add_argument("--output", default="./output", help="Base output directory (default: ./output)")
    parser.add_argument(
        "--cocomo-mode",
        choices=["organic", "semi-detached", "embedded"],
        default="organic",
        help="COCOMO project mode passed through to cocomo_locomo.py (default: organic).",
    )
    args = parser.parse_args()

    json_output_dir = str(Path(args.output) / "json")
    results = run_all_analyzers(args.repo_path, args.github_repo, json_output_dir, cocomo_mode=args.cocomo_mode)

    report_md = render_report(results, args.repo_path, args.github_repo)

    report_path = Path(args.output) / "report.md"
    report_path.parent.mkdir(parents=True, exist_ok=True)
    with open(report_path, "w", encoding="utf-8") as f:
        f.write(report_md)

    print(f"\n[ok] Report written to {report_path}")

    all_succeeded = print_run_summary(results)
    if not all_succeeded:
        sys.exit(1)


if __name__ == "__main__":
    main()