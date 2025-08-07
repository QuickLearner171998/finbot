import argparse
import logging
import os
from datetime import datetime
from logging_config import setup_logging
from schemas import InputProfile, AnalysisBundle
from orchestrator import build_graph


def run_once(company_name: str, risk_level: str, horizon_years: float, log_level: str | int | None = None, run_dir: str | None = None, stream: bool = False, committee_rounds: int = 0):
    logger = setup_logging(level=log_level)
    logger.info("Starting analysis for %s", company_name)
    logger.debug("Input profile: risk=%s horizon=%.2f years", risk_level, horizon_years)

    # Build a unique run directory if not provided
    if not run_dir:
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in company_name).strip("_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join("runs", f"{timestamp}_{safe_name}")
    os.makedirs(run_dir, exist_ok=True)

    graph = build_graph()
    state = {
        "company_name": company_name,
        "profile": InputProfile(risk_level=risk_level, horizon_years=horizon_years),
        "run_dir": run_dir,
        "stream": stream,
        "committee_rounds": committee_rounds,
    }
    result = graph.invoke(state)

    bundle = AnalysisBundle(
        input=result["ticker"],
        profile=result["profile"],
        fundamentals=result["fundamentals"],
        technical=result["technical"],
        news=result["news"],
        sector_macro=result["sector_macro"],
        alternatives=result["alternatives"],
        decision=result["decision"],
    )

    # Save final bundle for the run
    try:
        import json
        with open(os.path.join(run_dir, "bundle.json"), "w", encoding="utf-8") as f:
            json.dump(bundle.model_dump(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.debug("Failed to write bundle.json: %s", e)

    logger.info("Decision: %s (confidence=%.2f)", bundle.decision.decision, bundle.decision.confidence)
    print("\n=== Final Decision ===")
    print(f"{bundle.input.name} ({bundle.input.yf_symbol}) -> {bundle.decision.decision} | confidence {bundle.decision.confidence:.2f}")
    print(f"Entry: {bundle.decision.entry_timing} | Size: {bundle.decision.position_size}")
    print(f"Rationale: {bundle.decision.rationale}")
    print("\n=== News Summary ===")
    print(bundle.news.summary)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Run long-term investment analysis for Indian stocks.")
    parser.add_argument("company", help="Company name, e.g., Reliance, TCS, HDFC Bank")
    parser.add_argument("--risk", default="medium", choices=["low", "medium", "high"], help="Risk level")
    parser.add_argument("--horizon", type=float, default=2.0, help="Holding horizon in years")
    parser.add_argument(
        "--log-level",
        dest="log_level",
        default=None,
        choices=["debug", "info", "warning", "error", "critical"],
        help="Logging level; defaults to env LOG_LEVEL or INFO",
    )
    parser.add_argument(
        "--stream",
        action="store_true",
        help="Stream high-level progress to console",
    )
    parser.add_argument(
        "--rounds",
        type=int,
        default=0,
        help="Number of committee critique/revision rounds",
    )
    args = parser.parse_args()

    run_once(
        args.company,
        args.risk,
        args.horizon,
        args.log_level,
        stream=args.stream,
        committee_rounds=args.rounds,
    )
