import os
import json
import time
import requests
import tempfile
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
import matplotlib.dates as mdates
import yfinance as yf

from openai import AzureOpenAI

# ==================================================
# 페이지 설정
# ==================================================

st.set_page_config(
    page_title="💜 세무요정 지민",
    page_icon="💜",
    layout="wide"
)

# ==================================================
# 스타일
# ==================================================

st.markdown("""
<style>
.weather-mini {
    background: linear-gradient(135deg, #a855f7, #ec4899);
    padding: 12px;
    border-radius: 12px;
    color: white;
    font-size: 13px;
    margin-bottom: 10px;
}
</style>
""", unsafe_allow_html=True)

# ==================================================
# Secrets
# ==================================================

endpoint = st.secrets["AZURE_OPENAI_ENDPOINT"]
apikey = st.secrets["AZURE_OPENAI_API_KEY"]
assistant_id = st.secrets["ASSISTANT_ID"]

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=apikey,
    api_version="2024-05-01-preview"
)

# ==================================================
# Thread (chat용)
# ==================================================

if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

if "messages" not in st.session_state:
    st.session_state.messages = []

# ==================================================
# 날씨
# ==================================================

def get_weather_mini():
    try:
        loc = requests.get("https://ipapi.co/json/", timeout=3).json()
        city = loc.get("city", "Seoul")

        w = requests.get(f"https://wttr.in/{city}?format=j1", timeout=3).json()
        cur = w["current_condition"][0]

        return {
            "city": city,
            "temp": cur["temp_C"],
            "desc": cur["weatherDesc"][0]["value"]
        }
    except:
        return {"city": "Seoul", "temp": "-", "desc": "N/A"}

# ==================================================
# 주가 (1주일)
# ==================================================

def show_stock_chart():

    hynix = yf.download("000660.KS", period="7d")["Close"]
    samsung = yf.download("005930.KS", period="7d")["Close"]

    c1, c2 = st.columns(2)

    # =========================
    # SK하이닉스
    # =========================
    with c1:

        st.markdown("##### 📈 SK하이닉스")

        fig1, ax1 = plt.subplots(figsize=(5, 1.8))

        ax1.plot(
            hynix.index,
            hynix.values,
            color="red",
            linewidth=2
        )

        # 날짜 포맷
        ax1.xaxis.set_major_formatter(
            mdates.DateFormatter('%m/%d')
        )

        # 날짜 간격
        ax1.xaxis.set_major_locator(
            mdates.DayLocator(interval=2)
        )

        # 글자 크기
        ax1.tick_params(axis='x', labelsize=7)

        ax1.ticklabel_format(
            style='plain',
            axis='y'
        )

        plt.tight_layout()

        st.pyplot(fig1)

        hynix_latest = hynix.dropna().iloc[-1].item()

        st.caption(
            f"현재가: {hynix_latest:,.0f}원"
        )

    # =========================
    # 삼성전자
    # =========================
    with c2:

        st.markdown("##### 📈 삼성전자")

        fig2, ax2 = plt.subplots(figsize=(5, 1.8))

        ax2.plot(
            samsung.index,
            samsung.values,
            color="blue",
            linewidth=2
        )

        # 날짜 포맷
        ax2.xaxis.set_major_formatter(
            mdates.DateFormatter('%m/%d')
        )

        # 날짜 간격
        ax2.xaxis.set_major_locator(
            mdates.DayLocator(interval=2)
        )

        # 글자 크기
        ax2.tick_params(axis='x', labelsize=7)

        ax2.ticklabel_format(
            style='plain',
            axis='y'
        )

        plt.tight_layout()

        st.pyplot(fig2)

        samsung_latest = samsung.dropna().iloc[-1].item()

        st.caption(
            f"현재가: {samsung_latest:,.0f}원"
        )

# ==================================================
# 파일 분석 (ONE SHOT)
# ==================================================

def analyze_file(file_id):

    thread = client.beta.threads.create()

    client.beta.threads.messages.create(
        thread_id=thread.id,
        role="user",
        content="이 파일을 세무 관점에서 분석하고 핵심 내용을 요약해줘."
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
# SIDEBAR
# ==================================================

with st.sidebar:

    st.title("💜 세무요정 지민")

    w = get_weather_mini()

    st.markdown(f"""
<div class="weather-mini">
🌤 {w['city']}<br>
🌡 {w['temp']}°C<br>
{w['desc']}
</div>
""", unsafe_allow_html=True)

    st.divider()

    uploaded_files = st.file_uploader(
        "📄 파일 업로드 (자동 분석)",
        type=["pdf","txt","csv","xlsx","png","jpg","jpeg"],
        accept_multiple_files=True
    )

    if st.button("🧹 초기화"):
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
        st.session_state.messages = []
        st.rerun()

# ==================================================
# MAIN
# ==================================================

st.title("💜 세무요정 지민")
st.caption("세법 + 금융 + AI 분석")

# =========================
# 주가 최상단
# =========================

show_stock_chart()

st.divider()

# =========================
# 채팅
# =========================

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

prompt = st.chat_input("세금 / 주식 / 파일 분석 💜")

# ==================================================
# CHAT 처리
# ==================================================

if prompt:

    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

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
        text = ""

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
# FILE UPLOAD → 즉시 분석
# ==================================================

if uploaded_files:

    st.subheader("📊 파일 분석 결과")

    for file in uploaded_files:

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file.read())
            path = tmp.name

        with open(path, "rb") as f:
            up = client.files.create(
                file=f,
                purpose="assistants"
            )

        st.info("분석 중... 💜")

        result = analyze_file(up.id)

        st.success("완료!")
        st.markdown(result)
