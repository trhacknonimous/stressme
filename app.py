from __future__ import annotations

import asyncio
import hmac
import json
from pathlib import Path

import pandas as pd
import plotly.express as px
import streamlit as st

from config import (
    PASSWORD, ALLOWED_HOSTS, MAX_REQUESTS, MAX_CONCURRENCY,
    MIN_INTERVAL_MS, MAX_K6_VUS, MAX_K6_DURATION, MAX_K6_RATE,
    validate_target,
)
from engine.http_engine import run_http_test
from engine.k6_engine import run_k6_test
from storage import save_campaign, get_campaigns


st.set_page_config(
    page_title="TRHACKNON WEB STRESS LAB",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded",
)

css = Path("static/style.css")
if css.exists():
    st.markdown(f"<style>{css.read_text(encoding='utf-8')}</style>", unsafe_allow_html=True)

if not PASSWORD or PASSWORD == "CHANGE_ME":
    st.error("Configure un mot de passe fort dans .env avant de démarrer.")
    st.stop()

if "authenticated" not in st.session_state:
    st.session_state.authenticated = False

if not st.session_state.authenticated:
    st.markdown("# ⚡ TRHACKNON")
    st.caption("WEB STRESS LAB / AUTHENTICATION REQUIRED")
    password = st.text_input("ACCESS PASSWORD", type="password")
    if st.button("AUTHENTICATE"):
        if hmac.compare_digest(password, PASSWORD):
            st.session_state.authenticated = True
            st.rerun()
        st.error("Authentication failed.")
    st.stop()

st.sidebar.markdown("# TRHACKNON")
st.sidebar.caption("WEB STRESS LAB")
page = st.sidebar.radio("NAVIGATION", ["Dashboard", "HTTP Testing", "k6 Load Testing", "History"])
st.sidebar.divider()
st.sidebar.caption("AUTHORIZED HOSTS")
for host in sorted(ALLOWED_HOSTS):
    st.sidebar.write(f"● {host}")
if st.sidebar.button("LOGOUT"):
    st.session_state.authenticated = False
    st.rerun()

st.markdown("# ⚡ WEB STRESS LAB")
st.caption("HTTP PERFORMANCE ANALYSIS / CONTROLLED TESTING")
st.divider()

if page == "Dashboard":
    campaigns = get_campaigns()
    st.subheader("SYSTEM OVERVIEW")
    c1, c2, c3 = st.columns(3)
    c1.metric("CAMPAIGNS", len(campaigns))
    c2.metric("SUCCESSFUL REQUESTS", sum(x["success"] for x in campaigns))
    c3.metric("ERRORS", sum(x["errors"] for x in campaigns))
    st.subheader("RECENT CAMPAIGNS")
    if campaigns:
        st.dataframe(pd.DataFrame(campaigns).drop(columns=["details"]), use_container_width=True, hide_index=True)
    else:
        st.info("No campaign recorded yet.")

elif page == "HTTP Testing":
    st.subheader("HTTP REQUEST TESTER")
    with st.form("http_test"):
        url = st.text_input("TARGET URL", placeholder="https://example.com/")
        a, b, c = st.columns(3)
        count = a.number_input("REQUEST COUNT", 1, MAX_REQUESTS, 20)
        interval = b.number_input("INTERVAL (ms)", MIN_INTERVAL_MS, 60000, 1000)
        concurrency = c.number_input("CONCURRENCY", 1, MAX_CONCURRENCY, 2)
        submitted = st.form_submit_button("▶ START HTTP TEST", use_container_width=True)
    if submitted:
        try:
            target = validate_target(url)
            with st.spinner("Running bounded HTTP test..."):
                results = asyncio.run(run_http_test(target, int(count), int(interval), int(concurrency)))
            df = pd.DataFrame(results)
            successful = int(df["status"].between(200, 399).sum())
            errors = len(df) - successful
            average = float(df["latency_ms"].mean()) if len(df) else 0.0
            save_campaign("HTTP", target, successful, errors, average, results)
            st.success("HTTP campaign completed.")
            a, b, c = st.columns(3)
            a.metric("REQUESTS", len(df))
            b.metric("SUCCESS", successful)
            c.metric("ERRORS", errors)
            st.metric("AVERAGE LATENCY", f"{average:.2f} ms")
            st.plotly_chart(px.line(df, x="index", y="latency_ms", title="HTTP LATENCY", template="plotly_dark"), use_container_width=True)
            st.dataframe(df, use_container_width=True, hide_index=True)
            st.download_button("DOWNLOAD CSV", df.to_csv(index=False), "http-report.csv", "text/csv")
        except Exception as exc:
            st.error(str(exc))

elif page == "k6 Load Testing":
    st.subheader("K6 CONTROLLED LOAD TEST")
    with st.form("k6_test"):
        url = st.text_input("TARGET URL", placeholder="https://example.com/")
        a, b, c = st.columns(3)
        vus = a.number_input("VIRTUAL USERS", 1, MAX_K6_VUS, 2)
        duration = b.number_input("DURATION (SECONDS)", 1, MAX_K6_DURATION, 10)
        rate = c.number_input("REQUESTS / SECOND", 1, MAX_K6_RATE, 1)
        submitted = st.form_submit_button("▶ START K6 TEST", use_container_width=True)
    if submitted:
        try:
            target = validate_target(url)
            with st.spinner("k6 is executing the bounded scenario..."):
                result = asyncio.run(run_k6_test(target, int(vus), int(duration), int(rate)))
            metrics = result["summary"].get("metrics", {})
            req = metrics.get("http_reqs", {}).get("values", {})
            latency = metrics.get("http_req_duration", {}).get("values", {})
            failed_rate = metrics.get("http_req_failed", {}).get("values", {}).get("rate", 0)
            total = int(req.get("count", 0))
            errors = round(total * failed_rate)
            success = total - errors
            average = float(latency.get("avg", 0))
            save_campaign("K6", target, success, errors, average, result["summary"])
            a, b, c, d = st.columns(4)
            a.metric("REQUESTS", total)
            b.metric("SUCCESS", success)
            c.metric("ERRORS", errors)
            d.metric("AVG LATENCY", f"{average:.2f} ms")
            st.metric("P95 LATENCY", f'{latency.get("p(95)", 0):.2f} ms')
            st.download_button("DOWNLOAD JSON REPORT", json.dumps(result["summary"], indent=2), "k6-report.json", "application/json")
            with st.expander("K6 OUTPUT"):
                st.code(result["output"])
        except Exception as exc:
            st.error(str(exc))

elif page == "History":
    st.subheader("CAMPAIGN HISTORY")
    campaigns = get_campaigns()
    if campaigns:
        df = pd.DataFrame(campaigns)
        st.dataframe(df.drop(columns=["details"]), use_container_width=True, hide_index=True)
        selected_id = st.selectbox("SELECT CAMPAIGN", df["id"].tolist())
        selected = next(item for item in campaigns if item["id"] == selected_id)
        details = json.loads(selected["details"])
        st.json(details)
        st.download_button("EXPORT CAMPAIGN JSON", json.dumps(details, indent=2), f"campaign-{selected_id}.json", "application/json")
    else:
        st.info("No history available.")
