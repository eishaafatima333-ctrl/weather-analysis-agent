import os
import time
import glob
import streamlit as st
from agent import ask

st.set_page_config(page_title="Weather & Storm Agent", page_icon="⛈️")
st.title("⛈️ Weather Analysis & Storm Prediction Agent")
st.write("Ask for live weather anywhere in the world, or a storm and rain outlook.")

question = st.text_input("Your question", "Will it rain or storm in London in the next 12 hours?")

if st.button("Analyze"):
    start = time.time()
    with st.spinner("Fetching live data and analyzing..."):
        answer = ask(question)
    st.session_state["answer"] = answer
    # find PDFs created during this run
    new_pdfs = [f for f in glob.glob("reports/*.pdf") if os.path.getmtime(f) >= start]
    st.session_state["pdf"] = max(new_pdfs, key=os.path.getmtime) if new_pdfs else None

if "answer" in st.session_state:
    st.markdown(st.session_state["answer"])
    pdf = st.session_state.get("pdf")
    if pdf:
        with open(pdf, "rb") as f:
            st.download_button("📄 Download PDF report", f, file_name=os.path.basename(pdf),
                               mime="application/pdf")

st.divider()
st.subheader("Previous reports")
for f in sorted(glob.glob("reports/*.pdf"), reverse=True):
    with open(f, "rb") as fh:
        st.download_button(os.path.basename(f), fh, file_name=os.path.basename(f),
                           mime="application/pdf", key=f)