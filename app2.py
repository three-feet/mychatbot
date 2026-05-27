# app2.py

import os
import asyncio
import base64
import queue
import threading
import tempfile
import wave

import av
import numpy as np
import streamlit as st

from dotenv import load_dotenv
from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
from openai import AsyncOpenAI

# =========================
# 환경 변수 로드
# =========================
load_dotenv()

AZURE_OPENAI_ENDPOINT = st.secrets["AZURE_OPENAI_ENDPOINT"]
AZURE_OPENAI_API_KEY = st.secrets["AZURE_OPENAI_API_KEY"]
AZURE_OPENAI_DEPLOYMENT = st.secrets["AZURE_OPENAI_DEPLOYMENT"]

# =========================
# Streamlit 설정
# =========================
st.set_page_config(
    page_title="Realtime Voice Chat",
    page_icon="🎤",
    layout="wide",
)

# =========================
# CSS
# =========================
st.markdown(
    """
    <style>
    .main {
        background-color: #08131f;
        color: white;
    }

    .stApp {
        background: linear-gradient(180deg,#08131f,#0f2740);
    }

    .title {
        text-align:center;
        padding-top:20px;
        padding-bottom:10px;
    }

    .chat-box {
        background:#13283f;
        padding:15px;
        border-radius:15px;
        margin-top:10px;
        margin-bottom:10px;
    }

    .user-box {
        background:#1d4e89;
    }

    .assistant-box {
        background:#18324f;
    }

    .status {
        padding:10px;
        border-radius:10px;
        background:#102235;
        margin-bottom:10px;
    }
    </style>
    """,
    unsafe_allow_html=True,
)

st.markdown(
    """
    <div class="title">
        <h1>🎤 Azure OpenAI Realtime Voice Chat</h1>
        <p>브라우저 마이크 기반 실시간 음성 대화</p>
    </div>
    """,
    unsafe_allow_html=True,
)

# =========================
# Azure OpenAI 설정
# =========================
base_url = (
    AZURE_OPENAI_ENDPOINT.replace("https://", "wss://")
    .rstrip("/")
    + "/openai/v1"
)

client = AsyncOpenAI(
    websocket_base_url=base_url,
    api_key=AZURE_OPENAI_API_KEY,
)

# =========================
# 오디오 설정
# =========================
SAMPLE_RATE = 24000
CHANNELS = 1

# =========================
# Session State
# =========================
if "messages" not in st.session_state:
    st.session_state.messages = []

if "audio_queue" not in st.session_state:
    st.session_state.audio_queue = queue.Queue()

if "running" not in st.session_state:
    st.session_state.running = False

# =========================
# 상태 출력
# =========================
status_placeholder = st.empty()

# =========================
# WebRTC Audio Processor
# =========================
class AudioProcessor(AudioProcessorBase):

    def recv(self, frame: av.AudioFrame):

        audio = frame.to_ndarray()

        if len(audio.shape) > 1:
            audio = audio.mean(axis=0)

        audio = audio.astype(np.int16)

        st.session_state.audio_queue.put(audio.tobytes())

        return frame

# =========================
# 채팅 출력
# =========================
chat_container = st.container()

