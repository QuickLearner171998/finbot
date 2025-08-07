import argparse
import logging
from logging_config import setup_logging
from schemas import InputProfile, AnalysisBundle
from orchestrator import build_graph


def run_once(company_name: str, risk_level: str, horizon_years: float):
    logger = setup_logging()
    logger.info("Starting analysis for %s", company_name)

    graph = build_graph()
    state = {
        "company_name": company_name,
        "profile": InputProfile(risk_level=risk_level, horizon_years=horizon_years),
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
    args = parser.parse_args()

    run_once(args.company, args.risk, args.horizon)
