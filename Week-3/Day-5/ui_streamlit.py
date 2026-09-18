"""Minimal Streamlit chat UI for the AFL assistant."""

from __future__ import annotations

import sys
import uuid
from pathlib import Path

import streamlit as st
from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")
load_dotenv(ROOT.parent / "Day-4" / ".env")

from src.assistant import chat, reset_conversation  # noqa: E402

st.set_page_config(page_title="AFL Assistant", page_icon="🏉", layout="centered")
st.title("AFL Assistant")
st.caption("Stats lookup + probabilistic tips — domain-locked to AFL.")

if "conversation_id" not in st.session_state:
    st.session_state.conversation_id = str(uuid.uuid4())
if "messages" not in st.session_state:
    st.session_state.messages = []

col1, col2 = st.columns([3, 1])
with col2:
    if st.button("New chat"):
        reset_conversation(st.session_state.conversation_id)
        st.session_state.conversation_id = str(uuid.uuid4())
        st.session_state.messages = []
        st.rerun()

for m in st.session_state.messages:
    with st.chat_message(m["role"]):
        st.markdown(m["content"])
        if m.get("meta"):
            st.caption(m["meta"])

prompt = st.chat_input("Ask an AFL stats or tipping question…")
if prompt:
    st.session_state.messages.append({"role": "user", "content": prompt})
    with st.chat_message("user"):
        st.markdown(prompt)

    with st.chat_message("assistant"):
        with st.spinner("Thinking…"):
            out = chat(prompt, conversation_id=st.session_state.conversation_id)
        st.markdown(out["response"])
        meta_bits = [
            f"intent={out.get('intent')}",
            f"route={out.get('route')}",
            f"{out.get('latency_ms')} ms",
        ]
        if out.get("tool_name"):
            meta_bits.append(f"tool={out['tool_name']}")
        if out.get("prediction"):
            p = out["prediction"]
            if p.get("type") == "match_winner":
                meta_bits.append(
                    f"p_home={p.get('home_win_probability')}"
                )
        meta = " · ".join(meta_bits)
        st.caption(meta)
        st.session_state.messages.append(
            {"role": "assistant", "content": out["response"], "meta": meta}
        )
