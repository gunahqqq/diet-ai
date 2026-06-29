import streamlit as st
import google.generativeai as genai
from PIL import Image
import json

# --- 1. 모바일 친화적 UI 설정 ---
st.set_page_config(page_title="스마트 영양사 프로", page_icon="🍎", layout="centered")

# --- 2. API 키 및 모델 설정 ---
api_key = st.secrets["GEMINI_API_KEY"] 
genai.configure(api_key=api_key)
model = genai.GenerativeModel('gemini-2.5-flash')

# --- 3. 사이드바: 개인 맞춤형 프로필 & 오늘의 운동 ---
with st.sidebar:
    st.header("👤 나의 신체 정보")
    weight = st.number_input("체중 (kg)", min_value=30, max_value=150, value=70)
    
    st.header("🏃‍♂️ 오늘의 활동량")
    running_km = st.slider("오늘의 러닝 거리 (km)", 0.0, 20.0, 0.0, step=0.5)
    
    # 목표량 자동 계산
    base_cal = weight * 24 * 1.2
    burned_cal = running_km * 70
    target_cal = int(base_cal + burned_cal)
    
    protein_multiplier = 1.6 if running_km > 0 else 1.0
    target_protein = int(weight * protein_multiplier)
    target_carb = int((target_cal * 0.4) / 4) 
    target_fat = int((target_cal * 0.3) / 9)    
    
    st.info(f"🔥 러닝 소모 칼로리: +{int(burned_cal)} kcal")
    if running_km > 0:
        st.success("근육 회복을 위해 고단백 식단을 추천합니다!")

# --- 4. 하루 누적 데이터를 위한 세션 상태 초기화 ---
if 'cal' not in st.session_state:
    st.session_state.update({"cal": 0, "carb": 0, "protein": 0, "fat": 0})

# --- 5. [핵심] 다중 사진 & 잔반 계산 특화 프롬프트 ---
system_prompt = f"""
당신은 사용자의 건강을 책임지는 스마트 영양사입니다. 
제공된 텍스트나 사진을 분석하여 영양 성분을 계산하세요. 
만약 사용자가 '먹기 전 사진'과 '먹고 남은 사진'을 함께 올렸다면, 두 사진의 차이를 분석하여 **'실제로 섭취한 양'**에 대해서만 영양소를 계산해야 합니다.
반드시 아래의 [형식]에 맞춰 두 부분으로 나누어 출력하세요. 
'---DATA---' 아래에는 오직 JSON만 적어야 합니다.

[형식]
[식단 기록용 요약]
* 메뉴명: [인식된 음식 이름 / 잔반이 있을 경우 "실제 섭취량 기준" 표기]
* 총 칼로리: [000] kcal
* 탄수화물: [00] g
* 단백질: [00] g
* 지방: [00] g
* 당류: [00] g
* 나트륨: [000] mg
* AI 코멘트: [오늘의 러닝 거리({running_km}km)를 고려하여 피드백 1줄 작성]

---DATA---
{{"cal": 0, "carb": 0, "protein": 0, "fat": 0}}
"""

# 결과 처리 함수
def process_response(response_text):
    try:
        text_part, data_part = response_text.split("---DATA---")
        
        data = json.loads(data_part.strip())
        st.session_state.cal += int(data.get("cal", 0))
        st.session_state.carb += int(data.get("carb", 0))
        st.session_state.protein += int(data.get("protein", 0))
        st.session_state.fat += int(data.get("fat", 0))
        
        st.success("분석 완료! 우측 상단 아이콘을 눌러 복사하세요.")
        st.code(text_part.strip(), language="text")
        
    except Exception as e:
        st.warning("데이터 누적에는 실패했지만, 결과는 정상적으로 추출되었습니다.")
        st.code(response_text, language="text")

# --- 6. 메인 화면 UI (대시보드) ---
st.title("🍎 스마트 영양사 프로")

st.subheader("📊 오늘의 누적 영양소")
col1, col2, col3, col4 = st.columns(4)
col1.metric("칼로리", f"{st.session_state.cal} / {target_cal}")
col2.metric("탄수", f"{st.session_state.carb} / {target_carb}g")
col3.metric("단백질", f"{st.session_state.protein} / {target_protein}g")
col4.metric("지방", f"{st.session_state.fat} / {target_fat}g")

# [추가] 오늘 기록 초기화 버튼
if st.button("🔄 오늘 기록 초기화", key="reset_btn"):
    st.session_state.update({"cal": 0, "carb": 0, "protein": 0, "fat": 0})
    st.rerun()

st.divider()

# --- 7. 탭 구성 (카메라 제거, UI 심플화) ---
tab1, tab2 = st.tabs(["📸 음식 사진 분석", "✍️ 텍스트 분석"])

with tab1:
    st.info("💡 꿀팁: '먹기 전' 사진과 '먹고 남긴' 사진을 같이 올리면, AI가 차이를 계산해서 실제로 먹은 양만 알려줍니다!")
    # 카메라 입력 제거, 갤러리 업로드만 크게 배치
    uploaded_files = st.file_uploader("📂 사진 선택 (여러 장 가능)", type=['png', 'jpg', 'jpeg'], accept_multiple_files=True)
    
    if st.button("사진 영양 분석하기", use_container_width=True):
        if uploaded_files:
            images = [Image.open(f) for f in uploaded_files]
            with st.spinner("사진을 분석하여 영양소를 계산 중입니다..."):
                response = model.generate_content([system_prompt] + images)
                process_response(response.text)
        else:
            st.warning("사진을 업로드해주세요!")

with tab2:
    food_text = st.text_area(
        "먹은 음식과 양을 편하게 적어주세요.",
        placeholder="예: 짬뽕 시켜서 면은 절반 남기고 국물은 안 마셨어",
        height=100
    )
    if st.button("텍스트 영양 분석하기", use_container_width=True):
        if food_text:
            with st.spinner("문맥을 파악하여 영양소를 계산 중입니다..."):
                response = model.generate_content([system_prompt, food_text])
                process_response(response.text)
        else:
            st.warning("텍스트를 입력해주세요!")
