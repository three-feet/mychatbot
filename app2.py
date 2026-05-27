import streamlit as st
import asyncio
import base64
import queue
import threading
import av
import numpy as np

from streamlit_webrtc import webrtc_streamer, AudioProcessorBase
from openai import AsyncOpenAI

# =========================
# Azure OpenAI 설정
# =========================
endpoint = "YOUR_AZURE_ENDPOINT"
deployment_name = "YOUR_DEPLOYMENT"
token = "YOUR_API_KEY"

base_url = (
    endpoint.replace("https://", "wss://")
    .rstrip("/")
    + "/openai/v1"
)

# =========================
# 오디오 설정
# =========================
SAMPLE_RATE = 24000
CHANNELS = 1

# =========================
# OpenAI Client
# =========================
client = AsyncOpenAI(
    websocket_base_url=base_url,
    api_key=token,
)

# =========================
# Streamlit UI
# =========================
st.set_page_config(
    page_title="Azure OpenAI Realtime Voice",
    page_icon="🎤",
)

st.title("🎤 Azure OpenAI Realtime Voice Chat")

status_box = st.empty()
transcript_box = st.empty()

# =========================
# 오디오 큐
# =========================
audio_queue = queue.Queue()


# =========================
# WebRTC 오디오 입력
# =========================
class AudioProcessor(AudioProcessorBase):

    def recv(self, frame: av.AudioFrame):

        audio = frame.to_ndarray()

        # stereo -> mono
        if len(audio.shape) > 1:
            audio = audio.mean(axis=0)

        # int16 변환
        audio = audio.astype(np.int16)

        audio_bytes = audio.tobytes()

        audio_queue.put(audio_bytes)

        return frame


# =========================
# Realtime API 송신
# =========================
async def stream_audio(connection):

    while True:

        if not audio_queue.empty():

            audio_chunk = audio_queue.get()

            await connection.input_audio_buffer.append(
                audio=base64.b64encode(audio_chunk).decode("utf-8")
            )

        await asyncio.sleep(0.01)


# =========================
# Realtime API 수신
# =========================
async def receive_events(connection):

    full_text = ""

    async for event in connection:

        # GPT 텍스트 응답
        if event.type == "response.output_text.delta":

            full_text += event.delta

            transcript_box.markdown(
                f"""
                ### 🤖 GPT 응답

                {full_text}
                """
            )

        # 사용자 음성 인식 완료
        elif event.type == "conversation.item.input_audio_transcription.completed":

            st.write(f"🗣 사용자: {event.transcript}")

        # 완료
        elif event.type == "response.done":

            status_box.success("✅ 응답 완료")

        # 오류
        elif event.type == "error":

            status_box.error(f"❌ 오류: {event.error.message}")


# =========================
# 메인 Async
# =========================
async def realtime_main():

    async with client.realtime.connect(
        model=deployment_name
    ) as connection:

        # 세션 설정
        await connection.session.update(
            session={
                "type": "realtime",
                "instructions": (
                    "You are a helpful assistant. "
                    "Answer naturally in Korean."
                ),
                "modalities": ["text"],
                "input_audio_format": "pcm16",
                "output_audio_format": "pcm16",
                "turn_detection": {
                    "type": "server_vad"
                },
                "input_audio_transcription": {
                    "model": "whisper-1"
                },
            }
        )

        status_box.success("✅ Realtime API 연결 완료")

        await asyncio.gather(
            stream_audio(connection),
            receive_events(connection),
        )


# =========================
# Async 실행 Thread
# =========================
def run_async():

    loop = asyncio.new_event_loop()
    asyncio.set_event_loop(loop)

    loop.run_until_complete(realtime_main())


# =========================
# WebRTC 시작
# =========================
webrtc_streamer(
    key="voice-chat",
    audio_processor_factory=AudioProcessor,
    media_stream_constraints={
        "audio": True,
        "video": False,
    },
)

# =========================
# 시작 버튼
# =========================
if st.button("🎙 음성 대화 시작"):

    threading.Thread(
        target=run_async,
        daemon=True,
    ).start()

    st.info("마이크에 말해보세요.")
