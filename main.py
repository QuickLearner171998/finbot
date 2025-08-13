import argparse
import logging
import os
from datetime import datetime
from logging_config import setup_logging
from schemas import InputProfile, AnalysisBundle, ExtendedAnalysisBundle
from orchestrator import build_graph, fill_missing_decision_fields
from tools.report import generate_pdf_report
from tools.backtest import run_backtest


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

    bundle: ExtendedAnalysisBundle = ExtendedAnalysisBundle(
        input=result["ticker"],
        profile=result["profile"],
        fundamentals=result["fundamentals"],
        technical=result["technical"],
        news=result["news"],
        sector_macro=result["sector_macro"],
        decision=result["decision"],
        sentiment=result.get("sentiment"),
        research=result.get("research"),
        risk=result.get("risk"),
        approval=result.get("approval"),
    )

    # Fill missing decision fields (post-processing)
    bundle.decision = fill_missing_decision_fields(
        run_dir=run_dir,
        plan=bundle.decision,
        ticker=bundle.input,
        profile=bundle.profile,
        fundamentals=bundle.fundamentals,
        technical=bundle.technical,
        news=bundle.news,
        sector_macro=bundle.sector_macro,
        stream=stream,
    )

    # Save final bundle for the run
    try:
        import json
        with open(os.path.join(run_dir, "bundle.json"), "w", encoding="utf-8") as f:
            json.dump(bundle.model_dump(), f, indent=2, ensure_ascii=False)
    except Exception as e:
        logger.debug("Failed to write bundle.json: %s", e)

    conf_str = f"{bundle.decision.confidence:.2f}" if bundle.decision.confidence is not None else "N/A"
    logger.info("Decision: %s (confidence=%s)", bundle.decision.decision or "N/A", conf_str)
    print("\n=== Final Decision ===")
    print(f"{bundle.input.name} ({bundle.input.yf_symbol}) -> {bundle.decision.decision or 'N/A'} | confidence {conf_str}")
    print(f"Entry: {bundle.decision.entry_timing or 'N/A'} | Size: {bundle.decision.position_size or 'N/A'}")
    print(f"Rationale: {bundle.decision.rationale or 'N/A'}")
    print("\n=== News Summary ===")
    print(bundle.news.summary)
    if bundle.sentiment:
        print("\n=== Sentiment ===")
        print(f"Score: {bundle.sentiment.score:.2f} | Drivers: ", ", ".join(bundle.sentiment.drivers))
    if bundle.research:
        print("\n=== Research Debate ===")
        print("Bull:")
        for p in (bundle.research.bull_points or [])[:5]:
            print("-", p)
        print("Bear:")
        for p in (bundle.research.bear_points or [])[:5]:
            print("-", p)
        print("Consensus:", bundle.research.consensus)
    if bundle.risk:
        print("\n=== Risk Assessment ===")
        print(f"Level: {bundle.risk.overall_risk} | Veto: {bundle.risk.veto}")
        for p in (bundle.risk.issues or [])[:5]:
            print("-", p)
    if bundle.approval:
        print("\n=== Fund Manager ===")
        print(f"Approved: {bundle.approval.approved} | Notes: {bundle.approval.notes}")


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
    parser.add_argument(
        "--pdf",
        action="store_true",
        help="Generate a final PDF report under the run directory",
    )
    parser.add_argument(
        "--backtest",
        action="store_true",
        help="Run a simple MACD backtest for the resolved symbol and print metrics",
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
    
    # After run completes, optionally produce a PDF report
    if args.pdf:
        try:
            safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in args.company).strip("_")
            runs_root = os.path.join("runs")
            candidates = [d for d in os.listdir(runs_root) if d.endswith(safe_name) and os.path.isdir(os.path.join(runs_root, d))]
            candidates.sort(reverse=True)
            run_dir = os.path.join(runs_root, candidates[0]) if candidates else runs_root
            pdf_path = generate_pdf_report(run_dir)
            logging.getLogger("finbot").info("Saved PDF report: %s", pdf_path)
        except Exception as e:
            logging.getLogger("finbot").error("Failed to create PDF report: %s", e)

    if args.backtest:
        try:
            # Read the last run's ticker to get the symbol
            runs_root = os.path.join("runs")
            dirs = [d for d in os.listdir(runs_root) if os.path.isdir(os.path.join(runs_root, d))]
            dirs.sort(reverse=True)
            latest = os.path.join(runs_root, dirs[0]) if dirs else None
            symbol = None
            if latest:
                import json
                with open(os.path.join(latest, "ticker.json"), "r", encoding="utf-8") as f:
                    symbol = json.load(f).get("yf_symbol")
            symbol = symbol or args.company
            result = run_backtest(symbol)
            if result:
                print("\n=== Backtest (MACD) ===")
                print(f"{result.symbol}: {result.start} → {result.end} | CR {result.cumulative_return_pct}% | SR {result.sharpe_ratio:.2f} | MDD {result.max_drawdown_pct}% | Trades {result.num_trades}")
            else:
                print("Backtest: not available (insufficient data)")
        except Exception as e:
            logging.getLogger("finbot").error("Backtest failed: %s", e)
