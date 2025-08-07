import streamlit as st
import plotly.graph_objects as go
from logging_config import setup_logging
import schemas as schemas_mod
from orchestrator import build_graph, fill_missing_decision_fields
from tools.report import generate_markdown_report, convert_markdown_to_pdf
from tools.prices import fetch_history

logger = setup_logging()

st.set_page_config(page_title="FinBot India Advisor", layout="wide")

st.title("FinBot – India Long-term Advisor")
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
            with st.spinner(f"Analyzing {name}..."):
                result = graph.invoke(state)

            col1, col2 = st.columns([2, 1])

            with col1:
                st.subheader("Decision")
                d = result["decision"]
                st.markdown(f"**{result['ticker'].name} ({result['ticker'].yf_symbol})**")
                st.markdown(f"- **Decision**: {d.decision}")
                st.markdown(f"- **Confidence**: {d.confidence:.2f}")
                st.markdown(f"- **Entry**: {d.entry_timing}")
                st.markdown(f"- **Position Size**: {d.position_size}")
                if d.dca_plan:
                    st.markdown(f"- **DCA**: {d.dca_plan}")
                if d.risk_controls:
                    st.markdown("- **Risk Controls**:")
                    for k, v in d.risk_controls.items():
                        st.markdown(f"  - {k}: {v}")
                st.markdown("**Rationale**")
                st.write(d.rationale)

            with col2:
                st.subheader("Price & Trend")
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
                    st.plotly_chart(fig, use_container_width=True)
                else:
                    st.info("No price history available.")

            st.subheader("Fundamentals")
            f = result["fundamentals"]
            if f.metrics:
                st.json(f.metrics)
            st.markdown("**Pros**")
            st.write("\n".join([f"- {p}" for p in f.pros]) or "-")
            st.markdown("**Cons**")
            st.write("\n".join([f"- {c}" for c in f.cons]) or "-")

            st.subheader("News (Simplified)")
            st.write(result["news"].summary)
            if result["news"].items:
                for n in result["news"].items:
                    st.markdown(f"- [{n.title}]({n.url}) · {n.source or ''} {n.published_at or ''}")

            st.subheader("Sector / Macro context")
            st.write(result["sector_macro"].summary)

            st.subheader("Alternatives")
            for c in result["alternatives"].candidates:
                st.markdown(f"- **{c.name}**: {c.reason}")

            # Generate and offer report downloads
            import os, json
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
                "alternatives": result["alternatives"].model_dump(),
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
