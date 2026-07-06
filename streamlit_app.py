import os
import sys
import time
import asyncio
import streamlit as st
import pandas as pd

# Fallback for Streamlit Community Cloud secrets
try:
    if "GEMINI_API_KEY" in st.secrets:
        os.environ["GEMINI_API_KEY"] = st.secrets["GEMINI_API_KEY"]
except Exception:
    pass

# Ensure we can import our agents module
parent_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.append(parent_dir)

from agents.orchestrator import run_full_pipeline

# ---------------------------------------------------------------------------
# CSS Injection
# ---------------------------------------------------------------------------
def inject_custom_css():
    st.markdown("""
        <style>
            /* Base Theme Overrides */
            .stApp {
                background-color: #0d1117 !important;
                color: #c9d1d9 !important;
            }
            .stAppHeader {
                background-color: transparent !important;
            }
            .block-container {
                padding-top: 2rem !important;
                max-width: 900px;
            }
            h1, h2, h3, h4, p, span, div {
                color: #c9d1d9 !important;
            }
            
            /* Animations */
            @keyframes fadeInUp {
                0% { opacity: 0; transform: translateY(10px); }
                100% { opacity: 1; transform: translateY(0); }
            }
            .animate-fade-in {
                animation: fadeInUp 0.22s ease-out forwards;
            }
            
            /* Header and Badges */
            .title-text {
                font-size: 2.5rem;
                font-weight: 700;
                margin-bottom: 0px;
            }
            .subtitle-text {
                color: #8b949e !important;
                font-size: 1.1rem;
                margin-bottom: 20px;
            }
            .badge-container {
                display: flex;
                gap: 10px;
                margin-bottom: 30px;
            }
            .pill-badge {
                background-color: #161b22;
                border: 1px solid #21262d;
                color: #58a6ff !important;
                padding: 4px 12px;
                border-radius: 20px;
                font-size: 0.85rem;
                font-weight: 600;
            }
            
            /* Buttons */
            .stButton > button {
                background-color: #238636 !important;
                color: #ffffff !important;
                border: 1px solid rgba(240, 246, 252, 0.1) !important;
                transition: all 150ms ease-out !important;
                border-radius: 6px !important;
            }
            .stButton > button:hover {
                background-color: #2ea043 !important;
                border-color: rgba(240, 246, 252, 0.1) !important;
            }
            .stButton > button:active {
                transform: scale(0.97) !important;
            }
            
            /* Activity Feed */
            .feed-item {
                background-color: #161b22;
                border: 1px solid #21262d;
                border-radius: 6px;
                padding: 12px 16px;
                margin-bottom: 8px;
                display: flex;
                align-items: center;
                gap: 12px;
                opacity: 0;
            }
            .feed-icon {
                color: #238636 !important;
                font-size: 1.2rem;
                min-width: 20px;
            }
            .thinking-dots {
                color: #8b949e !important;
                font-size: 1.5rem;
                line-height: 0.5;
                animation: pulse-opacity 1.2s infinite ease-in-out;
            }
            @keyframes pulse-opacity {
                0% { opacity: 0.3; }
                50% { opacity: 1; }
                100% { opacity: 0.3; }
            }
            
            /* Metric Cards */
            .metrics-grid {
                display: grid;
                grid-template-columns: repeat(4, 1fr);
                gap: 15px;
                margin-top: 30px;
                margin-bottom: 30px;
            }
            .metric-card {
                background-color: #161b22;
                border: 1px solid #21262d;
                border-radius: 8px;
                padding: 16px;
                display: flex;
                flex-direction: column;
                opacity: 0;
            }
            .metric-label {
                color: #8b949e !important;
                font-size: 0.85rem;
                text-transform: uppercase;
                letter-spacing: 0.5px;
                margin-bottom: 8px;
            }
            .metric-value {
                font-size: 1.8rem;
                font-weight: 600;
            }
            .text-red { color: #f85149 !important; }
            .text-amber { color: #d29922 !important; }
            .text-blue { color: #58a6ff !important; }
            
            /* Findings List */
            .findings-list {
                display: flex;
                flex-direction: column;
                gap: 10px;
                margin-bottom: 30px;
            }
            .finding-row {
                background-color: #161b22;
                border: 1px solid #21262d;
                border-radius: 8px;
                padding: 14px 16px;
                display: flex;
                justify-content: space-between;
                align-items: center;
                opacity: 0;
            }
            .finding-left {
                display: flex;
                align-items: center;
                gap: 12px;
            }
            .finding-desc {
                font-size: 0.95rem;
            }
            .finding-amount {
                font-family: monospace;
                font-size: 1.05rem;
                color: #c9d1d9 !important;
            }
            
            .sev-badge {
                padding: 2px 8px;
                border-radius: 12px;
                font-size: 0.75rem;
                font-weight: 600;
                text-transform: uppercase;
            }
            .sev-high { background-color: rgba(248, 81, 73, 0.15); color: #f85149 !important; border: 1px solid rgba(248, 81, 73, 0.4); }
            .sev-medium { background-color: rgba(210, 153, 34, 0.15); color: #d29922 !important; border: 1px solid rgba(210, 153, 34, 0.4); }
            .sev-low { background-color: rgba(139, 148, 158, 0.15); color: #8b949e !important; border: 1px solid rgba(139, 148, 158, 0.4); }

            /* Expander & Markdown Overrides */
            [data-testid="stExpander"], 
            [data-testid="stExpanderDetails"],
            [data-testid="stMarkdownContainer"] {
                background-color: transparent !important;
            }
            .streamlit-expanderHeader {
                background-color: #161b22 !important;
                border: 1px solid #21262d !important;
                border-radius: 6px !important;
                color: #c9d1d9 !important;
            }
            .streamlit-expanderContent {
                border: 1px solid #21262d !important;
                border-top: none !important;
                border-bottom-left-radius: 6px !important;
                border-bottom-right-radius: 6px !important;
                background-color: #0d1117 !important;
            }
            div[data-testid="stExpanderDetails"] > div {
                background-color: #0d1117 !important;
            }
            /* Native <summary>/<details> override for expander header */
            [data-testid="stExpander"] summary {
                background-color: #161b22 !important;
                color: #c9d1d9 !important;
            }
            [data-testid="stExpander"] details {
                background-color: #161b22 !important;
                border: 1px solid #21262d !important;
            }
            [data-testid="stExpander"] summary:hover {
                background-color: #21262d !important;
            }
        </style>
    """, unsafe_allow_html=True)

