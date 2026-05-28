# app.py
# Python 3.14 기준으로 작성하였으나 배포는 3.11기준으로 할 예정
# 실행 방법:
# pip install streamlit openai pillow pandas matplotlib requests
# streamlit run app.py

import os
import json
import time
import tempfile
import requests
import streamlit as st

from openai import AzureOpenAI
from PIL import Image

# =========================================================
# Azure OpenAI 설정
# =========================================================

AZURE_ENDPOINT = st.secrets["endpoint"]
AZURE_API_KEY = st.secrets["apikey"]
AZURE_API_VERSION = "2024-05-01-preview"

MODEL_NAME = "gpt-4o-mini-10ai011"

VECTOR_STORE_ID = "vs_TiYcLEiJgc8m4XdAJJcvRWhO"

# =========================================================
# Streamlit 페이지 설정
# =========================================================

st.set_page_config(
    page_title="세무 전문 AI",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 세무 전문 AI")
st.caption("질문 / 그래프 생성 / 파일 요약 / 데이터 분석 / 실시간 날씨 / 오류 없는 곱셉")

# =========================================================
# OpenAI Client
# =========================================================

client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION
)

# =========================================================
# 함수 정의
# =========================================================

def multiply(a, b):

    print(f"multiply called with a={a}, b={b}")

    result = a * b

    return json.dumps({
        "a": a,
        "b": b,
        "result": result
    })


def get_weather(location, unit="c"):

    print(f"get_weather called with location={location}")

    try:

        url = f"https://wttr.in/{location}?format=j1"

        response = requests.get(url)

        data = response.json()

        current = data["current_condition"][0]

        if unit == "f":
            temperature = current["temp_F"]
            temp_unit = "°F"
        else:
            temperature = current["temp_C"]
            temp_unit = "°C"

        weather_desc = current["weatherDesc"][0]["value"]
        humidity = current["humidity"]
        feels_like = current["FeelsLikeC"]

        result = {
            "location": location,
            "temperature": f"{temperature}{temp_unit}",
            "weather": weather_desc,
            "humidity": humidity,
            "feels_like_c": feels_like
        }

        return json.dumps(result)

    except Exception as e:

        return json.dumps({
            "error": str(e)
        })

# =========================================================
# 세션 상태 초기화
# =========================================================

if "assistant_id" not in st.session_state:

    assistant = client.beta.assistants.create(
        model=MODEL_NAME,
        name="Streamlit Assistant",
        instructions="""
        너는 데이터 분석과 문서 요약을 잘하는 AI Assistant이다.

        사용자가:
        - 일반 질문을 하면 답변
        - 그래프를 요청하면 code interpreter로 그래프 생성
        - 파일을 업로드하면 내용 분석 및 요약
        - CSV/엑셀 파일이면 데이터 분석 가능
        - 날씨를 물어보면 get_weather 함수를 사용
        - 계산 요청 시 multiply 함수를 사용

        답변은 한국어로 해줘.

        한국 도시 이름은 영어로 변환해서 weather tool 호출:
        - 서울 → Seoul
        - 부산 → Busan
        - 대구 → Daegu
        - 인천 → Incheon
        """,
        tools=[
            {"type": "code_interpreter"},
            {"type": "file_search"},

            # =====================================================
            # 날씨 함수
            # =====================================================
            {
                "type": "function",
                "function": {
                    "name": "get_weather",
                    "description": "Get realtime weather information",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "location": {
                                "type": "string",
                                "description": "City name"
                            },
                            "unit": {
                                "type": "string",
                                "enum": ["c", "f"]
                            }
                        },
                        "required": ["location"]
                    }
                }
            },

            # =====================================================
            # 곱셈 함수
            # =====================================================
            {
                "type": "function",
                "function": {
                    "name": "multiply",
                    "description": "Multiply two numbers",
                    "parameters": {
                        "type": "object",
                        "properties": {
                            "a": {
                                "type": "number"
                            },
                            "b": {
                                "type": "number"
                            }
                        },
                        "required": ["a", "b"]
                    }
                }
            }
        ],
        tool_resources={
            "file_search": {
                "vector_store_ids": [VECTOR_STORE_ID]
            }
        },
        temperature=1,
        top_p=1
    )

    st.session_state.assistant_id = assistant.id

# =========================================================
# Thread 생성
# =========================================================

if "thread_id" not in st.session_state:

    thread = client.beta.threads.create()

    st.session_state.thread_id = thread.id

# =========================================================
# 메시지 저장
# =========================================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# =========================================================
# 이전 대화 출력
# =========================================================

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        if msg["type"] == "text":

            st.markdown(msg["content"])

        elif msg["type"] == "image":

            st.image(msg["content"])

# =========================================================
# 파일 업로드
# =========================================================

