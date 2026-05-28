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

.main {
    background-color: #faf7ff;
}

.stChatMessage {
    border-radius: 15px;
    padding: 10px;
}

.weather-card {
    background: linear-gradient(135deg, #a855f7, #ec4899);
    padding: 25px;
    border-radius: 20px;
    color: white;
    margin-bottom: 20px;
    box-shadow: 0px 4px 15px rgba(0,0,0,0.15);
}

.weather-city {
    font-size: 24px;
    font-weight: bold;
}

.weather-temp {
    font-size: 42px;
    font-weight: bold;
}

.weather-desc {
    font-size: 18px;
}

.metric-box {
    background-color: white;
    padding: 15px;
    border-radius: 15px;
    text-align: center;
    box-shadow: 0px 2px 10px rgba(0,0,0,0.08);
}

.stButton button {
    border-radius: 10px;
}

.block-container {
    padding-top: 2rem;
}

</style>
""", unsafe_allow_html=True)

# ==================================================
# Streamlit Secrets
# ==================================================

endpoint = st.secrets["AZURE_OPENAI_ENDPOINT"]
apikey = st.secrets["AZURE_OPENAI_API_KEY"]
deployment = st.secrets["AZURE_OPENAI_DEPLOYMENT"]
assistant_id = st.secrets["ASSISTANT_ID"]

# ==================================================
# Azure OpenAI Client
# ==================================================

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=apikey,
    api_version="2024-05-01-preview"
)

# ==================================================
# Thread 생성
# ==================================================

if "thread_id" not in st.session_state:

    thread = client.beta.threads.create()

    st.session_state.thread_id = thread.id

# ==================================================
# 메시지 저장
# ==================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# ==================================================
# 현재 날씨 조회
# ==================================================

def get_current_weather():

    try:

        location_res = requests.get(
            "https://ipapi.co/json/",
            timeout=5
        )

        location_data = location_res.json()

        city = location_data.get("city", "Seoul")

        weather_url = f"https://wttr.in/{city}?format=j1"

        weather_res = requests.get(
            weather_url,
            timeout=5
        )

        weather_data = weather_res.json()

        current = weather_data["current_condition"][0]

        return {
            "city": city,
            "temp": current["temp_C"],
            "weather": current["weatherDesc"][0]["value"],
            "humidity": current["humidity"],
            "wind": current["windspeedKmph"]
        }

    except Exception:

        return {
            "city": "Seoul",
            "temp": "-",
            "weather": "조회 실패",
            "humidity": "-",
            "wind": "-"
        }

# ==================================================
# 함수 정의
# ==================================================

def mul_numbers(a, b):

    return {
        "result": a * b
    }

def get_weather(location):

    try:

        url = f"https://wttr.in/{location}?format=j1"

        response = requests.get(url, timeout=5)

        if response.status_code == 200:

            data = response.json()

            current = data["current_condition"][0]

            return {
                "location": location,
                "temperature": current["temp_C"] + "°C",
                "weather": current["weatherDesc"][0]["value"],
                "humidity": current["humidity"] + "%"
            }

    except Exception as e:

        return {
            "error": str(e)
        }

# ==================================================
# 삼성전자 / 하이닉스 주가 차트
# ==================================================

def show_stock_chart():

    try:
        samsung = yf.download("005930.KS", period="3mo")[["Close"]]
        hynix = yf.download("000660.KS", period="3mo")[["Close"]]

        samsung.columns = ["Samsung Electronics"]
        hynix.columns = ["SK Hynix"]

        # 핵심: index 기준 병합
        chart_df = samsung.join(hynix, how="inner")

        fig, ax = plt.subplots(figsize=(10, 5))
        chart_df.plot(ax=ax)

        ax.set_title("최근 삼성전자 / SK하이닉스 주가")
        ax.set_xlabel("Date")
        ax.set_ylabel("Close Price")

        st.pyplot(fig)
        st.dataframe(chart_df.tail())

    except Exception as e:
        st.error(f"주가 데이터 오류: {e}")

# ==================================================
# 사이드바
# ==================================================

with st.sidebar:

    st.title("💜 세무요정 지민")

    st.markdown("""
### BTS 지민 컨셉 세법 상담 AI

- 종합소득세
- 부가가치세
- 연말정산
- 프리랜서 세금
- 사업자등록
- 절세 전략
- 금융 정보
    """)

    st.divider()

    uploaded_files = st.file_uploader(
        "📄 파일 업로드",
        type=[
            "pdf",
            "txt",
            "csv",
            "xlsx",
            "png",
            "jpg",
            "jpeg"
        ],
        accept_multiple_files=True
    )

    st.divider()

    if st.button("📈 삼성전자 / 하이닉스 주가 보기"):

        st.subheader("📈 반도체 주가 차트")

        show_stock_chart()

    st.divider()

    if st.button("🧹 대화 초기화"):

        thread = client.beta.threads.create()

        st.session_state.thread_id = thread.id
        st.session_state.messages = []

        st.rerun()

# ==================================================
# 메인 헤더
# ==================================================

st.title("💜 세무요정 지민")
st.caption("BTS 지민이 알려주는 세법 + 금융 상담 챗봇")

# ==================================================
# 그래픽 날씨 카드
# ==================================================

weather_info = get_current_weather()

st.markdown(f"""
<div class="weather-card">

<div class="weather-city">
📍 {weather_info['city']}
</div>

<br>

<div class="weather-temp">
🌡 {weather_info['temp']}°C
</div>

<div class="weather-desc">
☁️ {weather_info['weather']}
</div>

<br>

💧 습도: {weather_info['humidity']}%  
💨 풍속: {weather_info['wind']} km/h

</div>
""", unsafe_allow_html=True)

# ==================================================
# 날씨 상세 메트릭
# ==================================================

col1, col2, col3 = st.columns(3)

with col1:

    st.markdown(f"""
    <div class="metric-box">
    <h4>🌡 기온</h4>
    <h2>{weather_info['temp']}°C</h2>
    </div>
    """, unsafe_allow_html=True)

with col2:

    st.markdown(f"""
    <div class="metric-box">
    <h4>💧 습도</h4>
    <h2>{weather_info['humidity']}%</h2>
    </div>
    """, unsafe_allow_html=True)

with col3:

    st.markdown(f"""
    <div class="metric-box">
    <h4>💨 풍속</h4>
    <h2>{weather_info['wind']} km/h</h2>
    </div>
    """, unsafe_allow_html=True)

st.divider()

# ==================================================
# 이전 대화 출력
# ==================================================

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        st.markdown(msg["content"])

# ==================================================
# 채팅 입력
# ==================================================

prompt = st.chat_input(
    "세금이나 금융 관련 궁금한 걸 물어봐 💜"
)

# ==================================================
# 파일 업로드 처리
# ==================================================

uploaded_file_ids = []

if uploaded_files:

    with st.spinner("파일 업로드 중..."):

        for file in uploaded_files:

            with tempfile.NamedTemporaryFile(delete=False) as tmp:

                tmp.write(file.read())

                tmp_path = tmp.name

            uploaded = client.files.create(
                file=open(tmp_path, "rb"),
                purpose="assistants"
            )

            uploaded_file_ids.append(uploaded.id)

# ==================================================
# 질문 처리
# ==================================================

if prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):

        st.markdown(prompt)

    attachments = []

    for fid in uploaded_file_ids:

        attachments.append({
            "file_id": fid,
            "tools": [
                {"type": "file_search"},
                {"type": "code_interpreter"}
            ]
        })

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

    with st.chat_message("assistant"):

        response_placeholder = st.empty()

        full_response = ""

        while True:

            run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )

            # ======================================
            # 함수 호출 처리
            # ======================================

            if run.status == "requires_action":

                tool_outputs = []

                tool_calls = run.required_action.submit_tool_outputs.tool_calls

                for tool_call in tool_calls:

                    function_name = tool_call.function.name

                    arguments = json.loads(
                        tool_call.function.arguments
                    )

                    if function_name == "mul_numbers":

                        result = mul_numbers(
                            arguments["a"],
                            arguments["b"]
                        )

                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(result)
                        })

                    elif function_name == "get_weather":

                        result = get_weather(
                            arguments["location"]
                        )

                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(
                                result,
                                ensure_ascii=False
                            )
                        })

                client.beta.threads.runs.submit_tool_outputs(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )

            # ======================================
            # 완료 처리
            # ======================================

            elif run.status == "completed":

                messages = client.beta.threads.messages.list(
                    thread_id=st.session_state.thread_id
                )

                latest_message = messages.data[0]

                content_items = latest_message.content

                for item in content_items:

                    if item.type == "text":

                        full_response += item.text.value + "\n"

                    elif item.type == "image_file":

                        image_file_id = item.image_file.file_id

                        image_data = client.files.content(
                            image_file_id
                        )

                        st.image(
                            image_data.read(),
                            caption="생성된 이미지"
                        )

                response_placeholder.markdown(full_response)

                st.session_state.messages.append({
                    "role": "assistant",
                    "content": full_response
                })

                break

            # ======================================
            # 오류 처리
            # ======================================

            elif run.status in [
                "failed",
                "cancelled",
                "expired",
                "incomplete"
            ]:

                st.error(f"오류 발생: {run.status}")

                if run.last_error:
                    st.error(run.last_error.message)

                break

            else:

                time.sleep(1)