# ---------------------------------------------------------------------------
# App Logic
# ---------------------------------------------------------------------------

def main():
    st.set_page_config(page_title="AuditX", layout="centered")
    inject_custom_css()

    # Layout: Header
    st.markdown('<div class="title-text animate-fade-in">AuditX</div>', unsafe_allow_html=True)
    st.markdown('<div class="subtitle-text animate-fade-in">Fraud and compliance watchdog for expense data</div>', unsafe_allow_html=True)
    
    st.markdown("""
        <div class="badge-container animate-fade-in">
            <span class="pill-badge">Google ADK</span>
            <span class="pill-badge">MCP server</span>
            <span class="pill-badge">PII masked before LLM</span>
        </div>
    """, unsafe_allow_html=True)

    if 'run_triggered' not in st.session_state:
        st.session_state.run_triggered = False
    if 'pipeline_finished' not in st.session_state:
        st.session_state.pipeline_finished = False
    if 'messages' not in st.session_state:
        st.session_state.messages = []
    if 'masked_findings' not in st.session_state:
        st.session_state.masked_findings = []
    if 'final_report' not in st.session_state:
        st.session_state.final_report = None
        
    def trigger_run():
        st.session_state.run_triggered = True
        st.session_state.pipeline_finished = False
        st.session_state.messages = []
        
    st.button("Run audit", on_click=trigger_run, disabled=st.session_state.run_triggered and not st.session_state.pipeline_finished)

    # Layout: Activity Feed
    feed_placeholder = st.empty()
    
    def render_feed():
        html = '<div>'
        for i, item in enumerate(st.session_state.messages):
            delay = 0
            
            icon_html = '<span class="feed-icon">✓</span>' if item["status"] == "done" else '<span class="thinking-dots">...</span>'
            text = item["current_text"]
            
            html += f'''
<div class="feed-item animate-fade-in" style="animation-delay: {delay}s;">
    {icon_html}
    <span>{text}</span>
</div>
'''
        html += '</div>'
        feed_placeholder.markdown(html, unsafe_allow_html=True)

    if st.session_state.run_triggered and not st.session_state.pipeline_finished:
        def on_step_callback(msg):
            clean_msg = msg.split(". ", 1)[-1] if ". " in msg and msg[0].isdigit() else msg
            
            # 1. Add thinking state
            st.session_state.messages.append({"full_text": clean_msg, "current_text": "", "status": "thinking"})
            render_feed()
            time.sleep(0.4)
            
            # 2. Typewriter loop
            for char_idx in range(len(clean_msg)):
                st.session_state.messages[-1]["current_text"] += clean_msg[char_idx]
                render_feed()
                time.sleep(0.015)
                
            # 3. Done state
            st.session_state.messages[-1]["status"] = "done"
            render_feed()
            
        with st.spinner("Executing pipeline..."):
            loop = asyncio.new_event_loop()
            asyncio.set_event_loop(loop)
            try:
                final_report, masked_findings = loop.run_until_complete(run_full_pipeline(on_step=on_step_callback))
                
                st.session_state.masked_findings = masked_findings
                st.session_state.final_report = final_report
                st.session_state.pipeline_finished = True
            except Exception as e:
                error_msg = str(e)
                if "temporarily overloaded" in error_msg:
                    st.error(error_msg)
                else:
                    st.error(f"An unexpected error occurred: {error_msg}")
                st.session_state.pipeline_finished = False
                st.session_state.run_triggered = False
            
    # Keep feed rendered if finished
    if st.session_state.messages:
        render_feed()
        
    # Layout: Metrics & Results
    if st.session_state.pipeline_finished:
        findings = st.session_state.masked_findings
        total_findings = len(findings)
        
        high_count = sum(1 for f in findings if f.get('severity') == 'high')
        medium_count = sum(1 for f in findings if f.get('severity') == 'medium')
        
        # Sum total dollar amount
        total_amount = 0.0
        for f in findings:
            for ev in f.get('evidence', []):
                amt = ev.get('amount')
                if amt is not None:
                    try:
                        total_amount += float(amt)
                    except (ValueError, TypeError):
                        pass
                        
        st.markdown(f"""
            <div class="metrics-grid">
                <div class="metric-card animate-fade-in" style="animation-delay: 0.1s;">
                    <div class="metric-label">Total Findings</div>
                    <div class="metric-value">{total_findings}</div>
                </div>
                <div class="metric-card animate-fade-in" style="animation-delay: 0.2s;">
                    <div class="metric-label">High Severity</div>
                    <div class="metric-value text-red">{high_count}</div>
                </div>
                <div class="metric-card animate-fade-in" style="animation-delay: 0.3s;">
                    <div class="metric-label">Medium Severity</div>
                    <div class="metric-value text-amber">{medium_count}</div>
                </div>
                <div class="metric-card animate-fade-in" style="animation-delay: 0.4s;">
                    <div class="metric-label">Flagged Value</div>
                    <div class="metric-value text-blue">${total_amount:,.2f}</div>
                </div>
            </div>
        """, unsafe_allow_html=True)
        
        # Layout: Findings List
        html_findings = '<div class="findings-list">'
        for i, f in enumerate(findings):
            sev = f.get('severity', 'low')
            desc = f.get('description', '')
            
            # Keep description very compact for the list view
            short_desc = desc.split('.')[0] if '.' in desc else desc
            if len(short_desc) > 80:
                short_desc = short_desc[:77] + '...'
                
            # Compute row amount
            row_amt = 0.0
            for ev in f.get('evidence', []):
                amt = ev.get('amount')
                if amt is not None:
                    try:
                        row_amt += float(amt)
                    except:
                        pass
                        
            delay = 0.5 + (i * 0.06)
            html_findings += f'''
<div class="finding-row animate-fade-in" style="animation-delay: {delay}s;">
    <div class="finding-left">
        <span class="sev-badge sev-{sev}">{sev}</span>
        <span class="finding-desc">{short_desc}</span>
    </div>
    <div class="finding-amount">${row_amt:,.2f}</div>
</div>
'''
        html_findings += '</div>'
        
        st.markdown(html_findings, unsafe_allow_html=True)
        
        # Layout: Full report expander
        if st.session_state.final_report:
            report_content = st.session_state.final_report
            # Escape dollar signs to prevent LaTeX rendering in Streamlit
            report_content = report_content.replace("$", r"\$")
                
            with st.expander("Full report", expanded=False):
                st.markdown(report_content)
        else:
            st.error("No report available in session state.")

if __name__ == "__main__":
    main()