def render_chat():

    with chat_container:

        for role, msg in st.session_state.messages:

            if role == "user":

                st.markdown(
                    f"""
                    <div class="chat-box user-box">
                    🗣 <b>사용자</b><br><br>
                    {msg}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

            else:

                st.markdown(
                    f"""
                    <div class="chat-box assistant-box">
                    🤖 <b>GPT</b><br><br>
                    {msg}
                    </div>
                    """,
                    unsafe_allow_html=True,
                )

# =========================
# PCM → WAV
# =========================
def pcm_to_wav_bytes(pcm_bytes):

    with tempfile.NamedTemporaryFile(delete=False, suffix=".wav") as f:

        with wave.open(f.name, "wb") as wav_file:

            wav_file.setnchannels(CHANNELS)
            wav_file.setsampwidth(2)
            wav_file.setframerate(SAMPLE_RATE)
            wav_file.writeframes(pcm_bytes)

        with open(f.name, "rb") as audio_file:
            return audio_file.read()

# =========================
# 오디오 송신
# =========================
async def stream_audio(connection):

    while True:

        if not st.session_state.running:
            break

        if not st.session_state.audio_queue.empty():

            chunk = st.session_state.audio_queue.get()

            await connection.input_audio_buffer.append(
                audio=base64.b64encode(chunk).decode("utf-8")
            )

        await asyncio.sleep(0.01)

# =========================
# 이벤트 수신
# =========================
async def receive_events(connection):

    assistant_text = ""
    audio_chunks = []

    async for event in connection:

        # 사용자 STT
        if event.type == "conversation.item.input_audio_transcription.completed":

            st.session_state.messages.append(
                ("user", event.transcript)
            )

            render_chat()

        # GPT 텍스트
        elif event.type == "response.output_text.delta":

            assistant_text += event.delta

        # GPT 음성
        elif event.type == "response.output_audio.delta":

            audio_chunks.append(
                base64.b64decode(event.delta)
            )

        # GPT 응답 완료
        elif event.type == "response.done":

            if assistant_text:

                st.session_state.messages.append(
                    ("assistant", assistant_text)
                )

                render_chat()

            # 음성 재생
            if audio_chunks:

                merged_audio = b"".join(audio_chunks)

                wav_bytes = pcm_to_wav_bytes(merged_audio)

                st.audio(
                    wav_bytes,
                    format="audio/wav",
                    autoplay=True,
                )

            assistant_text = ""
            audio_chunks = []

        # 오류
        elif event.type == "error":

            status_placeholder.error(
                f"❌ 오류: {event.error.message}"
            )

# =========================
# 메인 Realtime
# =========================
async def realtime_main():

    async with client.realtime.connect(
        model=AZURE_OPENAI_DEPLOYMENT
    ) as connection:

        await connection.session.update(
            session={
                "type": "realtime",
                "instructions": (
                    "You are a friendly Korean AI assistant. "
                    "Always answer naturally in Korean."
                ),
                "modalities": ["text", "audio"],
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "voice": "alloy",
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.5,
                    "silence_duration_ms": 700,
                },
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
            }
        )

        status_placeholder.success(
            "✅ Realtime API 연결 완료"
        )

        await asyncio.gather(
            stream_audio(connection),
            receive_events(connection),
        )

# =========================
# Thread 실행
# =========================
def run_async():

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(
        realtime_main()
    )

# =========================
# WebRTC
# =========================
webrtc_streamer(
    key="voice-chat",
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={
        "audio": True,
        "video": False,
    },
    async_processing=True,
)

# =========================
# 버튼 UI
# =========================
col1, col2 = st.columns(2)

with col1:

    if st.button("🎙 음성 대화 시작"):

        if not st.session_state.running:

            st.session_state.running = True

            threading.Thread(
                target=run_async,
                daemon=True,
            ).start()

            status_placeholder.info(
                "🎤 마이크 연결됨"
            )

with col2:

    if st.button("🛑 종료"):

        st.session_state.running = False

        status_placeholder.warning(
            "⛔ 종료됨"
        )

# =========================
# 사이드바
# =========================
with st.sidebar:

    st.header("⚙️ 설정")

    st.markdown(
        """
        ### 사용 방법
        1. 음성 대화 시작 클릭
        2. 브라우저 마이크 권한 허용
        3. 말하면 GPT가 음성으로 응답

        ### 지원 기능
        - 실시간 음성 입력
        - Whisper STT
        - GPT 음성 응답
        - 모바일 브라우저 지원
        - Streamlit Cloud 배포 가능
        """
    )

# =========================
# 채팅 렌더링
# =========================
render_chat()
