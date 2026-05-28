# app.py
# Python 3.14 기준
# 실행 방법:
# pip install streamlit openai pillow pandas matplotlib
# streamlit run app.py

import os
import time
import tempfile
import streamlit as st
from openai import AzureOpenAI
from PIL import Image

# =========================================================
# Azure OpenAI 설정
# =========================================================

AZURE_ENDPOINT = os.getenv("AZURE_OPENAI_ENDPOINT", "YOUR_ENDPOINT")
AZURE_API_KEY = os.getenv("AZURE_OPENAI_API_KEY", "YOUR_API_KEY")
AZURE_API_VERSION = "2024-05-01-preview"

MODEL_NAME = "gpt-4o-mini-10ai011"

VECTOR_STORE_ID = "vs_TiYcLEiJgc8m4XdAJJcvRWhO"

# =========================================================
# Streamlit 페이지 설정
# =========================================================

st.set_page_config(
    page_title="Azure OpenAI Assistant",
    page_icon="🤖",
    layout="wide"
)

st.title("🤖 Azure OpenAI Assistant")
st.caption("질문 / 그래프 생성 / 파일 요약 / 데이터 분석")

# =========================================================
# OpenAI Client
# =========================================================

client = AzureOpenAI(
    azure_endpoint=AZURE_ENDPOINT,
    api_key=AZURE_API_KEY,
    api_version=AZURE_API_VERSION
)

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

        답변은 한국어로 해줘.
        """,
        tools=[
            {"type": "code_interpreter"},
            {"type": "file_search"}
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

if "thread_id" not in st.session_state:
    thread = client.beta.threads.create()
    st.session_state.thread_id = thread.id

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

    # 사용자 메시지 출력
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
    # Thread에 메시지 추가
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
    # 실행 상태 표시
    # =====================================================

    with st.spinner("AI가 작업 중입니다..."):

        while run.status in ["queued", "in_progress", "cancelling"]:

            time.sleep(1)

            run = client.beta.threads.runs.retrieve(
                thread_id=st.session_state.thread_id,
                run_id=run.id
            )

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

                    image = Image.open(
                        tempfile.NamedTemporaryFile(
                            delete=False,
                            suffix=".png"
                        ).name
                    )

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
                # 파일 생성 결과 처리
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

    else:
        st.error(f"실행 실패: {run.status}")
