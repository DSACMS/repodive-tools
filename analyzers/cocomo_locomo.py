"""
analyzers/cocomo_locomo.py

Computes two cost/time estimate models for the Repodive Report template's
"Costs" section:

  COCOMO (If Humans Built This From Scratch)
    - Industry-standard formula (Boehm, 1981) estimating effort, schedule,
      and headcount from codebase size (KLOC).

  LOCOMO (If an AI Tool Regenerated This Code)
    - A parallel estimate: what it would cost/take for an LLM to generate
      the same code, PLUS fixed human review time layered on top. Modeled
      across three illustrative model-size tiers (Small/Medium/Large).

IMPORTANT — these are brute-force, formula-based estimates, exactly as the
template itself cautions. They count lines of code and run that count
through a formula; they know nothing about code difficulty, team
staffing history, or whether the codebase includes untouched vendored
code. See the template's own "Why These Are Brute Force Numbers" section,
reproduced in the rendered report output.

Dependency: this analyzer consumes the ULOC and language breakdown
produced by scc_report.py rather than re-running scc itself. Run
scc_report.py first (or via the orchestrator, which always runs it
first) so its JSON output is available at
<output_dir>/scc_report.json.

COCOMO constants (Basic COCOMO, Boehm 1981):
    Effort (person-months) = a * (KLOC)^b
    Schedule (months)      = c * (Effort)^d
    People required        = Effort / Schedule

    Mode           a     b     c     d
    Organic        2.4   1.05  2.5   0.38   <- small, experienced team (default)
    Semi-detached  3.0   1.12  2.5   0.35   <- medium team/complexity
    Embedded       3.6   1.20  2.5   0.32   <- tight constraints, high complexity

LOCOMO constants (documented, clearly-labeled assumptions — NOT live
pricing; override via --tokens-per-line, --review-loc-per-hour, or by
editing MODEL_TIERS below if your organization has better figures):
    - ~10 tokens per line of code (rule of thumb for code, vs ~0.75
      words/token for prose)
    - 3 illustrative model tiers with distinct $/1M output tokens and
      generation speed (tokens/sec)
    - Fixed human review pace: 300 lines/hour (commonly cited sustainable
      careful-review rate; some cite 200-400 LOC/hr depending on rigor)

Runs standalone:
    python analyzers/cocomo_locomo.py --repo-path ./cloned-repos/repodive-tools \\
        --output ./output/json --mode organic

Or imported by orchestrator.py via `run(repo_path, output_dir, scc_data)`.
"""

import argparse
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parent.parent))
from config import (
    make_output,
    write_analyzer_output,
    load_analyzer_output,
    add_local_repo_arg,
    add_output_arg,
)

# ---------------------------------------------------------------------------
# COCOMO constants
# ---------------------------------------------------------------------------

COCOMO_MODES = {
    "organic": {"a": 2.4, "b": 1.05, "c": 2.5, "d": 0.38},
    "semi-detached": {"a": 3.0, "b": 1.12, "c": 2.5, "d": 0.35},
    "embedded": {"a": 3.6, "b": 1.20, "c": 2.5, "d": 0.32},
}


DEFAULT_AVG_MONTHLY_COST_USD = 16_000


# ---------------------------------------------------------------------------
# LOCOMO constants
# ---------------------------------------------------------------------------

DEFAULT_TOKENS_PER_LINE = 10
DEFAULT_REVIEW_LOC_PER_HOUR = 300
DEFAULT_REVIEWER_HOURLY_RATE_USD = 85

MODEL_TIERS = {
    "small": {
        "label": "LLM - Small",
        "cost_per_1m_output_tokens_usd": 0.80,
        "tokens_per_second": 150,
    },
    "medium": {
        "label": "LLM - Medium",
        "cost_per_1m_output_tokens_usd": 4.00,
        "tokens_per_second": 80,
    },
    "large": {
        "label": "LLM - Large",
        "cost_per_1m_output_tokens_usd": 18.00,
        "tokens_per_second": 40,
    },
}

# ---------------------------------------------------------------------------
# COCOMO
# ---------------------------------------------------------------------------

def compute_cocomo(uloc: int, mode: str, avg_monthly_cost_usd: float) -> dict:
    """
    Computes Basic COCOMO effort/schedule/people/cost for a given unique-
    lines-of-code count and project mode (organic/semi-detached/embedded).
    """
    if mode not in COCOMO_MODES:
        raise ValueError(f"Unknown COCOMO mode '{mode}'. Choose from: {list(COCOMO_MODES)}")

    params = COCOMO_MODES[mode]
    kloc = uloc / 1000.0

    effort_person_months = params["a"] * (kloc ** params["b"])
    schedule_months = params["c"] * (effort_person_months ** params["d"])
    people_required = effort_person_months / schedule_months if schedule_months else None
    estimated_cost_usd = effort_person_months * avg_monthly_cost_usd

    return {
        "mode": mode,
        "uloc": uloc,
        "kloc": round(kloc, 2),
        "effort_person_months": round(effort_person_months, 1),
        "schedule_months": round(schedule_months, 1),
        "people_required": round(people_required, 1) if people_required else None,
        "avg_monthly_cost_usd": avg_monthly_cost_usd,
        "estimated_cost_usd": round(estimated_cost_usd, 2),
    }