uploaded_file = st.sidebar.file_uploader(
    "파일 업로드",
    type=[
        "pdf",
        "txt",
        "csv",
        "xlsx",
        "png",
        "jpg",
        "jpeg"
    ]
)

# =========================================================
# 사용자 입력
# =========================================================

prompt = st.chat_input("메시지를 입력하세요")

if prompt:

    # =====================================================
    # 사용자 메시지 출력
    # =====================================================

    with st.chat_message("user"):
        st.markdown(prompt)

    st.session_state.messages.append({
        "role": "user",
        "type": "text",
        "content": prompt
    })

    # =====================================================
    # 파일 업로드 처리
    # =====================================================

    uploaded_file_ids = []

    if uploaded_file is not None:

        with tempfile.NamedTemporaryFile(delete=False) as tmp_file:

            tmp_file.write(uploaded_file.read())

            temp_path = tmp_file.name

        with open(temp_path, "rb") as f:

            uploaded = client.files.create(
                file=f,
                purpose="assistants"
            )

            uploaded_file_ids.append(uploaded.id)

        st.sidebar.success(f"업로드 완료: {uploaded_file.name}")

    # =====================================================
    # Thread 메시지 추가
    # =====================================================

    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt,
        attachments=[
            {
                "file_id": fid,
                "tools": [
                    {"type": "code_interpreter"},
                    {"type": "file_search"}
                ]
            }
            for fid in uploaded_file_ids
        ] if uploaded_file_ids else None
    )

    # =====================================================
    # Run 생성
    # =====================================================

    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=st.session_state.assistant_id
    )

    # =====================================================
    # 실행 처리
    # =====================================================

    with st.spinner("AI가 작업 중입니다..."):

        while True:

            run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )

            # =============================================
            # 일반 실행 중
            # =============================================

            if run.status in ["queued", "in_progress"]:

                time.sleep(1)

                continue

            # =============================================
            # 함수 호출 필요
            # =============================================

            elif run.status == "requires_action":

                tool_calls = (
                    run.required_action
                    .submit_tool_outputs
                    .tool_calls
                )

                tool_outputs = []

                for tool_call in tool_calls:

                    function_name = tool_call.function.name

                    arguments = json.loads(
                        tool_call.function.arguments
                    )

                    print("Function:", function_name)
                    print("Arguments:", arguments)

                    # =====================================
                    # multiply
                    # =====================================

                    if function_name == "multiply":

                        result = multiply(
                            a=arguments["a"],
                            b=arguments["b"]
                        )

                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": result
                        })

                    # =====================================
                    # get_weather
                    # =====================================

                    elif function_name == "get_weather":

                        result = get_weather(
                            location=arguments["location"],
                            unit=arguments.get("unit", "c")
                        )

                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": result
                        })

                # =========================================
                # Tool 결과 제출
                # =========================================

                run = client.beta.threads.runs.submit_tool_outputs(
                    thread_id=st.session_state.thread_id,
                    run_id=run.id,
                    tool_outputs=tool_outputs
                )

                time.sleep(1)

                continue

            # =============================================
            # 완료
            # =============================================

            elif run.status == "completed":

                break

            # =============================================
            # 실패
            # =============================================

            else:

                st.error(f"실행 실패: {run.status}")

                break

    # =====================================================
    # 결과 출력
    # =====================================================

    if run.status == "completed":

        messages = client.beta.threads.messages.list(
            thread_id=st.session_state.thread_id
        )

        latest_message = messages.data[0]

        with st.chat_message("assistant"):

            for content in latest_message.content:

                # =========================================
                # 텍스트 응답
                # =========================================

                if content.type == "text":

                    answer = content.text.value

                    st.markdown(answer)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "text",
                        "content": answer
                    })

                # =========================================
                # 이미지 출력
                # =========================================

                elif content.type == "image_file":

                    file_id = content.image_file.file_id

                    image_data = client.files.content(file_id)

                    image_bytes = image_data.read()

                    temp_image_path = tempfile.NamedTemporaryFile(
                        delete=False,
                        suffix=".png"
                    ).name

                    with open(temp_image_path, "wb") as f:

                        f.write(image_bytes)

                    st.image(temp_image_path)

                    st.session_state.messages.append({
                        "role": "assistant",
                        "type": "image",
                        "content": temp_image_path
                    })

                # =========================================
                # 파일 다운로드 처리
                # =========================================

                elif content.type == "file_path":

                    file_id = content.file_path.file_id

                    file_data = client.files.content(file_id)

                    file_name = f"output_{file_id}"

                    with open(file_name, "wb") as f:

                        f.write(file_data.read())

                    st.download_button(
                        label=f"📥 {file_name} 다운로드",
                        data=open(file_name, "rb"),
                        file_name=file_name
                    )
