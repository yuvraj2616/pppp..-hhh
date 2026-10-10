"""Streamlit UI. Owner: Pratham (F20). Scored only for usability: keep it minimal and clear.

Provided: ask box that sends X-Student-Id and as_of_date and renders the contract fields.
TODO (F20): ingest tab (file + metadata form -> POST /ingest), sources tab (GET /sources),
audit viewer (GET /audit/{trace_id}), colour badge per answer_type, chat history.
"""

from __future__ import annotations

import os
from datetime import date

import httpx
import streamlit as st

API_URL = os.getenv("API_URL", "http://localhost:8000")

st.set_page_config(page_title="Student Services Assistant", layout="wide")
st.title("Student Services Assistant")

with st.sidebar:
    student_id = st.text_input("Logged-in student (X-Student-Id)", value="S1001").strip() or None
    as_of = st.date_input("As of date", value=date.today())
    st.caption(f"API: {API_URL}")

question = st.text_input("Ask a question", placeholder="What is the minimum attendance for end-semester exams?")
if st.button("Ask", type="primary") and question:
    headers = {"X-Student-Id": student_id} if student_id else {}
    try:
        r = httpx.post(f"{API_URL}/ask", json={"question": question, "as_of_date": as_of.isoformat()},
                       headers=headers, timeout=120)
        r.raise_for_status()
        data = r.json()
    except httpx.HTTPError as exc:
        st.error(f"API error: {exc}")
    else:
        st.subheader(data["answer"])
        st.caption(f"answer_type: {data['answer_type']} · trace_id: {data['trace_id']} · as of {data['as_of_date']}")
        if data.get("explanation"):
            st.write(data["explanation"])
        if data.get("citations"):
            st.markdown("**Sources**")
            for c in data["citations"]:
                st.markdown(f"- {c['title']} ({c['doc_id']}) · section {c.get('section')} · page {c.get('page')} "
                            f"· v{c.get('version')} · effective {c.get('effective_from')}")
        with st.expander("Tools, rules and conflicts"):
            st.json({k: data[k] for k in ("tools_invoked", "applied_rules", "conflicts_detected")})