# ---------------------------------------------------------------------------
# LOCOMO
# ---------------------------------------------------------------------------

def compute_locomo_tier(
    uloc: int,
    tier_key: str,
    tokens_per_line: float,
    review_loc_per_hour: float,
    reviewer_hourly_rate_usd: float,
) -> dict:
    """Computes generation cost/time + fixed human review time for one model tier."""
    tier = MODEL_TIERS[tier_key]

    total_tokens = uloc * tokens_per_line
    generation_seconds = total_tokens / tier["tokens_per_second"]
    generation_hours = generation_seconds / 3600.0
    generation_cost_usd = (total_tokens / 1_000_000) * tier["cost_per_1m_output_tokens_usd"]

    review_hours = uloc / review_loc_per_hour if review_loc_per_hour else 0
    review_cost_usd = review_hours * reviewer_hourly_rate_usd

    total_hours = generation_hours + review_hours
    total_cost_usd = generation_cost_usd + review_cost_usd
    review_pct_of_total = (review_hours / total_hours * 100) if total_hours else None

    return {
        "tier": tier_key,
        "label": tier["label"],
        "total_tokens": round(total_tokens),
        "generation_hours": round(generation_hours, 2),
        "generation_cost_usd": round(generation_cost_usd, 2),
        "review_hours": round(review_hours, 1),
        "review_cost_usd": round(review_cost_usd, 2),
        "total_hours": round(total_hours, 1),
        "total_days": round(total_hours / 24, 1),
        "total_cost_usd": round(total_cost_usd, 2),
        "review_pct_of_total": round(review_pct_of_total, 1) if review_pct_of_total is not None else None,
    }


def compute_locomo(
    uloc: int,
    tokens_per_line: float = DEFAULT_TOKENS_PER_LINE,
    review_loc_per_hour: float = DEFAULT_REVIEW_LOC_PER_HOUR,
    reviewer_hourly_rate_usd: float = DEFAULT_REVIEWER_HOURLY_RATE_USD,
) -> dict:
    """Computes all three LOCOMO model tiers for a given ULOC count."""
    tiers = {}
    for tier_key in MODEL_TIERS:
        tiers[tier_key] = compute_locomo_tier(
            uloc, tier_key, tokens_per_line, review_loc_per_hour, reviewer_hourly_rate_usd
        )

    return {
        "assumptions": {
            "tokens_per_line": tokens_per_line,
            "review_loc_per_hour": review_loc_per_hour,
            "reviewer_hourly_rate_usd": reviewer_hourly_rate_usd,
            "model_tiers": MODEL_TIERS,
        },
        "tiers": tiers,
    }


# ---------------------------------------------------------------------------
# Orchestration
# ---------------------------------------------------------------------------

def get_uloc_from_scc_data(scc_payload: dict) -> int:
    """
    Extracts total code lines (used as our ULOC proxy) from a scc_report.py
    JSON payload. Per project decision, we use scc's totals as-is (scc's
    own --exclude-dir handling already strips common vendor/generated
    directories at the scc_report.py layer).
    """
    if not scc_payload or "data" not in scc_payload:
        raise ValueError(
            "No scc_report data available. Run analyzers/scc_report.py first — "
            "cocomo_locomo.py depends on its ULOC output."
        )
    return scc_payload["data"]["totals"]["code"]


