# app.py
# 실행:
# streamlit run app.py

import os
import queue
import tempfile
import threading
import time

import numpy as np
import sounddevice as sd
import streamlit as st

from openai import OpenAI
from scipy.io.wavfile import write

# ---------------------------------
# OpenAI 클라이언트
# ---------------------------------
client = OpenAI(
    api_key=STT_API_KEY
)

# ---------------------------------
# 설정
# ---------------------------------
SAMPLE_RATE = 16000
CHANNELS = 1

# ---------------------------------
# Streamlit
# ---------------------------------
st.set_page_config(
    page_title="실시간 Whisper API STT",
    page_icon="🎤",
    layout="wide"
)

st.title("🎤 실시간 음성 자막")
st.caption("Python 3.14 + OpenAI Whisper API")

# ---------------------------------
# 세션 상태
# ---------------------------------
if "running" not in st.session_state:
    st.session_state.running = False

if "subtitles" not in st.session_state:
    st.session_state.subtitles = []

# ---------------------------------
# 사이드바
# ---------------------------------
st.sidebar.header("⚙️ 설정")

language = st.sidebar.selectbox(
    "언어",
    ["ko", "en", "ja"],
    index=0
)

chunk_seconds = st.sidebar.slider(
    "자막 생성 주기",
    1,
    10,
    3
)

# ---------------------------------
# 오디오 큐
# ---------------------------------
audio_queue = queue.Queue()

# ---------------------------------
# 오디오 콜백
# ---------------------------------
def audio_callback(indata, frames, time_info, status):

    if status:
        print(status)

    audio_queue.put(indata.copy())

# ---------------------------------
# Whisper API 호출
# ---------------------------------
def transcribe_audio(file_path):

    with open(file_path, "rb") as audio_file:

        transcript = client.audio.transcriptions.create(
            model="whisper-1",
            file=audio_file,
            language=language
        )

    return transcript.text

# ---------------------------------
# STT 워커
# ---------------------------------
def transcribe_worker():

    buffer = []

    with sd.InputStream(
        samplerate=SAMPLE_RATE,
        channels=CHANNELS,
        dtype="float32",
        callback=audio_callback
    ):

        while st.session_state.running:

            try:
                data = audio_queue.get(timeout=1)

            except queue.Empty:
                continue

            buffer.append(data)

            total_samples = sum(len(x) for x in buffer)

            if total_samples >= SAMPLE_RATE * chunk_seconds:

                audio_data = np.concatenate(buffer, axis=0)

                with tempfile.NamedTemporaryFile(
                    suffix=".wav",
                    delete=False
                ) as temp_audio:

                    temp_path = temp_audio.name

                    write(
                        temp_path,
                        SAMPLE_RATE,
                        (audio_data * 32767).astype(np.int16)
                    )

                try:

                    text = transcribe_audio(temp_path)

                    if text:

                        current_time = time.strftime("%H:%M:%S")

                        st.session_state.subtitles.append(
                            f"[{current_time}] {text}"
                        )

                except Exception as e:

                    st.error(f"STT 오류: {e}")

                finally:

                    if os.path.exists(temp_path):
                        os.remove(temp_path)

                buffer = []

# ---------------------------------
# 버튼
# ---------------------------------
col1, col2, col3 = st.columns(3)

with col1:

    if st.button("▶️ 시작"):

        if not st.session_state.running:

            st.session_state.running = True

            threading.Thread(
                target=transcribe_worker,
                daemon=True
            ).start()

with col2:

    if st.button("⛔ 중지"):

        st.session_state.running = False

with col3:

    if st.button("🗑️ 기록 삭제"):

        st.session_state.subtitles = []

# ---------------------------------
# 상태 표시
# ---------------------------------
if st.session_state.running:
    st.success("🎙️ 음성 인식 중")
else:
    st.info("대기 중")

# ---------------------------------
# 자막 표시
# ---------------------------------
st.subheader("📝 실시간 자막")

for line in reversed(st.session_state.subtitles[-15:]):

    st.markdown(
        f"""
        <div style="
            background:#111827;
            color:white;
            padding:14px;
            border-radius:12px;
            margin-bottom:10px;
            font-size:20px;
            line-height:1.6;
        ">
            {line}
        </div>
        """,
        unsafe_allow_html=True
    )

# ---------------------------------
# 전체 기록
# ---------------------------------
with st.expander("📜 전체 기록"):

    st.text_area(
        "Transcript",
        value="\n".join(st.session_state.subtitles),
        height=300
    )

# ---------------------------------
# 자동 새로고침
# ---------------------------------
if st.session_state.running:

    time.sleep(1)
    st.rerun()
