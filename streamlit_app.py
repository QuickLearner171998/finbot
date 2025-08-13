import streamlit as st
import plotly.graph_objects as go
from logging_config import setup_logging
import schemas as schemas_mod
from orchestrator import build_graph, fill_missing_decision_fields
from tools.report import generate_markdown_report, convert_markdown_to_pdf
from tools.prices import fetch_history
import time
import os
import json
import threading

logger = setup_logging()

st.set_page_config(page_title="FinBot India Advisor", layout="wide")

st.title("FinBot – India Long-term Advisor")

# Custom CSS for better UI
st.markdown("""
<style>
    .advisor-section {
        padding: 10px;
        border-radius: 5px;
        margin-bottom: 10px;
    }
    .loading {
        color: #808080;
        font-style: italic;
    }
    .complete {
        border-left: 4px solid #4CAF50;
        padding-left: 10px;
    }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    company = st.text_input("Company name(s) (comma-separated)", "Reliance Industries, TCS, HDFC Bank")
    risk = st.selectbox("Risk level", ["low", "medium", "high"], index=1)
    horizon = st.slider("Horizon (years)", 1.0, 5.0, 2.0, 0.5)
    run = st.button("Analyze")

if run:
    names = [c.strip() for c in company.split(",") if c.strip()]
    tabs = st.tabs([n for n in names])
    for tab, name in zip(tabs, names):
        with tab:
            graph = build_graph()
            state = {
                "company_name": name,
                "profile": schemas_mod.InputProfile(risk_level=risk, horizon_years=horizon),
                "stream": True,
                "committee_rounds": 1,
            }
            
            # Create placeholders for each advisor section
            st.subheader(f"Analyzing {name}...")
            progress_bar = st.progress(0)
            
            # Create section containers with loading indicators
            ticker_section = st.container()
            fundamentals_section = st.container()
            technical_section = st.container()
            news_section = st.container()
            sector_macro_section = st.container()
            sentiment_section = st.container()
            research_section = st.container()
            risk_section = st.container()
            traders_section = st.container()
            decision_section = st.container()
            
            with ticker_section:
                st.markdown("<div class='advisor-section'><h3>Company Information</h3><p class='loading'>Loading...</p></div>", unsafe_allow_html=True)
            
            with fundamentals_section:
                st.markdown("<div class='advisor-section'><h3>Fundamentals Analysis</h3><p class='loading'>Loading...</p></div>", unsafe_allow_html=True)
                
            with technical_section:
                st.markdown("<div class='advisor-section'><h3>Technical Analysis</h3><p class='loading'>Loading...</p></div>", unsafe_allow_html=True)
                
            with news_section:
                st.markdown("<div class='advisor-section'><h3>News Analysis</h3><p class='loading'>Loading...</p></div>", unsafe_allow_html=True)
                
            with sector_macro_section:
                st.markdown("<div class='advisor-section'><h3>Sector & Macro Analysis</h3><p class='loading'>Loading...</p></div>", unsafe_allow_html=True)
                
            with sentiment_section:
                st.markdown("<div class='advisor-section'><h3>Sentiment Analysis</h3><p class='loading'>Loading...</p></div>", unsafe_allow_html=True)
                
            with research_section:
                st.markdown("<div class='advisor-section'><h3>Research Debate</h3><p class='loading'>Loading...</p></div>", unsafe_allow_html=True)
                
            with risk_section:
                st.markdown("<div class='advisor-section'><h3>Risk Assessment</h3><p class='loading'>Loading...</p></div>", unsafe_allow_html=True)
                
            with traders_section:
                st.markdown("<div class='advisor-section'><h3>Trader Signals</h3><p class='loading'>Loading...</p></div>", unsafe_allow_html=True)
                
            with decision_section:
                st.markdown("<div class='advisor-section'><h3>Final Decision</h3><p class='loading'>Loading...</p></div>", unsafe_allow_html=True)
            
            # Define a callback function to update UI as results come in
            def on_update(state):
                progress = 0
                
                # Update ticker info
                if "ticker" in state:
                    progress += 10
                    with ticker_section:
                        st.markdown(f"<div class='advisor-section complete'><h3>Company Information</h3></div>", unsafe_allow_html=True)
                        st.markdown(f"**{state['ticker'].name} ({state['ticker'].yf_symbol})**")
                        if state['ticker'].exchange:
                            st.markdown(f"Exchange: {state['ticker'].exchange}")
                
                # Update fundamentals
                if "fundamentals" in state:
                    progress += 10
                    with fundamentals_section:
                        st.markdown(f"<div class='advisor-section complete'><h3>Fundamentals Analysis</h3></div>", unsafe_allow_html=True)
                        f = state["fundamentals"]
                        if f.metrics:
                            st.json(f.metrics)
                        st.markdown("**Pros**")
                        st.write("\n".join([f"- {p}" for p in f.pros]) or "-")
                        st.markdown("**Cons**")
                        st.write("\n".join([f"- {c}" for c in f.cons]) or "-")
                        if f.notes:
                            st.markdown("**Notes**")
                            st.write(f.notes)
                
                # Update technical analysis
                if "technical" in state:
                    progress += 10
                    with technical_section:
                        st.markdown(f"<div class='advisor-section complete'><h3>Technical Analysis</h3></div>", unsafe_allow_html=True)
                        t = state["technical"]
                        st.markdown(f"**Trend**: {t.trend}")
                        if t.metrics:
                            st.json(t.metrics)
                        st.markdown("**Pros**")
                        st.write("\n".join([f"- {p}" for p in t.pros]) or "-")
                        st.markdown("**Cons**")
                        st.write("\n".join([f"- {c}" for c in t.cons]) or "-")
                        
                        # Show price chart
                        if "ticker" in state:
                            sym = state["ticker"].yf_symbol
                            df = fetch_history(sym, period="2y")
                            if df is not None and len(df) > 0:
                                close = df["Close"].dropna()
                                ma50 = close.rolling(50).mean()
                                ma200 = close.rolling(200).mean()
                                fig = go.Figure()
                                fig.add_trace(go.Scatter(x=close.index, y=close.values, name="Close"))
                                fig.add_trace(go.Scatter(x=ma50.index, y=ma50.values, name="MA50"))
                                fig.add_trace(go.Scatter(x=ma200.index, y=ma200.values, name="MA200"))
                                st.plotly_chart(fig, use_container_width=True)
                            else:
                                st.info("No price history available.")
                
                # Update news
                if "news" in state:
                    progress += 10
                    with news_section:
                        st.markdown(f"<div class='advisor-section complete'><h3>News Analysis</h3></div>", unsafe_allow_html=True)
                        st.write(state["news"].summary)
                        if state["news"].items:
                            for n in state["news"].items:
                                st.markdown(f"- [{n.title}]({n.url}) · {n.source or ''} {n.published_at or ''}")
                
                # Update sector/macro
                if "sector_macro" in state:
                    progress += 10
                    with sector_macro_section:
                        st.markdown(f"<div class='advisor-section complete'><h3>Sector & Macro Analysis</h3></div>", unsafe_allow_html=True)
                        st.write(state["sector_macro"].summary)
                
                # Update sentiment
                if "sentiment" in state:
                    progress += 10
                    with sentiment_section:
                        st.markdown(f"<div class='advisor-section complete'><h3>Sentiment Analysis</h3></div>", unsafe_allow_html=True)
                        s = state["sentiment"]
                        st.markdown(f"**Score**: {s.score:.2f} (-1.0 to 1.0)")
                        st.markdown("**Drivers**")
                        st.write("\n".join([f"- {d}" for d in s.drivers]) or "-")
                        if s.summary:
                            st.write(s.summary)
                
                # Update research debate
                if "research" in state:
                    progress += 10
                    with research_section:
                        st.markdown(f"<div class='advisor-section complete'><h3>Research Debate</h3></div>", unsafe_allow_html=True)
                        r = state["research"]
                        col1, col2 = st.columns(2)
                        with col1:
                            st.markdown("**Bull Case**")
                            st.write("\n".join([f"- {p}" for p in r.bull_points]) or "-")
                        with col2:
                            st.markdown("**Bear Case**")
                            st.write("\n".join([f"- {p}" for p in r.bear_points]) or "-")
                        st.markdown("**Consensus**")
                        st.write(r.consensus)
                
                # Update risk assessment
                if "risk" in state:
                    progress += 10
                    with risk_section:
                        st.markdown(f"<div class='advisor-section complete'><h3>Risk Assessment</h3></div>", unsafe_allow_html=True)
                        r = state["risk"]
                        st.markdown(f"**Overall Risk**: {r.overall_risk.upper()}")
                        st.markdown("**Issues**")
                        st.write("\n".join([f"- {i}" for i in r.issues]) or "None identified")
                        if r.constraints:
                            st.markdown("**Constraints**")
                            for k, v in r.constraints.items():
                                st.markdown(f"- {k}: {v}")
                        if r.veto:
                            st.error("⚠️ Risk manager has issued a VETO on this investment")
                
                # Update trader signals
                if "trader_signals" in state:
                    progress += 10
                    with traders_section:
                        st.markdown(f"<div class='advisor-section complete'><h3>Trader Signals</h3></div>", unsafe_allow_html=True)
                        signals = state["trader_signals"]
                        for i, signal in enumerate(signals.signals):
                            st.markdown(f"**Trader {i+1} ({signal.risk_profile})**")
                            st.markdown(f"- Action: {signal.action}")
                            st.markdown(f"- Confidence: {signal.confidence:.2f}")
                            if signal.entry_timing:
                                st.markdown(f"- Entry: {signal.entry_timing}")
                            if signal.position_size:
                                st.markdown(f"- Position Size: {signal.position_size}")
                            if signal.rationale:
                                st.markdown(f"- Rationale: {signal.rationale}")
                        
                        st.markdown("**Consensus**")
                        st.markdown(f"- Action: {signals.consensus_action}")
                        st.markdown(f"- Confidence: {signals.consensus_confidence:.2f}")
                        if signals.notes:
                            st.markdown(f"- Notes: {signals.notes}")
                
                # Update decision
                if "decision" in state:
                    progress += 10
                    with decision_section:
                        st.markdown(f"<div class='advisor-section complete'><h3>Final Decision</h3></div>", unsafe_allow_html=True)
                        d = state["decision"]
                        st.markdown(f"**Decision**: {d.decision}")
                        st.markdown(f"**Confidence**: {d.confidence:.2f if isinstance(d.confidence, float) else d.confidence}")
                        st.markdown(f"**Entry**: {d.entry_timing or 'Not specified'}")
                        st.markdown(f"**Position Size**: {d.position_size or 'Not specified'}")
                        if d.dca_plan:
                            st.markdown(f"**DCA Plan**: {d.dca_plan}")
                        if d.risk_controls:
                            st.markdown("**Risk Controls**:")
                            for k, v in d.risk_controls.items():
                                st.markdown(f"- {k}: {v}")
                        st.markdown("**Rationale**")
                        st.write(d.rationale or "No rationale provided")
                
                # Update progress bar
                progress_bar.progress(min(progress, 100))
                
            # Create a placeholder for the graph execution
            status_text = st.empty()
            
            # Start the graph execution in a separate thread
            result_container = {"result": None, "current_state": {}}
            
            def run_graph():
                result_container["result"] = graph.invoke(state)
            
            thread = threading.Thread(target=run_graph)
            thread.start()
            
            # Poll for updates while the graph is running
            while thread.is_alive():
                status_text.text("Analysis in progress...")
                
                # Get the latest state from the run directory
                run_dir = os.path.join("runs", f"streamlit_{name.replace(' ', '_')}")
                if os.path.exists(run_dir):
                    # Check for ticker.json
                    if os.path.exists(os.path.join(run_dir, "ticker.json")) and "ticker" not in result_container["current_state"]:
                        with open(os.path.join(run_dir, "ticker.json"), "r") as f:
                            result_container["current_state"]["ticker"] = schemas_mod.TickerInfo(**json.load(f))
                            on_update(result_container["current_state"])
                    
                    # Check for fundamentals.json
                    if os.path.exists(os.path.join(run_dir, "fundamentals.json")) and "fundamentals" not in result_container["current_state"]:
                        with open(os.path.join(run_dir, "fundamentals.json"), "r") as f:
                            result_container["current_state"]["fundamentals"] = schemas_mod.FundamentalsReport(**json.load(f))
                            on_update(result_container["current_state"])
                    
                    # Check for technical.json
                    if os.path.exists(os.path.join(run_dir, "technical.json")) and "technical" not in result_container["current_state"]:
                        with open(os.path.join(run_dir, "technical.json"), "r") as f:
                            result_container["current_state"]["technical"] = schemas_mod.TechnicalReport(**json.load(f))
                            on_update(result_container["current_state"])
                    
                    # Check for news.json
                    if os.path.exists(os.path.join(run_dir, "news.json")) and "news" not in result_container["current_state"]:
                        with open(os.path.join(run_dir, "news.json"), "r") as f:
                            result_container["current_state"]["news"] = schemas_mod.NewsReport(**json.load(f))
                            on_update(result_container["current_state"])
                    
                    # Check for sector_macro.json
                    if os.path.exists(os.path.join(run_dir, "sector_macro.json")) and "sector_macro" not in result_container["current_state"]:
                        with open(os.path.join(run_dir, "sector_macro.json"), "r") as f:
                            result_container["current_state"]["sector_macro"] = schemas_mod.SectorMacroReport(**json.load(f))
                            on_update(result_container["current_state"])
                    
                    # Check for sentiment.json
                    if os.path.exists(os.path.join(run_dir, "sentiment.json")) and "sentiment" not in result_container["current_state"]:
                        with open(os.path.join(run_dir, "sentiment.json"), "r") as f:
                            result_container["current_state"]["sentiment"] = schemas_mod.SentimentReport(**json.load(f))
                            on_update(result_container["current_state"])
                    
                    # Check for research.json
                    if os.path.exists(os.path.join(run_dir, "research.json")) and "research" not in result_container["current_state"]:
                        with open(os.path.join(run_dir, "research.json"), "r") as f:
                            result_container["current_state"]["research"] = schemas_mod.ResearchDebateReport(**json.load(f))
                            on_update(result_container["current_state"])
                    
                    # Check for risk.json
                    if os.path.exists(os.path.join(run_dir, "risk.json")) and "risk" not in result_container["current_state"]:
                        with open(os.path.join(run_dir, "risk.json"), "r") as f:
                            result_container["current_state"]["risk"] = schemas_mod.RiskAssessment(**json.load(f))
                            on_update(result_container["current_state"])
                    
                    # Check for traders_signals.json and traders_ensemble.json
                    if os.path.exists(os.path.join(run_dir, "traders_signals.json")) and os.path.exists(os.path.join(run_dir, "traders_ensemble.json")) and "trader_signals" not in result_container["current_state"]:
                        with open(os.path.join(run_dir, "traders_ensemble.json"), "r") as f:
                            result_container["current_state"]["trader_signals"] = schemas_mod.TraderEnsemble(**json.load(f))
                            on_update(result_container["current_state"])
                    
                    # Check for decision.json
                    if os.path.exists(os.path.join(run_dir, "decision.json")) and "decision" not in result_container["current_state"]:
                        with open(os.path.join(run_dir, "decision.json"), "r") as f:
                            result_container["current_state"]["decision"] = schemas_mod.DecisionPlan(**json.load(f))
                            on_update(result_container["current_state"])
                
                # Sleep for a short time before polling again
                time.sleep(1)
            
            # Thread is done, get the final result
            status_text.empty()
            result = result_container["result"]

            # Final summary section after all analysis is complete
            st.markdown("---")
            st.subheader("Summary Dashboard")
            
            # Create a dashboard layout with the most important information
            col1, col2 = st.columns([2, 1])

            with col1:
                d = result["decision"]
                st.markdown(f"### {result['ticker'].name} ({result['ticker'].yf_symbol})")
                
                # Create a colored box based on decision
                decision_color = "green" if d.decision == "Buy" else "orange" if d.decision == "Hold" else "red"
                st.markdown(f"""
                <div style="padding: 10px; background-color: {decision_color}; color: white; border-radius: 5px; margin-bottom: 10px;">
                    <h2 style="margin: 0; text-align: center;">{d.decision}</h2>
                </div>
                """, unsafe_allow_html=True)
                
                # Key metrics in a clean format
                st.markdown(f"**Confidence**: {d.confidence:.2f if isinstance(d.confidence, float) else d.confidence}")
                st.markdown(f"**Entry Timing**: {d.entry_timing or 'Not specified'}")
                st.markdown(f"**Position Size**: {d.position_size or 'Not specified'}")
                
                if d.dca_plan:
                    st.markdown(f"**DCA Plan**: {d.dca_plan}")
                    
                if d.risk_controls:
                    st.markdown("**Risk Controls**:")
                    for k, v in d.risk_controls.items():
                        st.markdown(f"- {k}: {v}")
                        
                # Rationale in a box
                st.markdown("""<div style="border: 1px solid #ddd; border-radius: 5px; padding: 10px; margin-top: 10px;">""")
                st.markdown("**Investment Rationale**")
                st.write(d.rationale or "No rationale provided")
                st.markdown("</div>", unsafe_allow_html=True)

            with col2:
                # Price chart in the sidebar
                st.markdown("**Price Chart (2Y)**")
                sym = result["ticker"].yf_symbol
                df = fetch_history(sym, period="2y")
                if df is not None and len(df) > 0:
                    close = df["Close"].dropna()
                    ma50 = close.rolling(50).mean()
                    ma200 = close.rolling(200).mean()
                    fig = go.Figure()
                    fig.add_trace(go.Scatter(x=close.index, y=close.values, name="Close"))
                    fig.add_trace(go.Scatter(x=ma50.index, y=ma50.values, name="MA50"))
                    fig.add_trace(go.Scatter(x=ma200.index, y=ma200.values, name="MA200"))
                    fig.update_layout(margin=dict(l=0, r=0, t=0, b=0), height=300)
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No price history available.")

                # Risk assessment summary if available
                if "risk" in result:
                    r = result["risk"]
                    risk_color = "green" if r.overall_risk == "low" else "orange" if r.overall_risk == "medium" else "red"
                    st.markdown(f"""
                    <div style="padding: 5px; background-color: {risk_color}; color: white; border-radius: 5px; margin-bottom: 10px; text-align: center;">
                        <h4 style="margin: 0;">Risk: {r.overall_risk.upper()}</h4>
                    </div>
                    """, unsafe_allow_html=True)

            # Alternatives removed

            # Generate and offer report downloads
            run_dir = os.path.join("runs", f"streamlit_{name.replace(' ', '_')}")
            os.makedirs(run_dir, exist_ok=True)
            # Save a lightweight bundle
            bundle = {
                "input": result["ticker"].model_dump(),
                "profile": result["profile"].model_dump(),
                "fundamentals": result["fundamentals"].model_dump(),
                "technical": result["technical"].model_dump(),
                "news": result["news"].model_dump(),
                "sector_macro": result["sector_macro"].model_dump(),
                "decision": result["decision"].model_dump(),
            }
            with open(os.path.join(run_dir, "bundle.json"), "w", encoding="utf-8") as f:
                json.dump(bundle, f, indent=2, ensure_ascii=False)

            md_path, html_path = generate_markdown_report(run_dir)
            pdf_path = convert_markdown_to_pdf(md_path)

            st.subheader("Download Reports")
            with open(md_path, "r", encoding="utf-8") as f:
                st.download_button("Download Markdown", data=f.read(), file_name=f"{name}_report.md", mime="text/markdown")
            with open(html_path, "r", encoding="utf-8") as f:
                st.download_button("Download HTML", data=f.read(), file_name=f"{name}_report.html", mime="text/html")
            with open(pdf_path, "rb") as f:
                st.download_button("Download PDF", data=f.read(), file_name=f"{name}_report.pdf", mime="application/pdf")

            st.caption("Not financial advice. For educational use only.")