def analyze(
    uloc: int,
    mode: str = "organic",
    avg_monthly_cost_usd: float = DEFAULT_AVG_MONTHLY_COST_USD,
    tokens_per_line: float = DEFAULT_TOKENS_PER_LINE,
    review_loc_per_hour: float = DEFAULT_REVIEW_LOC_PER_HOUR,
    reviewer_hourly_rate_usd: float = DEFAULT_REVIEWER_HOURLY_RATE_USD,
) -> dict:
    cocomo = compute_cocomo(uloc, mode, avg_monthly_cost_usd)
    locomo = compute_locomo(uloc, tokens_per_line, review_loc_per_hour, reviewer_hourly_rate_usd)

    # Side-by-side comparison rows, directly mirroring the template's
    # "Human vs. LLM Cost & Time" table (Human COCOMO | LLM Small | Medium | Large).
    comparison_rows = [
        {
            "metric": "Generation Time (serial)",
            "human": f"{cocomo['schedule_months']} months",
            "llm_small": f"{locomo['tiers']['small']['generation_hours']} hrs",
            "llm_medium": f"{locomo['tiers']['medium']['generation_hours']} hrs",
            "llm_large": f"{locomo['tiers']['large']['generation_hours']} hrs",
        },
        {
            "metric": "Human Review Time",
            "human": "—",
            "llm_small": f"{locomo['tiers']['small']['review_hours']} hrs",
            "llm_medium": f"{locomo['tiers']['medium']['review_hours']} hrs",
            "llm_large": f"{locomo['tiers']['large']['review_hours']} hrs",
        },
        {
            "metric": "Total Time to Delivery",
            "human": f"{round(cocomo['schedule_months'] * 30.44)} days ({cocomo['schedule_months']} mo.)",
            "llm_small": f"{locomo['tiers']['small']['total_days']} days",
            "llm_medium": f"{locomo['tiers']['medium']['total_days']} days",
            "llm_large": f"{locomo['tiers']['large']['total_days']} days",
        },
        {
            "metric": "Review Time as % of LLM Total",
            "human": "—",
            "llm_small": f"{locomo['tiers']['small']['review_pct_of_total']}%",
            "llm_medium": f"{locomo['tiers']['medium']['review_pct_of_total']}%",
            "llm_large": f"{locomo['tiers']['large']['review_pct_of_total']}%",
        },
        {
            "metric": "Estimated Cost",
            "human": f"${cocomo['estimated_cost_usd']:,.2f}",
            "llm_small": f"${locomo['tiers']['small']['total_cost_usd']:,.2f}",
            "llm_medium": f"${locomo['tiers']['medium']['total_cost_usd']:,.2f}",
            "llm_large": f"${locomo['tiers']['large']['total_cost_usd']:,.2f}",
        },
    ]

    review_pcts = [t["review_pct_of_total"] for t in locomo["tiers"].values() if t["review_pct_of_total"] is not None]

    return {
        "uloc": uloc,
        "cocomo": cocomo,
        "locomo": locomo,
        "comparison_table": comparison_rows,
        "review_pct_range": {
            "min": round(min(review_pcts), 1) if review_pcts else None,
            "max": round(max(review_pcts), 1) if review_pcts else None,
        },
    }


def run(
    repo_path: str,
    output_dir: str,
    mode: str = "organic",
    avg_monthly_cost_usd: float = DEFAULT_AVG_MONTHLY_COST_USD,
    tokens_per_line: float = DEFAULT_TOKENS_PER_LINE,
    review_loc_per_hour: float = DEFAULT_REVIEW_LOC_PER_HOUR,
    reviewer_hourly_rate_usd: float = DEFAULT_REVIEWER_HOURLY_RATE_USD,
) -> dict:
    """
    Entry point used by orchestrator.py. Reads scc_report.json from
    output_dir (must have been written already — the orchestrator always
    runs scc_report before cocomo_locomo) to get ULOC, then computes both
    models.
    """
    scc_payload = load_analyzer_output(output_dir, "scc_report")
    uloc = get_uloc_from_scc_data(scc_payload)

    data = analyze(
        uloc,
        mode=mode,
        avg_monthly_cost_usd=avg_monthly_cost_usd,
        tokens_per_line=tokens_per_line,
        review_loc_per_hour=review_loc_per_hour,
        reviewer_hourly_rate_usd=reviewer_hourly_rate_usd,
    )
    payload = make_output("cocomo_locomo", repo_path, data)
    write_analyzer_output(output_dir, "cocomo_locomo", payload)
    return payload


def main():
    parser = argparse.ArgumentParser(
        description="Compute COCOMO (human) and LOCOMO (AI-regeneration) cost/time estimates."
    )
    add_local_repo_arg(parser)
    add_output_arg(parser)
    parser.add_argument(
        "--mode",
        choices=list(COCOMO_MODES.keys()),
        default="organic",
        help="COCOMO project mode (default: organic — small, experienced team).",
    )
    parser.add_argument(
        "--avg-monthly-cost",
        type=float,
        default=DEFAULT_AVG_MONTHLY_COST_USD,
        help=f"Fully-loaded avg monthly cost per engineer, for COCOMO $ estimate (default: ${DEFAULT_AVG_MONTHLY_COST_USD:,}).",
    )
    parser.add_argument(
        "--tokens-per-line",
        type=float,
        default=DEFAULT_TOKENS_PER_LINE,
        help=f"Tokens-per-line-of-code assumption for LOCOMO (default: {DEFAULT_TOKENS_PER_LINE}).",
    )
    parser.add_argument(
        "--review-loc-per-hour",
        type=float,
        default=DEFAULT_REVIEW_LOC_PER_HOUR,
        help=f"Human review pace in lines/hour for LOCOMO (default: {DEFAULT_REVIEW_LOC_PER_HOUR}).",
    )
    parser.add_argument(
        "--reviewer-hourly-rate",
        type=float,
        default=DEFAULT_REVIEWER_HOURLY_RATE_USD,
        help=f"Reviewer hourly rate in USD for LOCOMO review cost (default: ${DEFAULT_REVIEWER_HOURLY_RATE_USD}).",
    )
    args = parser.parse_args()

    run(
        args.repo_path,
        args.output,
        mode=args.mode,
        avg_monthly_cost_usd=args.avg_monthly_cost,
        tokens_per_line=args.tokens_per_line,
        review_loc_per_hour=args.review_loc_per_hour,
        reviewer_hourly_rate_usd=args.reviewer_hourly_rate,
    )


if __name__ == "__main__":
    main()