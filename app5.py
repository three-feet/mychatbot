```python id="app_final"
import os
import json
import time
import requests
import tempfile
import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt
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
deployment = st.secrets["AZURE_OPENAI_DEPLOYMENT"]
assistant_id = st.secrets["ASSISTANT_ID"]

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=apikey,
    api_version="2024-05-01-preview"
)

# ==================================================
# Thread
# ==================================================

if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

if "messages" not in st.session_state:
    st.session_state.messages = []

# ==================================================
# 날씨 (사이드바용)
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
# 주가 (자동 표시)
# ==================================================

def show_stock_chart():

    samsung = yf.download("005930.KS", period="3mo")["Close"]
    hynix = yf.download("000660.KS", period="3mo")["Close"]

    df = pd.concat(
        [samsung, hynix],
        axis=1,
        join="inner"
    )

    df.columns = ["Samsung", "SK Hynix"]

    fig, ax = plt.subplots(figsize=(7, 4))
    df.plot(ax=ax)

    ax.set_title("📈 삼성전자 vs SK하이닉스 (3개월)")
    ax.set_ylabel("Price")

    st.pyplot(fig)
    st.dataframe(df.tail())

# ==================================================
# SIDEBAR (날씨 작게)
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
        "📄 파일 업로드",
        type=["pdf","txt","csv","xlsx","png","jpg","jpeg"],
        accept_multiple_files=True
    )

    if st.button("🧹 초기화"):
        thread = client.beta.threads.create()
        st.session_state.thread_id = thread.id
        st.session_state.messages = []
        st.rerun()

# ==================================================
# MAIN LAYOUT (좌:채팅 / 우:주가)
# ==================================================

col1, col2 = st.columns([2, 1])

# ===========================
# LEFT: CHAT
# ===========================

with col1:

    st.title("💜 세무요정 지민")
    st.caption("세법 + 금융 + 팬챗 AI")

    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    prompt = st.chat_input("세금 / 주식 / 궁금한 거 물어봐 💜")

# ===========================
# RIGHT: STOCK (AUTO)
# ===========================

with col2:

    st.subheader("📈 실시간 주가")

    show_stock_chart()

# ==================================================
# FILE UPLOAD 처리
# ==================================================

uploaded_file_ids = []

if uploaded_files:

    for file in uploaded_files:

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(file.read())
            path = tmp.name

        up = client.files.create(
            file=open(path, "rb"),
            purpose="assistants"
        )

        uploaded_file_ids.append(up.id)

# ==================================================
# CHAT 처리
# ==================================================

if prompt:

    st.session_state.messages.append(
        {"role": "user", "content": prompt}
    )

    with col1:
        with st.chat_message("user"):
            st.markdown(prompt)

    attachments = [
        {
            "file_id": fid,
            "tools": [
                {"type": "file_search"},
                {"type": "code_interpreter"}
            ]
        }
        for fid in uploaded_file_ids
    ]

    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt,
        attachments=attachments if attachments else None
    )

    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=assistant_id
    )

    with col1:
        with st.chat_message("assistant"):

            box = st.empty()
            text = ""

            while True:

                run = client.beta.threads.runs.retrieve(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id
                )

                if run.status == "requires_action":

                    outputs = []

                    for call in run.required_action.submit_tool_outputs.tool_calls:

                        name = call.function.name
                        args = json.loads(call.function.arguments)

                        outputs.append({
                            "tool_call_id": call.id,
                            "output": json.dumps({"ok": True})
                        })

                    client.beta.threads.runs.submit_tool_outputs(
                        thread_id=st.session_state.thread_id,
                        run_id=run.id,
                        tool_outputs=outputs
                    )

                elif run.status == "completed":

                    msgs = client.beta.threads.messages.list(
                        thread_id=st.session_state.thread_id
                    )

                    latest = msgs.data[0]

                    for item in latest.content:
                        if item.type == "text":
                            text += item.text.value

                    box.markdown(text)

                    st.session_state.messages.append(
                        {"role": "assistant", "content": text}
                    )

                    break

                elif run.status in ["failed","cancelled","expired"]:
                    st.error("오류 발생")
                    break

                else:
                    time.sleep(1)
```
