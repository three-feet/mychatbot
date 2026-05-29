# app.py
# ============================================
# 💜 지민이랑 영화볼래? (Stable Version)
# Streamlit + Azure OpenAI + Azure AI Search
# ============================================

import streamlit as st
from openai import AzureOpenAI

# ============================================
# Page config
# ============================================

st.set_page_config(
    page_title="지민이랑 영화볼래?",
    page_icon="💜",
    layout="wide"
)

# ============================================
# Secrets
# ============================================

searchkey = st.secrets["searchkey"]
searchendpoint = st.secrets["searchendpoint"]

index = st.secrets["index"]
semantic = st.secrets["semantic"]

endpoint = st.secrets["endpoint"]
apikey = st.secrets["apikey"]
deploymentname = st.secrets["deploymentname"]

# ============================================
# Azure OpenAI Client
# ============================================

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=apikey,
    api_version="2024-05-01-preview"
)

# ============================================
# CSS (safe)
# ============================================

st.markdown(
    """
    <style>

    .stApp {
        background-image:
            linear-gradient(rgba(0,0,0,0.6), rgba(0,0,0,0.6)),
            url("https://sstatic.naver.net/people/profileImg/977878c9-7a3e-4434-9fa6-da1eba022a5f.jpg");
        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    .title {
        text-align: center;
        font-size: 48px;
        font-weight: 800;
        color: white;
        margin-top: 20px;
    }

    .subtitle {
        text-align: center;
        color: #e9d5ff;
        margin-bottom: 30px;
        font-size: 18px;
    }

    div[data-testid="stChatMessage"] {
        background: rgba(255,255,255,0.12);
        border-radius: 16px;
        padding: 10px;
        backdrop-filter: blur(10px);
    }

    .card {
        background: rgba(255,255,255,0.15);
        padding: 12px;
        border-radius: 14px;
        margin-top: 10px;
    }

    </style>
    """,
    unsafe_allow_html=True
)

# ============================================
# Title
# ============================================

st.markdown("<div class='title'>💜 지민이랑 영화볼래?</div>", unsafe_allow_html=True)
st.markdown("<div class='subtitle'>지민 감성으로 영화 추천해줄게 ✨</div>", unsafe_allow_html=True)

# ============================================
# Session state
# ============================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# ============================================
# Sidebar
# ============================================

with st.sidebar:
    st.markdown("## 🎬 Mood")

    mood = st.selectbox(
        "오늘 기분",
        [
            "로맨스 💕",
            "감성 😭",
            "힐링 🌿",
            "스릴러 🔥",
            "코미디 😂"
        ]
    )

    if st.button("🗑️ Reset Chat"):
        st.session_state.messages = []
        st.rerun()

# ============================================
# Chat history
# ============================================

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ============================================
# Input
# ============================================

prompt = st.chat_input("지민이랑 어떤 영화 보고 싶어? 💜")

# ============================================
# Main logic (STABLE)
# ============================================

if prompt:

    # user save
    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    # default answer (VERY IMPORTANT for stability)
    answer = "추천을 생성하는 중이야 💜 잠시만 기다려줘"

    try:
        response = client.chat.completions.create(
            model=deploymentname,
            messages=[
                {
                    "role": "system",
                    "content": f"""
너는 BTS 지민 감성 영화 추천 챗봇이다.

규칙:
- 감성적이고 따뜻한 말투
- 영화 2~3개 추천
- 이유 설명
- 이모지 적당히 사용

현재 무드: {mood}
"""
                },
                {
                    "role": "user",
                    "content": prompt
                }
            ],
            temperature=0.9,
            max_tokens=700,
            extra_body={
                "data_sources": [
                    {
                        "type": "azure_search",
                        "parameters": {
                            "endpoint": searchendpoint,
                            "index_name": index,
                            "semantic_configuration": semantic,
                            "authentication": {
                                "type": "api_key",
                                "key": searchkey
                            }
                        }
                    }
                ]
            }
        )

        answer = response.choices[0].message.content

    except Exception as e:
        answer = f"⚠️ 오류 발생: {str(e)}"

    # save assistant
    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

    # show assistant
    with st.chat_message("assistant"):
        st.markdown(answer)

        st.markdown(
            """
            <div class='card'>
            💜 오늘도 좋은 영화와 함께 행복한 시간 보내길 바라 ✨
            </div>
            """,
            unsafe_allow_html=True
        )
