# app.py
# ============================================
# 💜 BTS 감성 영화 추천 챗봇
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
# Azure OpenAI
# ============================================

client = AzureOpenAI(
    azure_endpoint=endpoint,
    api_key=apikey,
    api_version="2024-05-01-preview"
)

# ============================================
# 💜 BTS 연보라 테마 CSS
# ============================================

st.markdown(
    """
    <style>

    /* =========================
    💜 GLOBAL BACKGROUND LOCK
    ========================= */

    html, body {
        background-color: #120a1f !important;
    }

    /* Streamlit 전체 앱 */
    .stApp {
        background: linear-gradient(
            135deg,
            #120a1f 0%,
            #2a0f3a 50%,
            #3b1c5c 100%
        ) !important;
    }

    /* Streamlit 기본 컨테이너 (흰색 덮는 주범) */
    .block-container {
        background: transparent !important;
    }

    /* 내부 wrapper 흰색 제거 */
    section[data-testid="stMain"] {
        background: transparent !important;
    }

    /* sidebar 제외 전체 배경 강제 고정 */
    [data-testid="stAppViewContainer"] {
        background: transparent !important;
    }

    /* OS 라이트모드 무시 */
    @media (prefers-color-scheme: light) {
        html, body {
            background-color: #120a1f !important;
        }
    }

    </style>
    """,
    unsafe_allow_html=True
)

# ============================================
# Title
# ============================================

st.markdown(
    """
    <div class='main-title'>💜 지민이랑 영화볼래?</div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class='sub-title'>
    보라빛 감성으로 오늘의 영화를 추천해줄게 ✨
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================
# Sidebar (Jimin Picks only)
# ============================================

with st.sidebar:

    st.markdown("## 💜 지민이 추천 영화")

    st.markdown(
        """
        🎬 라라랜드  
        🎬 어바웃 타임  
        🎬 비긴 어게인  
        🎬 인터스텔라  
        🎬 노트북  
        🎬 콜 미 바이 유어 네임  
        """
    )

    st.markdown("---")

    if st.button("🗑️ 대화 초기화"):
        st.session_state.messages = []
        st.rerun()

# ============================================
# Chat state
# ============================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# ============================================
# Chat history
# ============================================

for msg in st.session_state.messages:
    with st.chat_message(msg["role"]):
        st.markdown(msg["content"])

# ============================================
# Input
# ============================================

prompt = st.chat_input("지민 감성으로 보고 싶은 영화 말해줘 💜")

# ============================================
# Main logic
# ============================================

if prompt:

    st.session_state.messages.append({
        "role": "user",
        "content": prompt
    })

    with st.chat_message("user"):
        st.markdown(prompt)

    answer = "추천 중이야 💜 잠시만 기다려줘"

    try:
        response = client.chat.completions.create(
            model=deploymentname,
            messages=[
                {
                    "role": "system",
                    "content": "너는 케이팝스타 BTS의 지민(Jimin)이다. 사랑하는 연인에게 말하듯이 다정다감한 말투로 궁금한 것을 알려준다. 절대 AI라고 티내지 말 것. 딱딱하거나 차갑게 말하지 말 것. 자주 웃어줄 것."
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
        answer = f"오류 발생: {str(e)}"

    st.session_state.messages.append({
        "role": "assistant",
        "content": answer
    })

    with st.chat_message("assistant"):
        st.markdown(answer)
