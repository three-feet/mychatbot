import os
import json
import time
import requests
import tempfile
import numpy as np
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import yfinance as yf
import seaborn as sns

from openai import AzureOpenAI

# ==================================================
# PAGE
# ==================================================

st.set_page_config(
    page_title="💜 세무요정 지민",
    page_icon="💜",
    layout="wide"
)

st.markdown("""
<style>
.weather-mini {
    background: linear-gradient(135deg, #a855f7, #ec4899);
    padding: 12px;
    border-radius: 12px;
    color: white;
    font-size: 13px;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# AZURE
# ==================================================

client = AzureOpenAI(
    azure_endpoint=st.secrets["AZURE_OPENAI_ENDPOINT"],
    api_key=st.secrets["AZURE_OPENAI_API_KEY"],
    api_version="2024-05-01-preview"
)

assistant_id = st.secrets["ASSISTANT_ID"]

# ==================================================
# SESSION (chat thread)
# ==================================================

if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

if "messages" not in st.session_state:
    st.session_state.messages = []

# ==================================================
# WEATHER (SEOUL FIXED)
# ==================================================

def get_weather():
    try:
        w = requests.get("https://wttr.in/Seoul?format=j1", timeout=3).json()
        cur = w["current_condition"][0]

        return {
            "city": "Seoul",
            "temp": cur["temp_C"],
            "desc": cur["weatherDesc"][0]["value"]
        }
    except:
        return {"city": "Seoul", "temp": "-", "desc": "N/A"}

# ==================================================
# STOCK (7 DAYS)
# ==================================================

def show_stock_chart():

    sns.set_theme(style="whitegrid")

    # =========================
    # 데이터 안정화 함수
    # =========================
    def get_df(ticker):
        df = yf.download(ticker, period="7d")[["Close"]].dropna().reset_index()
        df.columns = ["Date", "Close"]
        return df

    hynix = get_df("000660.KS")
    samsung = get_df("005930.KS")

    # =========================
    # SK Hynix
    # =========================
    fig1, ax1 = plt.subplots(figsize=(6, 3))

    sns.lineplot(
        data=hynix,
        x="Date",
        y="Close",
        ax=ax1,
        color="red",
        linewidth=2.5
    )

    ax1.set_title("SK Hynix (7 Days)")
    ax1.set_ylabel("Price")
    ax1.ticklabel_format(style='plain', axis='y')
    ax1.grid(True, alpha=0.3)
    fig1.autofmt_xdate()

    st.pyplot(fig1)

    # =========================
    # Samsung
    # =========================
    fig2, ax2 = plt.subplots(figsize=(6, 3))

    sns.lineplot(
        data=samsung,
        x="Date",
        y="Close",
        ax=ax2,
        color="blue",
        linewidth=2.5
    )

    ax2.set_title("Samsung Electronics (7 Days)")
    ax2.set_ylabel("Price")
    ax2.ticklabel_format(style='plain', axis='y')
    ax2.grid(True, alpha=0.3)
    fig2.autofmt_xdate()

    st.pyplot(fig2)
    
# ==================================================
# FILE ANALYSIS (SEPARATE THREAD)
# ==================================================

def analyze_file(file_path):

    with open(file_path, "rb") as f:
        up = client.files.create(
            file=f,
            purpose="assistants"
        )

    thread = client.beta.threads.create()

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="이 파일을 세무 관점에서 분석해서 요약해줘.",
        attachments=[{"file_id": up.id}]
    )

    run = client.beta.threads.runs.create(
        thread_id=thread.id,
        assistant_id=assistant_id
    )

    while True:

        run = client.beta.threads.runs.retrieve(
            thread_id=thread.id,
            run_id=run.id
        )

        if run.status == "completed":

            msgs = client.beta.threads.messages.list(
                thread_id=thread.id
            )

            return msgs.data[0].content[0].text.value

        elif run.status in ["failed", "cancelled", "expired"]:
            return "❌ 분석 실패"

        time.sleep(1)

# ==================================================
# SIDEBAR (weather + stock only)
# ==================================================

with st.sidebar:

    st.title("💜 세무요정 지민")

    w = get_weather()

    st.markdown(f"""
<div class="weather-mini">
🌤 Seoul<br>
🌡 {w['temp']}°C<br>
{w['desc']}
</div>
""", unsafe_allow_html=True)

    st.divider()

    st.subheader("")

    show_stock_chart()

# ==================================================
# MAIN TOP UI (moved controls)
# ==================================================

st.title("💜 세무요정 지민")

colA, colB = st.columns([1, 3])

with colA:
    if st.button("🧹 초기화"):
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
        st.session_state.messages = []
        st.rerun()

with colB:
    uploaded_files = st.file_uploader(
        "📄 파일 업로드 (즉시 분석)",
        type=["pdf","txt","csv","xlsx","png","jpg","jpeg"],
        accept_multiple_files=True
    )

# ==================================================
# CHAT UI
# ==================================================

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("세금 / 주식 / 파일 분석 💜")

# ==================================================
# CHAT PROCESS
# ==================================================

if prompt:

    st.session_state.messages.append({"role": "user", "content": prompt})

    st.chat_message("user").markdown(prompt)

    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt
    )

    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=assistant_id
    )

    with st.chat_message("assistant"):

        box = st.empty()

        while True:

            run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )

            if run.status == "completed":

                msgs = client.beta.threads.messages.list(
                    thread_id=st.session_state.thread_id
                )

                text = msgs.data[0].content[0].text.value

                box.markdown(text)

                st.session_state.messages.append(
                    {"role": "assistant", "content": text}
                )

                break

            elif run.status in ["failed", "cancelled", "expired"]:
                box.error("오류 발생")
                break

            time.sleep(1)

# ==================================================
# FILE UPLOAD PROCESS (SEPARATE FROM VECTOR STORE)
# ==================================================

if uploaded_files:

    st.subheader("📊 파일 분석 결과")

    for file in uploaded_files:

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file.read())
            path = tmp.name

        st.info("분석 중... 💜")

        result = analyze_file(path)

        st.success("완료")
        st.markdown(result)
