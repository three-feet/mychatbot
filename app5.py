import os
import json
import time
import requests
import tempfile
import streamlit as st
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
.stChatMessage {
    border-radius: 15px;
    padding: 10px;
}

.block-container {
    padding-top: 2rem;
}

.stButton button {
    border-radius: 10px;
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

    if st.button("🧹 대화 초기화"):

        thread = client.beta.threads.create()

        st.session_state.thread_id = thread.id
        st.session_state.messages = []

        st.rerun()

# ==================================================
# 메인 헤더
# ==================================================

st.title("💜 세무요정 지민")
st.caption("BTS 지민이 알려주는 세법 상담 챗봇")

# ==================================================
# 이전 대화 출력
# ==================================================

for msg in st.session_state.messages:

    with st.chat_message(msg["role"]):

        st.markdown(msg["content"])

# ==================================================
# 음성 입력
# ==================================================

audio_file = st.audio_input("🎤 음성으로 질문하기")

voice_prompt = None

if audio_file:

    with st.spinner("음성 인식 중..."):

        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file
        )

        voice_prompt = transcript.text

        st.success(f"인식된 질문: {voice_prompt}")

# ==================================================
# 채팅 입력
# ==================================================

text_prompt = st.chat_input(
    "세금이나 궁금한 걸 물어봐 💜"
)

prompt = voice_prompt if voice_prompt else text_prompt

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

    # ==============================================
    # 첨부파일 연결
    # ==============================================

    attachments = []

    for fid in uploaded_file_ids:

        attachments.append({
            "file_id": fid,
            "tools": [
                {"type": "file_search"},
                {"type": "code_interpreter"}
            ]
        })

    # ==============================================
    # 사용자 메시지 생성
    # ==============================================

    client.beta.threads.messages.create(
        thread_id=st.session_state.thread_id,
        role="user",
        content=prompt,
        attachments=attachments if attachments else None
    )

    # ==============================================
    # Run 실행
    # ==============================================

    run = client.beta.threads.runs.create(
        thread_id=st.session_state.thread_id,
        assistant_id=assistant_id
    )

    # ==============================================
    # Assistant 응답 처리
    # ==============================================

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

                    # ==============================
                    # 곱셈 함수
                    # ==============================

                    if function_name == "mul_numbers":

                        result = mul_numbers(
                            arguments["a"],
                            arguments["b"]
                        )

                        tool_outputs.append({
                            "tool_call_id": tool_call.id,
                            "output": json.dumps(result)
                        })

                    # ==============================
                    # 날씨 함수
                    # ==============================

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

                # ==================================
                # 함수 결과 제출
                # ==================================

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

                    # ==============================
                    # 텍스트 응답
                    # ==============================

                    if item.type == "text":

                        full_response += item.text.value + "\n"

                    # ==============================
                    # 이미지 응답
                    # ==============================

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

                # ==================================
                # TTS 음성 출력
                # ==================================

                try:

                    speech = client.audio.speech.create(
                        model="tts-1",
                        voice="nova",
                        input=full_response
                    )

                    st.audio(
                        speech.content,
                        format="audio/mp3"
                    )

                except Exception as e:

                    st.warning(f"TTS 오류: {e}")

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
