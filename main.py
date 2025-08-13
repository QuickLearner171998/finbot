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
        "approval_attempts": 0,  # Initialize approval attempts counter
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
    parser.add_argument("company", help="Company name(s), comma-separated, e.g., 'Reliance, TCS, HDFC Bank'")
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
    
    # Split company names and process each one
    company_names = [name.strip() for name in args.company.split(',') if name.strip()]
    run_dirs = []
    
    for company_name in company_names:
        print(f"\n{'='*50}\nAnalyzing {company_name}\n{'='*50}")
        
        # Create a unique run directory for each company
        safe_name = "".join(c if c.isalnum() or c in ("-", "_") else "_" for c in company_name).strip("_")
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        run_dir = os.path.join("runs", f"{timestamp}_{safe_name}")
        run_dirs.append(run_dir)
        
        # Run analysis for this company
        run_once(
            company_name,
            args.risk,
            args.horizon,
            args.log_level,
            run_dir=run_dir,
            stream=args.stream,
            committee_rounds=args.rounds,
        )
    
    # After all runs complete, optionally produce PDF reports
    if args.pdf:
        for run_dir in run_dirs:
            try:
                pdf_path = generate_pdf_report(run_dir)
                logging.getLogger("finbot").info("Saved PDF report: %s", pdf_path)
            except Exception as e:
                logging.getLogger("finbot").error("Failed to create PDF report for %s: %s", run_dir, e)

    # Run backtest for each company if requested
    if args.backtest:
        for run_dir in run_dirs:
            try:
                # Read the ticker.json from the run directory
                symbol = None
                try:
                    import json
                    with open(os.path.join(run_dir, "ticker.json"), "r", encoding="utf-8") as f:
                        ticker_data = json.load(f)
                        symbol = ticker_data.get("yf_symbol")
                        company_name = ticker_data.get("name")
                except Exception:
                    # If ticker.json doesn't exist or is invalid, use directory name as fallback
                    company_name = os.path.basename(run_dir).split('_', 1)[1] if '_' in os.path.basename(run_dir) else os.path.basename(run_dir)
                
                if symbol:
                    result = run_backtest(symbol)
                    if result:
                        print(f"\n=== Backtest for {company_name} (MACD) ===")
                        print(f"{result.symbol}: {result.start} → {result.end} | CR {result.cumulative_return_pct}% | SR {result.sharpe_ratio:.2f} | MDD {result.max_drawdown_pct}% | Trades {result.num_trades}")
                    else:
                        print(f"\nBacktest for {company_name}: not available (insufficient data)")
            except Exception as e:
                logging.getLogger("finbot").error("Backtest failed for %s: %s", run_dir, e)
