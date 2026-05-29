# ============================================
# 💜 지민이랑 영화볼래?
# BTS 지민 감성 영화 추천 챗봇
# Streamlit + Azure OpenAI + Azure AI Search
# ============================================

import streamlit as st
from openai import AzureOpenAI

# ============================================
# 페이지 설정
# ============================================

st.set_page_config(
    page_title="지민이랑 영화볼래?",
    page_icon="💜",
    layout="wide"
)

# ============================================
# Secret 불러오기
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
# CSS 스타일
# ============================================

st.markdown(
    """
    <style>

    @import url('https://fonts.googleapis.com/css2?family=Pretendard:wght@400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Pretendard', sans-serif;
    }

    .stApp {
        background-image:
            linear-gradient(
                rgba(0,0,0,0.55),
                rgba(0,0,0,0.55)
            ),
            url("https://sstatic.naver.net/people/profileImg/977878c9-7a3e-4434-9fa6-da1eba022a5f.jpg");

        background-size: cover;
        background-position: center;
        background-attachment: fixed;
    }

    .main-title {
        font-size: 58px;
        font-weight: 800;
        color: white;
        text-align: center;
        margin-top: 10px;
        margin-bottom: 8px;
        text-shadow: 2px 2px 15px rgba(0,0,0,0.5);
    }

    .sub-title {
        text-align: center;
        color: #f3e8ff;
        font-size: 22px;
        margin-bottom: 35px;
    }

    div[data-testid="stChatMessage"] {
        background: rgba(255,255,255,0.12);
        border-radius: 22px;
        padding: 14px;
        backdrop-filter: blur(10px);
        margin-bottom: 14px;
        border: 1px solid rgba(255,255,255,0.1);
    }

    .stChatInput input {
        background-color: rgba(255,255,255,0.92) !important;
        color: black !important;
        border-radius: 20px !important;
    }

    section[data-testid="stSidebar"] {
        background: rgba(30, 10, 45, 0.95);
    }

    section[data-testid="stSidebar"] * {
        color: white !important;
    }

    .movie-card {
        background: rgba(255,255,255,0.15);
        padding: 16px;
        border-radius: 18px;
        margin-top: 12px;
        backdrop-filter: blur(8px);
    }

    </style>
    """,
    unsafe_allow_html=True
)

# ============================================
# 제목
# ============================================

st.markdown(
    """
    <div class='main-title'>
        💜 지민이랑 영화볼래?
    </div>
    """,
    unsafe_allow_html=True
)

st.markdown(
    """
    <div class='sub-title'>
        오늘 기분에 어울리는 영화를 지민 감성으로 추천해줄게 ✨
    </div>
    """,
    unsafe_allow_html=True
)

# ============================================
# 사이드바
# ============================================

with st.sidebar:

    st.markdown("## 🎬 오늘의 영화 무드")

    mood = st.selectbox(
        "기분 선택",
        [
            "설레는 로맨스 💕",
            "눈물나는 감성 😭",
            "힐링 영화 🌿",
            "긴장감 스릴러 🔥",
            "웃긴 코미디 😂",
            "지민 감성 영화 ✨"
        ]
    )

    st.markdown("---")

    st.markdown("## 💜 JIMIN PICK")

    st.markdown(
        """
        🎞️ 라라랜드  
        🎞️ 어바웃 타임  
        🎞️ 비긴 어게인  
        🎞️ 인터스텔라  
        """
    )

    st.markdown("---")

    if st.button("🗑️ 대화 초기화"):
        st.session_state.messages = []
        st.rerun()

# ============================================
# 세션 상태
# ============================================

if "messages" not in st.session_state:
    st.session_state.messages = []

# ============================================
# 기존 채팅 출력
# ============================================

for message in st.session_state.messages:

    with st.chat_message(message["role"]):
        st.markdown(message["content"])

# ============================================
# 입력창
# ============================================

prompt = st.chat_input(
    "지민이와 함께 보고 싶은 영화 스타일을 말해줘 💜"
)

# ============================================
# 질문 처리
# ============================================

if prompt:

    # 사용자 메시지 저장
    st.session_state.messages.append(
        {
            "role": "user",
            "content": prompt
        }
    )

    # 사용자 메시지 출력
    with st.chat_message("user"):
        st.markdown(prompt)

    # 로딩 표시
    with st.spinner("💜 지민이가 영화 찾는 중..."):

        try:

            # ============================================
            # Azure OpenAI 호출
            # ============================================

            response = client.chat.completions.create(
                model=deploymentname,
                messages=[
                    {
                        "role": "system",
                        "content": f"""
너는 BTS 지민 감성의 영화 추천 챗봇이야.

규칙:
- 따뜻하고 감성적인 말투 사용
- 팬들이 좋아할 만한 부드러운 분위기
- 영화 추천을 자세하게 설명
- 말 끝에 가끔 💜 ✨ 😊 같은 이모지 사용
- 영화 추천 이유를 감성적으로 설명
- 사용자의 현재 기분에 맞춰 추천
- 마치 지민이 대화하는 느낌으로 답변

현재 사용자 무드:
{mood}
"""
                    },
                    {
                        "role": "user",
                        "content": prompt
                    }
                ],
                max_tokens=700,
                temperature=0.9,
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

            answer = f"""
앗 😢 영화 추천 중 오류가 발생했어.

오류 내용:

{str(e)}

st.session_state.messages.append(
    {
        "role": "assistant",
        "content": answer
    }
)

# 답변 출력
with st.chat_message("assistant"):

    st.markdown(answer)

    card_html = """
    <div class='movie-card'>
        💜 오늘도 좋은 영화와 함께 행복한 시간 보내길 바라 ✨
    </div>
    """

    st.markdown(card_html, unsafe_allow_html=True)
