
import os
import streamlit as st
from openai import AzureOpenAI
from dotenv import load_dotenv

# 로컬 테스트용 .env 로드 (스트림릿 클라우드 배포 시에는 웹 상의 Settings > Secrets에 등록해야 합니다)
load_dotenv()

# 스트림릿 페이지 설정
st.set_page_config(page_title="과일 전문가 AI 챗봇", page_icon="🍓", layout="centered")
st.title("🍓 과일 전문가 AI 챗봇")
st.subheader("과일에 대해 물어보시면 맛과 영양성분을 귀엽게 알려드려요! 😊")

# 1. 사이드바 설정 (하이퍼파라미터 조정용)
with st.sidebar:
    st.header("⚙️ 챗봇 설정")
    message_cnt = st.slider("기억할 대화 개수 (Turn)", min_value=1, max_value=10, value=3)
    max_tokens = st.slider("Max Tokens", min_value=100, max_value=2000, value=800)
    temperature = st.slider("Temperature", min_value=0.0, max_value=2.0, value=0.7, step=0.1)
    top_p = st.slider("Top P", min_value=0.0, max_value=1.0, value=0.95, step=0.05)

    if st.button("대화 내역 초기화 🧹"):
        st.session_state.chat_prompt = [
            {
                "role": "system",
                "content": [{"type": "text", "text": "너는 과일전문가야. 사용자가 과일에 대해서 질문하면 맛과 영양성분 등에 대해서 귀여운 어투로 대답해줘. 답변의 길이는 200자 이내로"}]
            }
        ]
        st.rerun()

# 2. Azure OpenAI 클라이언트 초기화 (st.cache_resource로 매번 생성되지 않도록 캐싱)
@st.cache_resource
def get_openai_client():
    endpoint = os.getenv("AZURE_OAI_ENDPOINT")
    subscription_key = os.getenv("AZURE_OAI_KEY")

    if not endpoint or not subscription_key:
        st.error("⚠️ 환경 변수(AZURE_OAI_ENDPOINT, AZURE_OAI_KEY)가 설정되지 않았습니다.")
        st.stop()

    return AzureOpenAI(
        azure_endpoint=endpoint,
        api_key=subscription_key,
        api_version="2025-01-01-preview",
    )

client = get_openai_client()
deployment = os.getenv("AZURE_OAI_DEPLOYMENT", "gpt-4o") # 기본값 설정 가능

# 3. 세션 상태(Session State)를 활용한 대화 내역 기억
if "chat_prompt" not in st.session_state:
    st.session_state.chat_prompt = [
        {
            "role": "system",
            "content": [{"type": "text", "text": "너는 과일전문가야. 사용자가 과일에 대해서 질문하면 맛과 영양성분 등에 대해서 귀여운 어투로 대답해줘. 답변의 길이는 200자 이내로"}]
        }
    ]

# 4. 화면에 기존 대화 내역 렌더링 (System 메시지는 제외)
for msg in st.session_state.chat_prompt:
    if msg["role"] == "system":
        continue

    # 챗봇 UI 형식으로 표시
    with st.chat_message(msg["role"]):
        # content 리스트 내부의 text만 추출
        for content_item in msg["content"]:
            if content_item["type"] == "text":
                st.write(content_item["text"])

# 5. 사용자 입력 처리
if user_input := st.chat_input("과일에 대해 무엇이든 물어보세요! (예: 사과는 몸에 왜 좋아?)"):

    # 대화 제한 개수 제어 (기존 콘솔 코드 로직 유지)
    message_limit = message_cnt * 2
    if len(st.session_state.chat_prompt) > (1 + message_limit):
        st.session_state.chat_prompt = [st.session_state.chat_prompt[0]] + st.session_state.chat_prompt[-message_limit:]

    # 화면에 사용자 질문 즉시 표시 및 세션 추가
    with st.chat_message("user"):
        st.write(user_input)

    st.session_state.chat_prompt.append({
        "role": "user",
        "content": [{"type": "text", "text": user_input}]
    })

    # AI 답변 생성 중 로딩 애니메이션 표시
    with st.chat_message("assistant"):
        with st.spinner("과일 박사가 생각 중이에요... 🍓"):
            try:
                completion = client.chat.completions.create(
                    model=deployment,
                    messages=st.session_state.chat_prompt,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    top_p=top_p,
                    stream=False
                )
                ai_response = completion.choices[0].message.content
                st.write(ai_response)

                # 세션에 AI 답변 추가
                st.session_state.chat_prompt.append({
                    "role": "assistant",
                    "content": [{"type": "text", "text": ai_response}]
                })

            except Exception as e:
                st.error(f"에러가 발생했습니다: {e}")
