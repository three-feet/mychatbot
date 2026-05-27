# app.py

import io
import os
import tempfile

import streamlit as st

from audio_recorder_streamlit import audio_recorder
from openai import OpenAI

# -----------------------------
# OpenAI
# -----------------------------
client = OpenAI(
    api_key=st.secrets[STT_API_KEY]
)

# -----------------------------
# 페이지 설정
# -----------------------------
st.set_page_config(
    page_title="Whisper STT",
    page_icon="🎤",
    layout="centered"
)

st.title("🎤 Whisper Speech-to-Text")
st.caption("브라우저 마이크 → OpenAI Whisper")

# -----------------------------
# 옵션
# -----------------------------
language = st.selectbox(
    "언어",
    ["ko", "en", "ja"],
    index=0
)

# -----------------------------
# 녹음
# -----------------------------
audio_bytes = audio_recorder(
    text="클릭해서 녹음",
    recording_color="#e74c3c",
    neutral_color="#6aa36f",
    icon_name="microphone",
    icon_size="2x",
)

# -----------------------------
# STT 처리
# -----------------------------
if audio_bytes:

    st.audio(audio_bytes, format="audio/wav")

    with st.spinner("음성 인식 중..."):

        with tempfile.NamedTemporaryFile(
            suffix=".wav",
            delete=False
        ) as tmp_file:

            tmp_file.write(audio_bytes)
            temp_path = tmp_file.name

        with open(temp_path, "rb") as audio_file:

            transcript = client.audio.transcriptions.create(
                model="whisper-1",
                file=audio_file,
                language=language
            )

        text = transcript.text

    st.success("인식 완료")

    st.subheader("📝 변환 결과")

    st.markdown(
        f"""
        <div style="
            background:#111827;
            color:white;
            padding:20px;
            border-radius:12px;
            font-size:20px;
            line-height:1.8;
        ">
            {text}
        </div>
        """,
        unsafe_allow_html=True
    )
